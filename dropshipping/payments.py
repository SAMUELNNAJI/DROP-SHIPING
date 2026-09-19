"""Server-side clients for the three payment rails DropHub accepts.

Only the standard library is used for HTTP, so no extra dependency has to be
installed on Render.  Nothing in here touches the database: the checkout flow in
``dashboards/payment_views.py`` owns that side.

Rails
-----
* **Paystack** — Naira cards/transfers.  The transaction is *initialised*
  server-side (secret key) and then finished in the browser with the inline
  popup; the outcome is always confirmed back through ``/transaction/verify``
  (or a signed webhook) before an order is created.
* **PayPal** — an order is created server-side (CAPTURE intent) and captured
  server-side again once the buyer approves it in the PayPal window.
* **Pi Network** — the Pi Browser SDK performs the payment and the server calls
  ``approve`` then ``complete`` with the app's API key.

Every function raises :class:`PaymentError` with a buyer-safe message when the
provider rejects the call, so views can turn it into a readable response.
"""

from __future__ import annotations

import base64
import hmac
import json
import logging
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from hashlib import sha512
from urllib import error as urlerror
from urllib import parse as urlparse
from urllib import request as urlrequest

from django.conf import settings

logger = logging.getLogger(__name__)

PAYSTACK_API_BASE = 'https://api.paystack.co'
PAYPAL_CURRENCY = 'USD'


class PaymentError(Exception):
    """A provider call failed (bad key, network problem, rejected payment)."""


# ══════════════════════════════════════════════════════════════
#  HTTP + money helpers
# ═══════════════════════════════════════════════════════════════

