"""Tests for the Pi Browser payment gateway (marketplace checkout + boost).

Pi payments only run through the Pi Browser SDK: the server approves, verifies
and completes the payment with its own API key, then creates the order (or
activates the boost). These tests mock the Pi API so the whole chain runs
without touching the network, and assert the security properties that make the
flow trustworthy:

* an order is only created after Pi confirms the money,
* a payment aimed at another wallet, or for too little, is rejected,
* another user's Pi payment cannot be claimed,
* the manual-transfer claim is closed while the Pi Browser is required,
* a boost activates the moment Pi confirms — no admin review.
"""

from decimal import Decimal
from unittest import mock

from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import User
from dropshipping.payments import PaymentError
from shop.models import Product

from .models import (
    BoostOrder,
    BoostPlan,
    CartItem,
    Order,
    PaymentIntent,
    SellerVerification,
)

WALLET = 'G_DROP_HUB_TEST_WALLET_ADDRESS_0000000000'


@override_settings(
    PI_API_KEY='test_pi_api_key',
    PI_WALLET_ADDRESS=WALLET,
    PI_REQUIRE_BROWSER=True,
    PI_MANUAL_TRANSFER=False,
    PI_SANDBOX=True,
    PI_PER_USD=Decimal('2'),
)
class PiPaymentTestBase(TestCase):
    """Shared fixtures: a verified seller, a live product and a buyer with a cart."""

    def setUp(self):
        self.seller = User.objects.create_user(
            username='seller1', password='pw', role='seller', email='seller@example.com'
        )
        SellerVerification.objects.create(user=self.seller, status='verified')

        self.product = Product.objects.create(
            name='Test Headphones',
            seller=self.seller,
            price=Decimal('50.00'),
            stock=10,
            status='live',
        )

        self.buyer = User.objects.create_user(
            username='buyer1', password='pw', role='buyer', email='buyer@example.com'
        )
        self.cart_item = CartItem.objects.create(
            user=self.buyer, product=self.product, quantity=1
        )

    def pi_payment(self, amount, dest=WALLET, payment_id='pi_pay_1', uid=None):
        """A Pi ``GET /v2/payments`` response, as our verification helper sees it."""
        return {
            'id': payment_id,
            'amount': str(amount),
            'transaction': {'dest_address': dest, 'txid': None},
            'user_uid': {'uid': uid} if uid else None,
        }


