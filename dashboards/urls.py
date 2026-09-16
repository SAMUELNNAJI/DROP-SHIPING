from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard_home, name="dashboard"),
    path("seller/", views.seller_dashboard, name="dashboard_seller"),
    path("buyer/", views.buyer_dashboard, name="dashboard_buyer"),
    path("admin/", views.admin_dashboard, name="dashboard_admin"),
    path("seller/verification/", views.seller_verification_view, name="dashboard_seller_verification"),
    path("buyer/addresses/", views.buyer_addresses, name="dashboard_buyer_addresses"),
    path("buyer/addresses/<int:pk>/delete/", views.buyer_address_delete, name="buyer_address_delete"),
    path("buyer/addresses/<int:pk>/default/", views.buyer_address_set_default, name="buyer_address_set_default"),
    path("buyer/settings/", views.buyer_settings, name="buyer_settings"),

    # Wishlist
    path("wishlist/toggle/", views.wishlist_toggle, name="wishlist_toggle"),
    path("wishlist/remove/<slug:slug>/", views.wishlist_remove, name="wishlist_remove"),

    # Seller products
    path("seller/products/", views.seller_products_view, name="seller_products"),
    path("seller/products/add/", views.seller_product_add, name="seller_product_add"),
    path("admin/verifications/", views.admin_verifications_view, name="admin_verifications"),
    path("admin/verifications/<int:pk>/<str:action>/", views.admin_verification_action, name="admin_verification_action"),

    path("seller/products/<int:pk>/edit/", views.seller_product_edit, name="seller_product_edit"),

    # Seller order actions
    path("seller/orders/", views.seller_orders_view, name="seller_orders"),
    path("orders/<int:pk>/transit/", views.order_mark_in_transit, name="order_mark_in_transit"),
    path("orders/<int:pk>/delivered/", views.order_mark_delivered, name="order_mark_delivered"),

    # Buyer order actions
    path("orders/<int:pk>/confirm/", views.order_buyer_confirm, name="order_buyer_confirm"),

    # Admin order actions
    path("orders/<int:pk>/release-payout/", views.order_release_payout, name="order_release_payout"),

    # Order detail (buyer / seller / admin)
    path("orders/<int:pk>/", views.order_detail, name="order_detail"),

    # Seller payout methods
    path("seller/payouts/save-method/",        views.seller_save_payout_method,        name="seller_save_payout_method"),
    path("seller/payouts/delete-method/<int:pk>/", views.seller_delete_payout_method,  name="seller_delete_payout_method"),
    path("seller/payouts/set-default/<int:pk>/",   views.seller_set_default_payout_method, name="seller_set_default_payout_method"),
    path("seller/payouts/request/",            views.seller_request_payout,            name="seller_request_payout"),

    # Generic section loader (must stay last)
    path("<str:role>/<str:section>/", views.dashboard_section, name="dashboard_section"),
]
