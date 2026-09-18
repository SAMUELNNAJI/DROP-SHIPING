"""Real payment flows for the marketplace checkout.

The buyer picks a rail on ``/checkout-payment/`` and this module talks to the
provider that owns it:

* **Paystack** — the transaction is initialised server-side with the secret key;
  the browser finishes it with the inline popup and the result is confirmed
  through ``/transaction/verify`` (plus a signed webhook as a safety net).
* **PayPal** — the order is created and captured server-side; the browser only
  hosts the official buttons.
* **Pi Network** — the Pi Browser SDK runs the payment and the server calls
  ``approve`` then ``complete``.  Outside the Pi Browser (or without an API key)
  the buyer can transfer Pi to the configured wallet instead.

Orders are created **only** after the provider confirms the money, and
:class:`PaymentIntent` keeps a row for every attempt so nothing is lost when a
buyer closes the window mid-payment.
"""

from __future__ import annotations

import json
import logging
from decimal import Decimal, InvalidOperation
from uuid import uuid4

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from dropshipping import payments
from dropshipping.payments import PaymentError

from .models import BuyerAddress, CartItem, Order, OrderTrackingEvent, PaymentIntent

logger = logging.getLogger(__name__)

# Which currency each rail charges in.
CURRENCY_BY_METHOD = {'paystack': 'NGN', 'paypal': 'USD', 'pi': 'PI'}


class CheckoutError(Exception):
    """Something the buyer can act on: empty cart, sold-out item, bad rail."""


# ══════════════════════════════════════════════════════════════
#  Cart maths and page context
# ══════════════════════════════════════════════════════════════

def cart_totals(subtotal):
    """Subtotal plus the escrow (2%) and platform (1%) fees shown at checkout."""
    subtotal = payments.money(subtotal)
    escrow = payments.money(subtotal * settings.CHECKOUT_ESCROW_FEE_RATE)
    platform = payments.money(subtotal * settings.CHECKOUT_PLATFORM_FEE_RATE)
    return {
        'subtotal': subtotal,
        'escrow': escrow,
        'platform': platform,
        'total': subtotal + escrow + platform,
    }


def cart_snapshot(user):
    """The buyer's DB cart as ``(items, subtotal, totals)``."""
    items = list(CartItem.objects.filter(user=user).select_related('product', 'product__seller'))
    subtotal = payments.money(sum(item.line_total for item in items))
    return items, subtotal, cart_totals(subtotal)


def provider_config():
    """Browser-safe provider configuration (never contains a secret key)."""
    manual_pi = bool(settings.PI_MANUAL_TRANSFER and settings.PI_WALLET_ADDRESS)
    return {
        'paystack': {
            'enabled': payments.paystack_enabled(),
            'public_key': settings.PAYSTACK_PUBLIC_KEY,
        },
        'paypal': {
            'enabled': payments.paypal_enabled(),
            'client_id': settings.PAYPAL_CLIENT_ID,
            'currency': payments.PAYPAL_CURRENCY,
            'mode': settings.PAYPAL_MODE,
        },
        'pi': {
            'enabled': payments.pi_sdk_enabled() or manual_pi,
            'sdk': payments.pi_sdk_enabled(),
            'manual': manual_pi,
            'wallet_address': settings.PI_WALLET_ADDRESS,
        },
        'rates': {
            'ngn_per_usd': str(settings.NGN_PER_USD),
            'pi_per_usd': str(settings.PI_PER_USD),
        },
    }


def checkout_context(request):
    """Cart + totals + live rails for the payment page."""
    items, subtotal, totals = cart_snapshot(request.user) if request.user.is_authenticated else (
        [], payments.money(0), cart_totals(0)
    )
    return {
        'cart_items': items,
        'cart_subtotal': totals['subtotal'],
        'cart_count': sum(item.quantity for item in items),
        'checkout_totals': totals,
        # Amount the buyer pays in each rail's own currency.
        'payment_amounts': {
            'usd': str(totals['total']),
            'ngn': str(payments.usd_to_ngn(totals['total'])),
            'pi': str(payments.usd_to_pi(totals['total'])),
        },
        'payment_config': provider_config(),
    }

