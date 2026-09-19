from django.urls import path
from . import payment_views, views

urlpatterns = [
    # ── Dashboard homes ──────────────────────────────────────
    path("", views.dashboard_home, name="dashboard"),
    path("seller/", views.seller_dashboard, name="dashboard_seller"),
    path("buyer/", views.buyer_dashboard, name="dashboard_buyer"),
    path("admin/", views.admin_dashboard, name="dashboard_admin"),

    # ── Seller: verification ─────────────────────────────────
    path("seller/verification/", views.seller_verification_view, name="dashboard_seller_verification"),

    # ── Buyer: addresses & settings ──────────────────────────
    path("buyer/addresses/", views.buyer_addresses, name="dashboard_buyer_addresses"),
    path("buyer/addresses/<int:pk>/delete/", views.buyer_address_delete, name="buyer_address_delete"),
    path("buyer/addresses/<int:pk>/default/", views.buyer_address_set_default, name="buyer_address_set_default"),
    path("buyer/settings/", views.buyer_settings, name="buyer_settings"),

    # ── Wishlist ─────────────────────────────────────────────
    path("wishlist/toggle/", views.wishlist_toggle, name="wishlist_toggle"),
    path("wishlist/remove/<slug:slug>/", views.wishlist_remove, name="wishlist_remove"),

    # ── Seller: products ─────────────────────────────────────
    path("seller/products/", views.seller_products_view, name="seller_products"),
    path("seller/products/add/", views.seller_product_add, name="seller_product_add"),
    path("seller/products/<int:pk>/edit/", views.seller_product_edit, name="seller_product_edit"),
    path("seller/products/<int:product_pk>/boost/", views.seller_boost_checkout, name="seller_boost_checkout"),

    # ── Seller: orders ────────────────────────────────────────
    path("seller/orders/", views.seller_orders_view, name="seller_orders"),
    path("orders/<int:pk>/transit/", views.order_mark_in_transit, name="order_mark_in_transit"),
    path("orders/<int:pk>/delivered/", views.order_mark_delivered, name="order_mark_delivered"),

    # ── Buyer: order actions ──────────────────────────────────
    path("orders/<int:pk>/confirm/", views.order_buyer_confirm, name="order_buyer_confirm"),
    path("orders/<int:pk>/not-delivered/", views.order_not_delivered, name="order_not_delivered"),
    path("orders/<int:pk>/refund/", views.order_request_refund, name="order_request_refund"),

    # ── Order detail ──────────────────────────────────────────
    path("orders/<int:pk>/", views.order_detail, name="order_detail"),

    # ── Admin: order actions ──────────────────────────────────
    path("orders/<int:pk>/release-payout/", views.order_release_payout, name="order_release_payout"),
    path("orders/<int:pk>/refund/approve/", views.order_admin_refund, name="order_admin_refund"),

    # ── Buyer: refund complaint reply ─────────────────────────
    path("refund-complaints/<int:complaint_pk>/reply/", views.buyer_refund_reply, name="buyer_refund_reply"),

    # ── Admin: refund complaints ──────────────────────────────
    path("admin/refunds/", views.admin_refund_complaints, name="admin_refund_complaints"),
    path("admin/refunds/<int:pk>/", views.admin_refund_complaint_detail, name="admin_refund_complaint_detail"),

    # ── Admin: seller payouts ─────────────────────────────────
    path("admin/seller-payouts/", views.admin_seller_payouts, name="admin_seller_payouts"),

    # ── Seller: payouts ───────────────────────────────────────
    path("seller/payouts/save-method/", views.seller_save_payout_method, name="seller_save_payout_method"),
    path("seller/payouts/delete-method/<int:pk>/", views.seller_delete_payout_method, name="seller_delete_payout_method"),
    path("seller/payouts/set-default/<int:pk>/", views.seller_set_default_payout_method, name="seller_set_default_payout_method"),
    path("seller/payouts/request/", views.seller_request_payout, name="seller_request_payout"),

    # ── Admin: verifications ──────────────────────────────────
    path("admin/verifications/", views.admin_verifications_view, name="admin_verifications"),
    path("admin/verifications/<int:pk>/<str:action>/", views.admin_verification_action, name="admin_verification_action"),
    path("admin/verifications/<int:pk>/detail/", views.admin_verification_detail, name="admin_verification_detail"),
    path("admin/posts/", views.admin_posts, name="admin_posts"),
    path("admin/posts/create/", views.admin_post_create, name="admin_post_create"),
    path("admin/posts/<int:pk>/edit/", views.admin_post_edit, name="admin_post_edit"),
    path("admin/posts/<int:pk>/delete/", views.admin_post_delete, name="admin_post_delete"),

    # ── Admin: users ──────────────────────────────────────────
    path("admin/users/", views.admin_users_view, name="admin_users_view"),
    path("admin/users/<int:pk>/toggle-active/", views.admin_user_toggle_active, name="admin_user_toggle_active"),
    path("admin/users/<int:pk>/delete/", views.admin_user_delete, name="admin_user_delete"),

    # ── Admin: products ───────────────────────────────────────
    path("admin/products/", views.admin_products_view, name="admin_products_view"),
    path("admin/products/<int:pk>/toggle-status/", views.admin_product_toggle_status, name="admin_product_toggle_status"),
    path("admin/products/<int:pk>/delete/", views.admin_product_delete, name="admin_product_delete"),

    # ── Admin: featured / boost plans ────────────────────────
    path("admin/featured/", views.admin_featured_view, name="admin_featured_view"),
    path("admin/boost-plans/create/", views.admin_boost_plan_create, name="admin_boost_plan_create"),
    path("admin/boost-plans/<int:pk>/delete/", views.admin_boost_plan_delete, name="admin_boost_plan_delete"),
    path("admin/boost-orders/<int:pk>/remove/", views.admin_boost_order_remove, name="admin_boost_order_remove"),

    # ── Admin: currency rates ─────────────────────────────────
    path("admin/currency-rates/", views.admin_currency_rates, name="admin_currency_rates"),

    # ── Admin: Pi payment verification ───────────────────────
    path("admin/pi-payments/", views.admin_pi_payments, name="admin_pi_payments"),
    path("admin/pi-payments/<int:pk>/confirm/", views.admin_pi_confirm, name="admin_pi_confirm"),
    path("admin/pi-payments/<int:pk>/reject/", views.admin_pi_reject, name="admin_pi_reject"),
    path("admin/pi-payments/<int:pk>/reclaim/", views.admin_pi_reclaim, name="admin_pi_reclaim"),

    # ── Cart API ──────────────────────────────────────────────
    path("cart/add/<int:product_pk>/", views.cart_add, name="cart_add"),
    path("cart/update/<int:product_pk>/", views.cart_update, name="cart_update"),
    path("cart/remove/<int:product_pk>/", views.cart_remove, name="cart_remove"),
    path("cart/sync/", views.cart_sync, name="cart_sync"),
    path("checkout/payment/", views.checkout_payment, name="checkout_payment"),

    # ── Checkout payments (Paystack · PayPal · Pi Network) ────
    # Starting a payment never creates an order: that only happens once the
    # provider confirms the money through one of the endpoints below.
    path("checkout/start/", payment_views.payment_start, name="payment_start"),
    # Legacy alias — old pages posted straight to this URL.
    path("checkout/complete/", payment_views.payment_start, name="checkout_complete"),
    # Paystack: inline popup verification, hosted-flow callback and webhook.
    path("checkout/paystack/verify/", payment_views.paystack_verify_payment, name="paystack_verify"),
    path("checkout/paystack/callback/", payment_views.paystack_callback, name="paystack_callback"),
    path("checkout/paystack/webhook/", payment_views.paystack_webhook, name="paystack_webhook"),
    # PayPal: capture from the SDK buttons, plus the redirect fallbacks.
    path("checkout/paypal/capture/", payment_views.paypal_capture_payment, name="paypal_capture"),
    path("checkout/paypal/return/", payment_views.paypal_return, name="paypal_return"),
    path("checkout/paypal/cancel/", payment_views.paypal_cancel, name="paypal_cancel"),
    # Pi Network: Pi Browser approve/complete and the manual-transfer claim.
    path("checkout/pi/approve/", payment_views.pi_approve, name="pi_approve"),
    path("checkout/pi/complete/", payment_views.pi_complete, name="pi_complete"),
    path("checkout/pi/manual/", payment_views.pi_manual_claim, name="pi_manual_claim"),

    # ── Generic section loader (must stay last) ───────────────
    path("<str:role>/<str:section>/", views.dashboard_section, name="dashboard_section"),
]