class CheckoutPiPaymentTests(PiPaymentTestBase):
    def _start(self):
        self.client.force_login(self.buyer)
        return self.client.post(
            reverse('payment_start'),
            data={'payment_method': 'pi'},
            content_type='application/json',
        )

    def test_start_opens_the_pi_gateway_and_creates_no_order(self):
        response = self._start()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['mode'], 'sdk')
        self.assertTrue(response.json()['require_browser'])
        # Crucially: no manual-transfer instructions are handed out any more.
        self.assertNotIn('wallet_address', response.json())
        self.assertNotIn('amount_pi', response.json())
        self.assertFalse(Order.objects.exists())

        intent = PaymentIntent.objects.get(method='pi')
        self.assertEqual(intent.status, PaymentIntent.STATUS_PENDING)
        self.assertEqual(intent.purpose, PaymentIntent.PURPOSE_CHECKOUT)

    def test_complete_creates_the_order_after_pi_confirms(self):
        start = self._start()
        reference = start.json()['reference']

        with mock.patch(
            'dropshipping.payments.pi_verify_payment',
            return_value=self.pi_payment('100.00'),
        ) as verify, \
             mock.patch('dropshipping.payments.pi_complete_payment') as complete:
            response = self.client.post(
                reverse('pi_complete'),
                data={'payment_id': 'pi_pay_1', 'txid': 'TX123', 'reference': reference},
                content_type='application/json',
            )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['ok'])
        verify.assert_called_once()
        complete.assert_called_once_with('pi_pay_1', 'TX123')

        order = Order.objects.get()
        self.assertEqual(order.buyer, self.buyer)
        self.assertEqual(order.payment_method, 'pi')
        self.assertEqual(order.payment_reference, reference)
        # Stock only moves once the money is confirmed.
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 9)
        # The cart is emptied only on success.
        self.assertFalse(CartItem.objects.exists())

        intent = PaymentIntent.objects.get(reference=reference)
        self.assertTrue(intent.is_paid)

    def test_verify_rejects_a_payment_addressed_elsewhere(self):
        reference = self._start().json()['reference']

        with mock.patch(
            'dropshipping.payments.pi_get_payment',
            return_value=self.pi_payment('100.00', dest='SOMEONE_ELSES_WALLET'),
        ), mock.patch('dropshipping.payments.pi_complete_payment') as complete:
            response = self.client.post(
                reverse('pi_complete'),
                data={'payment_id': 'pi_pay_1', 'txid': 'TX123', 'reference': reference},
                content_type='application/json',
            )

        self.assertEqual(response.status_code, 402)
        self.assertIn('not addressed to DropHub', response.json()['error'])
        complete.assert_not_called()
        self.assertFalse(Order.objects.exists())

    def test_verify_rejects_an_underpayment(self):
        reference = self._start().json()['reference']

        with mock.patch(
            'dropshipping.payments.pi_get_payment',
            return_value=self.pi_payment('0.01'),
        ), mock.patch('dropshipping.payments.pi_complete_payment') as complete:
            response = self.client.post(
                reverse('pi_complete'),
                data={'payment_id': 'pi_pay_1', 'txid': 'TX123', 'reference': reference},
                content_type='application/json',
            )

        self.assertEqual(response.status_code, 402)
        self.assertIn('less than the amount due', response.json()['error'])
        complete.assert_not_called()
        self.assertFalse(Order.objects.exists())

    def test_recovery_settles_a_payment_pi_already_completed(self):
        # Pi reports a txid for a payment the buyer already broadcast (they
        # closed the page last time). Completing again would fail, so the server
        # must settle it as-is instead of stranding the money.
        reference = self._start().json()['reference']
        intent = PaymentIntent.objects.get(reference=reference)
        # Enough Pi, and Pi already broadcast the transaction.
        already_done = self.pi_payment(intent.amount)
        already_done['transaction']['txid'] = 'TX_OLD'

        with mock.patch(
            'dropshipping.payments.pi_get_payment', return_value=already_done
        ), mock.patch('dropshipping.payments.pi_complete_payment') as complete:
            response = self.client.post(
                reverse('pi_complete'),
                data={'payment_id': 'pi_pay_1', 'txid': 'TX_OLD', 'reference': reference},
                content_type='application/json',
            )

        self.assertEqual(response.status_code, 200)
        complete.assert_not_called()
        self.assertEqual(Order.objects.count(), 1)
        self.assertTrue(PaymentIntent.objects.get(reference=reference).is_paid)

    def test_cannot_complete_another_users_payment(self):
        reference = self._start().json()['reference']

        intruder = User.objects.create_user(username='intruder', password='pw', role='buyer')
        self.client.force_login(intruder)
        with mock.patch(
            'dropshipping.payments.pi_get_payment',
            return_value=self.pi_payment('100.00'),
        ), mock.patch('dropshipping.payments.pi_complete_payment') as complete:
            response = self.client.post(
                reverse('pi_complete'),
                data={'payment_id': 'pi_pay_1', 'txid': 'TX123', 'reference': reference},
                content_type='application/json',
            )

        # The intruder's reference does not match any intent of theirs.
        self.assertEqual(response.status_code, 404)
        complete.assert_not_called()
        self.assertFalse(Order.objects.exists())

    def test_manual_claim_is_closed_while_pi_browser_is_required(self):
        reference = self._start().json()['reference']

        response = self.client.post(
            reverse('pi_manual_claim'),
            data={'reference': reference},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 403)
        # No order and no "awaiting review" state from a self-reported transfer.
        self.assertFalse(Order.objects.exists())
        intent = PaymentIntent.objects.get(reference=reference)
        self.assertEqual(intent.status, PaymentIntent.STATUS_PENDING)

    def test_approve_stores_the_payment_id_on_the_right_intent(self):
        # Two Pi intents open at once — the callback must land on the one whose
        # reference the page sent, not on "any pending intent".
        first_reference = self._start().json()['reference']

        second_reference = 'PAY-SECONDINTENT01'
        PaymentIntent.objects.create(
            user=self.buyer,
            reference=second_reference,
            method='pi',
            purpose=PaymentIntent.PURPOSE_CHECKOUT,
            subtotal_usd=Decimal('50.00'),
            amount_usd=Decimal('50.00'),
            currency='PI',
            amount=Decimal('100.00'),
        )

        with mock.patch('dropshipping.payments.pi_approve_payment') as approve:
            response = self.client.post(
                reverse('pi_approve'),
                data={'payment_id': 'pi_pay_second', 'reference': second_reference},
                content_type='application/json',
            )

        self.assertEqual(response.status_code, 200)
        approve.assert_called_once_with('pi_pay_second')
        target = PaymentIntent.objects.get(reference=second_reference)
        self.assertEqual(target.provider_reference, 'pi_pay_second')
        other = PaymentIntent.objects.get(reference=first_reference)
        self.assertNotEqual(other.provider_reference, 'pi_pay_second')