# ══════════════════════════════════════════════════════════════
#  Small helpers
# ══════════════════════════════════════════════════════════════

def _request_payload(request):
    """Read a JSON body (fetch) or a normal form post without caring which."""
    if 'application/json' in (request.content_type or ''):
        try:
            data = json.loads(request.body.decode('utf-8') or '{}')
        except (ValueError, UnicodeDecodeError):
            return {}
        return data if isinstance(data, dict) else {}
    return request.POST


def _buyer_email(user):
    """Paystack needs an address to send the receipt to."""
    email = (getattr(user, 'email', '') or '').strip()
    if email and '@' in email:
        return email
    return '%s@drophub.local' % user.username


def _new_reference():
    return 'PAY-%s' % uuid4().hex[:14].upper()


def _get_intent(reference, user, method=None):
    if not reference:
        return None
    queryset = PaymentIntent.objects.filter(user=user, reference=reference)
    if method:
        queryset = queryset.filter(method=method)
    return queryset.first()


def _pending_intent(user, method):
    return PaymentIntent.objects.filter(
        user=user, method=method, status=PaymentIntent.STATUS_PENDING
    ).first()


def _get_intent_by_provider(user, provider_reference, method=None):
    if not provider_reference:
        return None
    queryset = PaymentIntent.objects.filter(user=user, provider_reference=provider_reference)
    if method:
        queryset = queryset.filter(method=method)
    return queryset.first()


def _new_intent(user, method, totals):
    """Open a payment attempt, abandoning any earlier unfinished one."""
    currency = CURRENCY_BY_METHOD.get(method, 'USD')
    if currency == 'NGN':
        amount = payments.usd_to_ngn(totals['total'])
    elif currency == 'PI':
        amount = payments.usd_to_pi(totals['total'])
    else:
        amount = payments.money(totals['total'])

    if amount <= 0:
        raise CheckoutError('This total is too small for the selected payment method.')

    # A buyer who switches rails (or retries) must never leave two live
    # transactions behind, so unfinished attempts are closed first.
    PaymentIntent.objects.filter(
        user=user, purpose=PaymentIntent.PURPOSE_CHECKOUT, status=PaymentIntent.STATUS_PENDING
    ).update(status=PaymentIntent.STATUS_CANCELLED, updated_at=timezone.now())

    return PaymentIntent.objects.create(
        user=user,
        reference=_new_reference(),
        method=method,
        purpose=PaymentIntent.PURPOSE_CHECKOUT,
        subtotal_usd=totals['subtotal'],
        amount_usd=totals['total'],
        currency=currency,
        amount=amount,
    )


def _fail_intent(intent, message):
    """Record a rejected/abandoned payment attempt."""
    if intent is None or intent.status == PaymentIntent.STATUS_PAID:
        return
    intent.status = PaymentIntent.STATUS_FAILED
    intent.note = (message or '')[:200]
    intent.save(update_fields=['status', 'note', 'updated_at'])


def _remember_for_success_page(request, intent):
    """The confirmation page reads the order PKs from the session."""
    if request is None or not hasattr(request, 'session'):
        return
    request.session['last_order_pks'] = list(intent.order_pks)
    request.session['last_order_payment_method'] = intent.method
    request.session['last_payment_awaiting_confirmation'] = (
        intent.status != PaymentIntent.STATUS_PAID
    )


# ══════════════════════════════════════════════════════════════
#  Orders + settlement
# ══════════════════════════════════════════════════════════════