def money(value, places='0.01'):
    """Round a money-ish value half-up to ``places`` decimals."""
    try:
        return Decimal(value).quantize(Decimal(places), rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise PaymentError('Invalid amount supplied to the payment provider.') from exc


def _provider_message(raw, status_code):
    """Pull a human-readable message out of a provider error body."""
    try:
        payload = json.loads(raw)
    except (ValueError, TypeError):
        payload = {}
    if isinstance(payload, dict):
        for key in ('message', 'error_description', 'error', 'detail', 'name'):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return f'The payment provider rejected the request (HTTP {status_code}).'


def _request(url, *, method='GET', json_body=None, body=None, content_type=None,
             headers=None, timeout=None):
    """Call a provider endpoint and return the decoded JSON response."""
    data = None
    if json_body is not None:
        data = json.dumps(json_body).encode('utf-8')
        content_type = content_type or 'application/json'
    elif body is not None:
        data = body

    req = urlrequest.Request(url, data=data, method=method)
    req.add_header('Accept', 'application/json')
    if content_type:
        req.add_header('Content-Type', content_type)
    for key, value in (headers or {}).items():
        if value:
            req.add_header(key, value)

    timeout = timeout or getattr(settings, 'PAYMENT_HTTP_TIMEOUT', 25)
    try:
        with urlrequest.urlopen(req, timeout=timeout) as response:
            raw = response.read().decode('utf-8') or '{}'
    except urlerror.HTTPError as exc:
        raw = exc.read().decode('utf-8', 'replace')
        logger.warning('Payment provider returned HTTP %s for %s: %s', exc.code, url, raw[:600])
        raise PaymentError(_provider_message(raw, exc.code)) from exc
    except (urlerror.URLError, TimeoutError, OSError) as exc:
        logger.warning('Payment provider unreachable (%s): %s', url, exc)
        raise PaymentError(
            'The payment provider could not be reached. Please try again in a moment.'
        ) from exc

    try:
        return json.loads(raw)
    except ValueError as exc:
        logger.warning('Payment provider sent a non-JSON reply for %s: %s', url, raw[:300])
        raise PaymentError('The payment provider sent an unexpected reply.') from exc
# ══════════════════════════════════════════════════════════════
#  Currency conversion (shop prices are stored in USD)
# ═════════════════════════════════════════════════════════════

def _live_ngn_rate():
    """Naira-per-dollar rate from the DB (admin-managed), fallback to settings."""
    try:
        from dashboards.models import CurrencyRate
        return CurrencyRate.ngn_per_usd()
    except Exception:
        return settings.NGN_PER_USD


def _live_pi_rate():
    """Pi-per-dollar rate from the DB (admin-managed), fallback to settings."""
    try:
        from dashboards.models import CurrencyRate
        return CurrencyRate.pi_per_usd()
    except Exception:
        return settings.PI_PER_USD


def usd_to_ngn(amount_usd):
    """Naira amount for a USD total, rounded to whole Naira."""
    return money(Decimal(str(amount_usd)) * _live_ngn_rate(), '1')


def usd_to_pi(amount_usd):
    """Pi amount for a USD total (2 decimals, which the Pi SDK accepts)."""
    return money(Decimal(str(amount_usd)) * _live_pi_rate(), '0.01')


def ngn_to_kobo(amount_ngn):
    """Paystack expects the smallest currency unit (kobo)."""
    return int(money(amount_ngn, '0.01') * 100)


def paystack_amount_ngn(kobo):
    """Convert kobo back into Naira for display."""
    return money(Decimal(kobo) / 100, '0.01')


# ═════════════════════════════════════════════════════════════
#  Paystack
# ══════════════════════════════════════════════════════════════

def paystack_enabled():
    return bool(settings.PAYSTACK_SECRET_KEY and settings.PAYSTACK_PUBLIC_KEY)


def _paystack_headers():
    return {'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}'}


def paystack_initialize(*, email, amount_ngn, reference, callback_url=None, metadata=None):
    """Create a Paystack transaction and return its ``data`` payload.

    The returned ``access_code`` is what the browser hands to the inline popup,
    and ``authorization_url`` is the hosted fallback page.
    """
    payload = {
        'email': email,
        'amount': ngn_to_kobo(amount_ngn),
        'currency': 'NGN',
        'reference': reference,
    }
    if callback_url:
        payload['callback_url'] = callback_url
    if metadata:
        payload['metadata'] = metadata

    response = _request(
        f'{PAYSTACK_API_BASE}/transaction/initialize',
        method='POST',
        json_body=payload,
        headers=_paystack_headers(),
    )
    if not response.get('status') or not response.get('data'):
        raise PaymentError(response.get('message') or 'Paystack could not start this payment.')
    return response['data']


def paystack_verify(reference):
    """Fetch the authoritative state of a transaction (the only source of truth)."""
    response = _request(
        f'{PAYSTACK_API_BASE}/transaction/verify/{urlparse.quote(str(reference))}',
        headers=_paystack_headers(),
    )
    if not response.get('status') or not response.get('data'):
        raise PaymentError(response.get('message') or 'Paystack could not verify that payment.')
    return response['data']
# ═════════════════════════════════════════════════════════════
#  PayPal
# ══════════════════════════════════════════════════════════════

def paypal_enabled():
    return bool(settings.PAYPAL_CLIENT_ID and settings.PAYPAL_CLIENT_SECRET)


def paypal_access_token():
    """Client-credentials token, valid for a few hours."""
    credentials = base64.b64encode(
        f'{settings.PAYPAL_CLIENT_ID}:{settings.PAYPAL_CLIENT_SECRET}'.encode('utf-8')
    ).decode('ascii')
    response = _request(
        f'{settings.PAYPAL_API_BASE}/v1/oauth2/token',
        method='POST',
        body=urlparse.urlencode({'grant_type': 'client_credentials'}).encode('utf-8'),
        content_type='application/x-www-form-urlencoded',
        headers={'Authorization': f'Basic {credentials}'},
    )
    token = response.get('access_token')
    if not token:
        raise PaymentError('PayPal did not issue an access token.')
    return token


def paypal_create_order(*, amount_usd, reference, return_url, cancel_url, description=''):
    """Create a CAPTURE-intent PayPal order for the cart total."""
    payload = {
        'intent': 'CAPTURE',
        'purchase_units': [{
            'reference_id': reference,
            'custom_id': reference,
            'description': (description or 'DropHub order')[:127],
            'amount': {
                'currency_code': PAYPAL_CURRENCY,
                'value': str(money(amount_usd)),
            },
        }],
        'application_context': {
            'brand_name': 'DropHub',
            'user_action': 'PAY_NOW',
            'shipping_preference': 'NO_SHIPPING',
            'return_url': return_url,
            'cancel_url': cancel_url,
        },
    }
    order = _request(
        f'{settings.PAYPAL_API_BASE}/v2/checkout/orders',
        method='POST',
        json_body=payload,
        headers={'Authorization': f'Bearer {paypal_access_token()}'},
    )
    if not order.get('id'):
        raise PaymentError('PayPal could not create this order.')
    return order


def paypal_capture_order(order_id):
    """Capture an approved PayPal order and return the updated order payload."""
    order = _request(
        f'{settings.PAYPAL_API_BASE}/v2/checkout/orders/{urlparse.quote(str(order_id))}/capture',
        method='POST',
        json_body={},
        headers={'Authorization': f'Bearer {paypal_access_token()}'},
    )
    if not order.get('id'):
        raise PaymentError('PayPal did not return the captured order.')
    return order


def paypal_approve_url(order):
    """The URL the buyer must visit to approve a server-created order."""
    for link in order.get('links') or []:
        if link.get('rel') in ('approve', 'payer-action') and link.get('href'):
            return link['href']
    return ''


def paypal_capture_details(order):
    """Return the successful capture for an order, or ``None``.

    A capture only counts when both the order and the capture itself report
    ``COMPLETED`` — that is the signal used to create the orders.
    """
    if (order or {}).get('status') != 'COMPLETED':
        return None
    for unit in order.get('purchase_units') or []:
        for capture in ((unit.get('payments') or {}).get('captures') or []):
            if capture.get('status') == 'COMPLETED':
                return capture
    return None


def paypal_captured_amount(capture):
    """The captured amount as a ``Decimal`` (USD), or ``None``."""
    value = (((capture or {}).get('amount') or {}).get('value'))
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None

def paystack_signature_is_valid(raw_body, signature):
    """Validate the ``x-paystack-signature`` header of a webhook call."""
    if not settings.PAYSTACK_SECRET_KEY or not signature:
        return False
    expected = hmac.new(
        settings.PAYSTACK_SECRET_KEY.encode('utf-8'), raw_body or b'', sha512
    ).hexdigest()
    return hmac.compare_digest(expected, signature.strip())


# ═════════════════════════════════════════════════════════════
#  Pi Network
# ══════════════════════════════════════════════════════════════

def pi_sdk_enabled():
    """True when the Pi Browser SDK flow can be used (needs the app API key)."""
    return bool(settings.PI_API_KEY)


def _pi_headers():
    return {'Authorization': f'Key {settings.PI_API_KEY}'}


def pi_get_payment(payment_id):
    """Read a payment back from Pi — used to double-check before completing."""
    return _request(
        f'{settings.PI_API_BASE}/v2/payments/{urlparse.quote(str(payment_id))}',
        headers=_pi_headers(),
    )


def pi_approve_payment(payment_id):
    """Approve a payment so the Pi wallet will let the buyer send it."""
    return _request(
        f'{settings.PI_API_BASE}/v2/payments/{urlparse.quote(str(payment_id))}/approve',
        method='POST',
        json_body={},
        headers=_pi_headers(),
    )


def pi_complete_payment(payment_id, txid):
    """Complete a payment with the blockchain transaction id from the client."""
    return _request(
        f'{settings.PI_API_BASE}/v2/payments/{urlparse.quote(str(payment_id))}/complete',
        method='POST',
        json_body={'txid': txid},
        headers=_pi_headers(),
    )

    expected = hmac.new(
        settings.PAYSTACK_SECRET_KEY.encode('utf-8'), raw_body or b'', sha512
    ).hexdigest()
    return hmac.compare_digest(expected, signature.strip())