class BoostPiPaymentTests(PiPaymentTestBase):
    def setUp(self):
        super().setUp()
        self.plan = BoostPlan.objects.create(
            name='Gold', price=Decimal('20.00'), duration_days=7, is_active=True
        )

    def _choose_pi(self):
        self.client.force_login(self.seller)
        return self.client.post(
            reverse('seller_boost_checkout', args=[self.product.pk]),
            data={'plan': self.plan.pk, 'payment_method': 'pi'},
        )

    def test_choosing_pi_creates_the_intent_and_opens_the_gateway_page(self):
        response = self._choose_pi()

        boost = BoostOrder.objects.get()
        self.assertRedirects(
            response, reverse('boost_pi_pay', args=[boost.pk]), fetch_redirect_response=False
        )

        self.assertEqual(boost.status, BoostOrder.STATUS_PENDING)
        self.assertEqual(boost.payment_method, 'pi')
        # The boost is NOT active until Pi confirms.
        self.assertIsNone(boost.paid_at)

        intent = PaymentIntent.objects.get(purpose=PaymentIntent.PURPOSE_BOOST)
        self.assertEqual(intent.method, 'pi')
        self.assertEqual(intent.provider_payload['boost_pk'], boost.pk)
        self.assertEqual(intent.provider_payload['purpose'], 'boost')

    def test_gateway_page_renders_for_the_pending_boost(self):
        self._choose_pi()
        boost = BoostOrder.objects.get()
        response = self.client.get(reverse('boost_pi_pay', args=[boost.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Pay with Pi')
        # The SDK is wired to this specific intent and the exact Pi amount.
        intent = PaymentIntent.objects.get(purpose=PaymentIntent.PURPOSE_BOOST)
        self.assertContains(response, 'data-reference="{}"'.format(intent.reference))
        self.assertContains(response, 'data-amount="{}"'.format(intent.amount))
        # And it talks to the real Pi approval/completion endpoints.
        self.assertContains(response, reverse('pi_approve'))
        self.assertContains(response, reverse('pi_complete'))
        self.assertContains(response, 'sdk.minepi.com/pi-sdk.js')

    def test_completion_activates_the_boost_immediately(self):
        self._choose_pi()
        boost = BoostOrder.objects.get()
        reference = PaymentIntent.objects.get(purpose=PaymentIntent.PURPOSE_BOOST).reference

        with mock.patch(
            'dropshipping.payments.pi_verify_payment',
            return_value=self.pi_payment('40.00', payment_id='pi_boost_1'),
        ) as verify, \
             mock.patch('dropshipping.payments.pi_complete_payment') as complete:
            response = self.client.post(
                reverse('pi_complete'),
                data={'payment_id': 'pi_boost_1', 'txid': 'TXBOOST', 'reference': reference},
                content_type='application/json',
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['redirect'], reverse('seller_products'))
        verify.assert_called_once()
        complete.assert_called_once_with('pi_boost_1', 'TXBOOST')

        boost.refresh_from_db()
        self.assertEqual(boost.status, BoostOrder.STATUS_PAID)
        self.assertIsNotNone(boost.paid_at)
        self.assertIsNotNone(boost.expires_at)
        self.assertEqual(boost.payment_reference, reference)
        # A boost purchase must never create a marketplace order.
        self.assertFalse(Order.objects.exists())
        # Nothing is left for an admin to review.
        self.assertFalse(
            PaymentIntent.objects.filter(status=PaymentIntent.STATUS_PI_PENDING).exists()
        )

    def test_underpaid_boost_is_rejected_and_stays_pending(self):
        self._choose_pi()
        reference = PaymentIntent.objects.get(purpose=PaymentIntent.PURPOSE_BOOST).reference

        with mock.patch(
            'dropshipping.payments.pi_get_payment',
            return_value=self.pi_payment('0.05', payment_id='pi_boost_2'),
        ), mock.patch('dropshipping.payments.pi_complete_payment') as complete:
            response = self.client.post(
                reverse('pi_complete'),
                data={'payment_id': 'pi_boost_2', 'txid': 'TXBOOST', 'reference': reference},
                content_type='application/json',
            )

        self.assertEqual(response.status_code, 402)
        complete.assert_not_called()
        boost = BoostOrder.objects.get()
        self.assertEqual(boost.status, BoostOrder.STATUS_PENDING)
        self.assertIsNone(boost.paid_at)

    def test_boost_without_pi_configured_falls_back_to_another_rail(self):
        with self.settings(PI_API_KEY=''):
            response = self._choose_pi()

        self.assertRedirects(
            response,
            reverse('seller_boost_checkout', args=[self.product.pk]),
            fetch_redirect_response=False,
        )
        # No orphan rows are left behind.
        self.assertFalse(BoostOrder.objects.exists())
        self.assertFalse(PaymentIntent.objects.exists())

    def test_manual_boost_claim_page_is_unreachable(self):
        self._choose_pi()
        boost = BoostOrder.objects.get()

        response = self.client.get(reverse('boost_pi_claim', args=[boost.pk]))

        self.assertRedirects(
            response,
            reverse('seller_boost_checkout', args=[boost.pk]),
            fetch_redirect_response=False,
        )


class PiBrowserHandoffTests(PiPaymentTestBase):
    """The out-of-Pi-Browser handoff must offer a real, working link.

    A plain browser cannot be redirected into a live Pi payment (the SDK only
    authenticates inside Pi Browser), so the page's job is to hand the buyer to
    the app. That link has to exist, point somewhere real, and stay hidden until
    it is actually needed.
    """

    def _checkout_page(self):
        self.client.force_login(self.buyer)
        return self.client.get(reverse('checkout-payment'))

    def test_checkout_page_hides_the_link_until_it_is_needed(self):
        response = self._checkout_page()
        self.assertContains(response, 'id="piPiBrowserLink"')
        # The hidden attribute alone is not enough: .ck-btn-ghost sets
        # display:inline-flex, so the page must carry the [hidden] override or
        # the link is visible on every load.
        self.assertContains(response, '.ck-btn-ghost[hidden]')

    def test_checkout_config_exposes_a_real_app_url(self):
        response = self._checkout_page()
        config = response.context['payment_config']
        app_url = config['pi']['app_url']
        self.assertTrue(app_url.startswith('https://'), app_url)
        self.assertTrue(config['pi']['require_browser'])

    def test_app_url_is_configurable(self):
        with self.settings(PI_BROWSER_APP_URL='https://example.test/pi-browser'):
            self.assertEqual(
                self._checkout_page().context['payment_config']['pi']['app_url'],
                'https://example.test/pi-browser',
            )

    def test_boost_page_offers_the_same_handoff(self):
        plan = BoostPlan.objects.create(
            name='Gold', price=Decimal('20.00'), duration_days=7, is_active=True
        )
        self.client.force_login(self.seller)
        self.client.post(
            reverse('seller_boost_checkout', args=[self.product.pk]),
            data={'plan': plan.pk, 'payment_method': 'pi'},
        )
        boost = BoostOrder.objects.get()
        response = self.client.get(reverse('boost_pi_pay', args=[boost.pk]))
        self.assertContains(response, 'id="bpiAppLink"')
        self.assertContains(response, 'bpiInstall')
        self.assertTrue(response.context['pi_app_url'].startswith('https://'))


class PiResumeAfterAppSwitchTests(PiPaymentTestBase):
    """Coming back from the Pi Browser app must not lose the payment.

    Pi Browser has its own cookie jar, so a buyer who installs it is signed out
    when they return. The cart survives (it is in the DB) but the pending Pi
    intent would not, which is what these tests pin down.
    """

    def _start_pi(self):
        self.client.force_login(self.buyer)
        response = self.client.post(
            reverse('payment_start'),
            data={'payment_method': 'pi'},
            content_type='application/json',
        )
        return response.json()['reference']

    def test_resume_endpoint_parks_the_payment_and_redirects_to_the_app(self):
        reference = self._start_pi()
        response = self.client.get(reverse('pi_resume'), {'reference': reference})

        self.assertRedirects(
            response,
            'https://play.google.com/store/apps/details?id=com.pi.browser',
            fetch_redirect_response=False,
        )
        self.assertEqual(response.cookies['drophub_pi_resume'].value, reference)

    def test_checkout_recognises_the_payment_after_the_switch(self):
        reference = self._start_pi()
        self.client.get(reverse('pi_resume'), {'reference': reference})

        # Same user, fresh visit (as if they came back in the app).
        response = self.client.get(reverse('checkout-payment'))
        self.assertEqual(response.context['pi_resume_reference'], reference)
        self.assertContains(response, 'piResumeBanner')
        self.assertContains(response, reference)

    def test_a_settled_payment_is_not_offered_for_resume(self):
        reference = self._start_pi()
        intent = PaymentIntent.objects.get(reference=reference)
        intent.status = PaymentIntent.STATUS_PAID
        intent.save(update_fields=['status'])

        self.client.get(reverse('pi_resume'), {'reference': reference})
        response = self.client.get(reverse('checkout-payment'))
        self.assertEqual(response.context['pi_resume_reference'], '')

    def test_tampered_cookie_cannot_expose_another_buyers_payment(self):
        reference = self._start_pi()

        # Re-open the page as a *different* buyer, carrying the cookie.
        intruder = User.objects.create_user(username='intruder2', password='pw', role='buyer')
        self.client.force_login(intruder)
        self.client.cookies['drophub_pi_resume'] = reference

        response = self.client.get(reverse('checkout-payment'))
        # The hint is ignored because the intent belongs to somebody else.
        self.assertEqual(response.context['pi_resume_reference'], '')

    def test_resume_ignores_a_reference_that_is_not_the_callers(self):
        reference = self._start_pi()
        self.client.force_login(self.seller)

        response = self.client.get(reverse('pi_resume'), {'reference': reference})
        # Still sent to the app, but nothing of theirs is parked.
        self.assertNotIn('drophub_pi_resume', response.cookies)


class PiVerificationHelperTests(PiPaymentTestBase):
    """Unit tests for payments.pi_verify_payment itself."""

    def test_accepts_a_matching_payment(self):
        from dropshipping import payments

        with mock.patch(
            'dropshipping.payments.pi_get_payment',
            return_value=self.pi_payment('100.00', payment_id='pi_ok'),
        ):
            result = payments.pi_verify_payment('pi_ok', expected_amount=Decimal('100.00'))
        self.assertEqual(result['id'], 'pi_ok')

    def test_rejects_when_pi_cannot_find_the_payment(self):
        from dropshipping import payments

        with mock.patch('dropshipping.payments.pi_get_payment', return_value={}):
            with self.assertRaises(PaymentError):
                payments.pi_verify_payment('nope', expected_amount=Decimal('1.00'))

    def test_rejects_a_payment_for_the_wrong_user(self):
        from dropshipping import payments

        with mock.patch(
            'dropshipping.payments.pi_get_payment',
            return_value=self.pi_payment('100.00', uid='someone-else'),
        ):
            with self.assertRaises(PaymentError):
                payments.pi_verify_payment(
                    'pi_x', expected_amount=Decimal('1.00'), expected_user='me'
                )