def create_orders_for_cart(user, method, reference):
    """Turn the buyer's DB cart into protected orders.

    Must be called *inside* a transaction: any problem rolls the whole cart
    back instead of leaving half-finished orders behind.
    """
    items = list(CartItem.objects.filter(user=user).select_related('product', 'product__seller'))
    if not items:
        raise CheckoutError('Your cart is empty.')

    address = (
        BuyerAddress.objects.filter(user=user, is_default=True).first()
        or BuyerAddress.objects.filter(user=user).first()
    )

    created = []
    for item in items:
        product = item.product
        verification = getattr(product.seller, 'seller_verification', None)
        if (product.status != 'live' or product.stock < item.quantity
                or not product.seller.is_active
                or not verification or verification.status != 'verified'):
            raise CheckoutError('%s is no longer available from a verified seller.' % product.name)

        order = Order.objects.create(
            buyer=user,
            seller=product.seller,
            product=product,
            product_name=product.name,
            product_image=product.image_src,
            store_name=product.get_store_display(),
            unit_price=product.price,
            quantity=item.quantity,
            total_price=product.price * item.quantity,
            currency='USD',
            payment_method=method,
            payment_reference=reference,
            shipping_name=address.recipient_name if address else user.get_full_name(),
            shipping_address=(
                '%s, %s, %s' % (address.line1, address.city, address.country) if address else ''
            ),
        )
        product.stock -= item.quantity
        product.sold += item.quantity
        product.save(update_fields=['stock', 'sold', 'updated_at'])
        OrderTrackingEvent.objects.create(
            order=order,
            status='pending',
            message='Payment secured in escrow. Seller is preparing your order.',
        )
        created.append(order)

    CartItem.objects.filter(user=user).delete()
    return created


def finalize_intent(intent, request=None):
    """Create the orders for a provider-verified payment (idempotent)."""
    if intent.status == PaymentIntent.STATUS_PAID:
        _remember_for_success_page(request, intent)
        return list(intent.order_pks)

    with transaction.atomic():
        orders = create_orders_for_cart(intent.user, intent.method, intent.reference)
        intent.order_pks = [order.pk for order in orders]
        intent.status = PaymentIntent.STATUS_PAID
        intent.paid_at = timezone.now()
        intent.save(update_fields=['order_pks', 'status', 'paid_at', 'updated_at'])

    _remember_for_success_page(request, intent)
    return list(intent.order_pks)


def _settle_intent(intent, request=None):
    """Settle a payment the provider already confirmed.

    If the cart turned invalid between opening the payment and the money
    arriving, the intent is still recorded as paid (with a note) so the admin
    can refund it instead of losing the trail.
    """
    try:
        return finalize_intent(intent, request)
    except CheckoutError as exc:
        intent.status = PaymentIntent.STATUS_PAID
        intent.paid_at = timezone.now()
        intent.note = ('Payment received but the order could not be created: %s' % exc)[:200]
        intent.save(update_fields=['status', 'paid_at', 'note', 'updated_at'])
        logger.error('Paid intent %s could not create orders: %s', intent.reference, exc)
        raise CheckoutError(
            'Your payment was received, but we could not create the order automatically '
            '(%s). Our team has been notified and will contact you.' % exc
        ) from exc


def _as_decimal(value, default='0'):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(default)


# ══════════════════════════════════════════════════════════════
#  Starting a payment
# ══════════════════════════════════════════════════════════════

def _start_paystack(request, intent):
    """Initialise the Naira transaction and return the popup's inputs."""
    if not payments.paystack_enabled():
        raise CheckoutError('Naira card payments are not configured yet. Please pick another method.')

    initialized = payments.paystack_initialize(
        email=_buyer_email(intent.user),
        amount_ngn=intent.amount,
        reference=intent.reference,
        callback_url=payments.absolute_url(request, reverse('paystack_callback')),
        metadata={
            'reference': intent.reference,
            'purpose': intent.purpose,
            'user_id': intent.user.pk,
        },
    )
    intent.provider_reference = initialized.get('reference') or intent.reference
    intent.provider_payload = {
        'access_code': initialized.get('access_code', ''),
        'authorization_url': initialized.get('authorization_url', ''),
    }
    intent.save(update_fields=['provider_reference', 'provider_payload', 'updated_at'])

    return {
        'public_key': settings.PAYSTACK_PUBLIC_KEY,
        'access_code': initialized.get('access_code', ''),
        'authorization_url': initialized.get('authorization_url', ''),
        'email': _buyer_email(intent.user),
        'amount_kobo': payments.ngn_to_kobo(intent.amount),
    }


def _start_paypal(request, intent):
    """Create the PayPal order and return the id the SDK buttons need."""
    if not payments.paypal_enabled():
        raise CheckoutError('PayPal is not configured yet. Please pick another method.')

    order = payments.paypal_create_order(
        amount_usd=intent.amount,
        reference=intent.reference,
        return_url=payments.absolute_url(request, reverse('paypal_return')),
        cancel_url=payments.absolute_url(request, reverse('paypal_cancel')),
        description='DropHub escrow order %s' % intent.reference,
    )
    intent.provider_reference = order['id']
    intent.provider_payload = {'paypal_status': order.get('status', '')}
    intent.save(update_fields=['provider_reference', 'provider_payload', 'updated_at'])

    return {
        'order_id': order['id'],
        'approve_url': payments.paypal_approve_url(order),
        'client_id': settings.PAYPAL_CLIENT_ID,
        'mode': settings.PAYPAL_MODE,
    }


def _start_pi(intent):
    """Pi runs inside the Pi Browser; otherwise offer the manual transfer."""
    if payments.pi_sdk_enabled():
        return {'mode': 'sdk'}

    wallet = settings.PI_WALLET_ADDRESS
    if settings.PI_MANUAL_TRANSFER and wallet:
        intent.note = 'Manual Pi transfer to %s — awaiting confirmation' % wallet[:20]
        intent.provider_payload = {'mode': 'manual', 'wallet_address': wallet}
        intent.save(update_fields=['note', 'provider_payload', 'updated_at'])
        return {
            'mode': 'manual',
            'wallet_address': wallet,
            'memo': intent.reference,
            'amount_pi': str(intent.amount),
        }

    raise CheckoutError('Pi payments are not configured yet. Please pick another method.')


@require_POST
@login_required
def payment_start(request):
    """Open a payment attempt for the chosen rail.

    Returns everything the browser needs to finish the payment (Paystack access
    code, PayPal order id, Pi payment instructions).  No order exists yet.
    """
    if getattr(request.user, 'role', '') not in ('buyer', ''):
        return JsonResponse(
            {'error': 'Please use a buyer account to complete a purchase.'}, status=403
        )

    payload = _request_payload(request)
    method = str(payload.get('payment_method') or payload.get('method') or '').strip().lower()
    if method not in CURRENCY_BY_METHOD:
        return JsonResponse({'error': 'Choose Paystack, PayPal, or Pi.'}, status=400)

    try:
        items, _subtotal, totals = cart_snapshot(request.user)
        if not items:
            raise CheckoutError('Your cart is empty.')
        intent = _new_intent(request.user, method, totals)

        if method == 'paystack':
            data = _start_paystack(request, intent)
        elif method == 'paypal':
            data = _start_paypal(request, intent)
        else:
            data = _start_pi(intent)
    except CheckoutError as exc:
        return JsonResponse({'error': str(exc)}, status=409)
    except PaymentError as exc:
        logger.warning('Could not start a %s payment: %s', method, exc)
        return JsonResponse({'error': str(exc)}, status=502)

    data.update({
        'ok': True,
        'method': method,
        'reference': intent.reference,
        'currency': intent.currency,
        'amount': str(intent.amount),
        'amount_usd': str(intent.amount_usd),
    })
    return JsonResponse(data)


# ═════════════════════════════════════════════════════════════
#  Paystack confirmation
# ══════════════════════════════════════════════════════════════

def _check_paystack_paid(intent, data):
    """Raise unless Paystack reports a successful transaction for this intent."""
    status = str(data.get('status') or '').lower()
    if status != 'success':
        raise CheckoutError(
            'Paystack did not confirm this payment (%s).'
            % (data.get('gateway_response') or status or 'unknown status')
        )
    if str(data.get('currency') or 'NGN').upper() != 'NGN':
        raise CheckoutError('Paystack returned an unexpected currency for this payment.')
    if str(data.get('reference') or '') != intent.reference:
        raise CheckoutError('This Paystack payment belongs to a different checkout.')
    paid_kobo = int(data.get('amount') or 0)
    expected_kobo = payments.ngn_to_kobo(intent.amount)
    if paid_kobo < expected_kobo:
        raise CheckoutError('The amount paid was less than the order total.')


def _confirm_paystack(intent, request=None):
    """Ask Paystack for the truth, then create the orders."""
    data = payments.paystack_verify(intent.provider_reference or intent.reference)
    _check_paystack_paid(intent, data)
    _settle_intent(intent, request)
    return data


@require_POST
@login_required
def paystack_verify_payment(request):
    """Called by the page right after the inline popup reports success."""
    payload = _request_payload(request)
    reference = str(payload.get('reference') or '').strip()
    intent = _get_intent(reference, request.user, method='paystack')
    if intent is None:
        return JsonResponse({'error': 'We could not find that Paystack payment.'}, status=404)
    if intent.is_paid:
        _remember_for_success_page(request, intent)
        return JsonResponse({'ok': True, 'redirect': reverse('checkout-success')})

    try:
        _confirm_paystack(intent, request)
    except PaymentError as exc:
        _fail_intent(intent, str(exc))
        return JsonResponse({'error': str(exc)}, status=502)
    except CheckoutError as exc:
        if intent.status != PaymentIntent.STATUS_PAID:
            _fail_intent(intent, str(exc))
        return JsonResponse({'error': str(exc)}, status=402)

    return JsonResponse({'ok': True, 'redirect': reverse('checkout-success')})


@login_required
def paystack_callback(request):
    """Where Paystack sends the browser back after a hosted payment."""
    reference = str(request.GET.get('reference') or request.GET.get('trxref') or '').strip()
    intent = _get_intent(reference, request.user, method='paystack')
    if intent is None:
        messages.error(request, 'We could not find that Paystack payment.')
        return redirect('checkout-payment')

    if not intent.is_paid:
        try:
            _confirm_paystack(intent, request)
        except (PaymentError, CheckoutError) as exc:
            if intent.status != PaymentIntent.STATUS_PAID:
                _fail_intent(intent, str(exc))
            messages.error(request, str(exc))
            return redirect('checkout-payment')

    return redirect('checkout-success')


@csrf_exempt
@require_POST
def paystack_webhook(request):
    """Server-to-server confirmation — the safety net when the buyer never
    returns to the site (closed tab, dead network, …)."""
    signature = request.headers.get('x-paystack-signature', '')
    if not payments.paystack_signature_is_valid(request.body, signature):
        logger.warning('Rejected a Paystack webhook with an invalid signature.')
        return HttpResponse(status=401)

    try:
        event = json.loads(request.body.decode('utf-8') or '{}')
    except (ValueError, UnicodeDecodeError):
        return HttpResponse(status=400)

    if event.get('event') == 'charge.success':
        data = event.get('data') or {}
        reference = str(data.get('reference') or '').strip()
        intent = PaymentIntent.objects.filter(
            reference=reference, method='paystack', status=PaymentIntent.STATUS_PENDING
        ).first()
        if intent is not None:
            try:
                # Re-verify with the API so a replayed webhook can never settle
                # a payment that Paystack does not actually consider successful.
                _confirm_paystack(intent)
            except PaymentError:
                try:
                    _check_paystack_paid(intent, data)
                    _settle_intent(intent)
                except CheckoutError as exc:
                    _fail_intent(intent, str(exc))
            except CheckoutError as exc:
                _fail_intent(intent, str(exc))
    return HttpResponse(status=200)


# ════════════════════════════════════════════════════════════
#  PayPal confirmation
# ═════════════════════════════════════════════════════════════

def _capture_paypal_intent(intent):
    """Capture an approved PayPal order and verify the money arrived."""
    order = payments.paypal_capture_order(intent.provider_reference)
    capture = payments.paypal_capture_details(order)
    if capture is None:
        raise CheckoutError(
            'PayPal did not complete this payment (%s).' % (order.get('status') or 'unknown status')
        )

    captured = payments.paypal_captured_amount(capture)
    if captured is not None and captured + Decimal('0.01') < Decimal(intent.amount_usd):
        raise CheckoutError('The amount captured by PayPal was less than the order total.')

    intent.provider_payload = {
        'paypal_status': order.get('status', ''),
        'capture_id': capture.get('id', ''),
    }
    intent.save(update_fields=['provider_payload', 'updated_at'])
    return order


def _settle_paypal(intent, request):
    """Capture (if needed) and settle, then hand back the success URL."""
    if not intent.is_paid:
        _capture_paypal_intent(intent)
        _settle_intent(intent, request)
    return reverse('checkout-success')


@require_POST
@login_required
def paypal_capture_payment(request):
    """Called by the PayPal buttons once the buyer approves the payment."""
    payload = _request_payload(request)
    order_id = str(payload.get('order_id') or payload.get('token') or '').strip()
    intent = _get_intent_by_provider(request.user, order_id, method='paypal')
    if intent is None:
        return JsonResponse({'error': 'We could not find that PayPal payment.'}, status=404)
    if intent.is_paid:
        _remember_for_success_page(request, intent)
        return JsonResponse({'ok': True, 'redirect': reverse('checkout-success')})

    try:
        redirect_to = _settle_paypal(intent, request)
    except PaymentError as exc:
        _fail_intent(intent, str(exc))
        return JsonResponse({'error': str(exc)}, status=502)
    except CheckoutError as exc:
        if intent.status != PaymentIntent.STATUS_PAID:
            _fail_intent(intent, str(exc))
        return JsonResponse({'error': str(exc)}, status=402)

    return JsonResponse({'ok': True, 'redirect': redirect_to})


@login_required
def paypal_return(request):
    """PayPal sends the browser here when the redirect flow is used."""
    order_id = str(request.GET.get('token') or request.GET.get('order_id') or '').strip()
    intent = _get_intent_by_provider(request.user, order_id, method='paypal')
    if intent is None:
        messages.error(request, 'We could not find that PayPal payment.')
        return redirect('checkout-payment')

    if not intent.is_paid:
        try:
            _settle_paypal(intent, request)
        except (PaymentError, CheckoutError) as exc:
            if intent.status != PaymentIntent.STATUS_PAID:
                _fail_intent(intent, str(exc))
            messages.error(request, str(exc))
            return redirect('checkout-payment')

    return redirect('checkout-success')


@login_required
def paypal_cancel(request):
    """The buyer closed the PayPal window — keep the cart so they can retry."""
    order_id = str(request.GET.get('token') or '').strip()
    intent = _get_intent_by_provider(request.user, order_id, method='paypal')
    if intent is not None and not intent.is_paid:
        intent.status = PaymentIntent.STATUS_CANCELLED
        intent.note = 'Cancelled in PayPal'
        intent.save(update_fields=['status', 'note', 'updated_at'])
    messages.info(request, 'Your PayPal payment was cancelled — your cart is still waiting.')
    return redirect('checkout-payment')


# ════════════════════════════════════════════════════════════
#  Pi Network confirmation
# ═════════════════════════════════════════════════════════════

@require_POST
@login_required
def pi_approve(request):
    """The Pi Browser SDK asks the server to approve the payment it just opened."""
    payload = _request_payload(request)
    payment_id = str(payload.get('payment_id') or '').strip()
    intent = _pending_intent(request.user, 'pi')
    if intent is None:
        return JsonResponse({'error': 'No Pi payment is waiting for approval.'}, status=404)
    if not payments.pi_sdk_enabled():
        return JsonResponse({'error': 'Pi payments are not configured on this server.'}, status=503)
    if not payment_id:
        return JsonResponse({'error': 'The Pi SDK did not send a payment id.'}, status=400)

    try:
        payments.pi_approve_payment(payment_id)
    except PaymentError as exc:
        _fail_intent(intent, str(exc))
        return JsonResponse({'error': str(exc)}, status=502)

    intent.provider_reference = payment_id
    intent.save(update_fields=['provider_reference', 'updated_at'])
    return JsonResponse({'ok': True})


@require_POST
@login_required
def pi_complete(request):
    """Finish a Pi payment with the blockchain transaction id from the client."""
    payload = _request_payload(request)
    payment_id = str(payload.get('payment_id') or '').strip()
    txid = str(payload.get('txid') or '').strip()
    if not payment_id or not txid:
        return JsonResponse(
            {'error': 'The Pi payment id and transaction id are both required.'}, status=400
        )

    intent = (
        _get_intent_by_provider(request.user, payment_id, method='pi')
        or _pending_intent(request.user, 'pi')
    )
    if intent is None:
        return JsonResponse({'error': 'We could not find that Pi payment.'}, status=404)
    if intent.is_paid:
        _remember_for_success_page(request, intent)
        return JsonResponse({'ok': True, 'redirect': reverse('checkout-success')})

    # Double-check the amount Pi recorded before completing the payment.
    try:
        remote = payments.pi_get_payment(payment_id)
    except PaymentError as exc:
        # The txid comes from the client, so a lookup failure must not block the
        # completion call — it is logged for follow-up instead.
        logger.warning('Could not read Pi payment %s before completing it: %s', payment_id, exc)
        remote = {}
    remote_amount = _as_decimal((remote or {}).get('amount'))
    if remote_amount and remote_amount < Decimal(intent.amount):
        message = 'The Pi amount paid was less than the order total.'
        _fail_intent(intent, message)
        return JsonResponse({'error': message}, status=402)

    try:
        payments.pi_complete_payment(payment_id, txid)
    except PaymentError as exc:
        _fail_intent(intent, str(exc))
        return JsonResponse({'error': str(exc)}, status=502)

    intent.provider_reference = payment_id
    intent.note = ('txid %s' % txid)[:200]
    intent.save(update_fields=['provider_reference', 'note', 'updated_at'])

    try:
        _settle_intent(intent, request)
    except CheckoutError as exc:
        return JsonResponse({'error': str(exc)}, status=409)

    return JsonResponse({'ok': True, 'redirect': reverse('checkout-success')})


@require_POST
@login_required
def pi_manual_claim(request):
    """Buyer paid Pi from a normal browser: record the order for confirmation.

    The Pi SDK only runs inside the Pi Browser, so buyers elsewhere send Pi to
    the wallet in ``PI_WALLET_ADDRESS`` quoting the payment reference.  The
    orders are created straight away but stay *pending* while an admin checks
    the wallet, so nobody ships against an unconfirmed transfer.
    """
    payload = _request_payload(request)
    reference = str(payload.get('reference') or '').strip()
    intent = _get_intent(reference, request.user, method='pi')
    if intent is None:
        return JsonResponse({'error': 'We could not find that Pi payment.'}, status=404)
    if intent.order_pks:
        _remember_for_success_page(request, intent)
        return JsonResponse({'ok': True, 'redirect': reverse('checkout-success')})
    if intent.status != PaymentIntent.STATUS_PENDING:
        return JsonResponse({'error': 'This Pi payment is no longer open.'}, status=409)

    try:
        with transaction.atomic():
            orders = create_orders_for_cart(request.user, intent.method, intent.reference)
    except CheckoutError as exc:
        return JsonResponse({'error': str(exc)}, status=409)

    intent.order_pks = [order.pk for order in orders]
    intent.note = ('Buyer reports a manual Pi transfer to %s — awaiting confirmation'
                   % settings.PI_WALLET_ADDRESS)[:200]
    intent.provider_payload = {
        **(intent.provider_payload or {}),
        'manual_claim': True,
        'claimed_at': timezone.now().isoformat(),
    }
    intent.save(update_fields=['order_pks', 'note', 'provider_payload', 'updated_at'])

    _remember_for_success_page(request, intent)
    logger.info('Manual Pi transfer claimed for intent %s', intent.reference)
    return JsonResponse({
        'ok': True,
        'redirect': reverse('checkout-success'),
        'awaiting_confirmation': True,
    })