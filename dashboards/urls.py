from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard_home, name="dashboard"),
    path("seller/", views.seller_dashboard, name="dashboard_seller"),
    path("buyer/", views.buyer_dashboard, name="dashboard_buyer"),
    path("admin/", views.admin_dashboard, name="dashboard_admin"),
    path("seller/verification/", views.seller_verification_view, name="dashboard_seller_verification"),
    path("buyer/addresses/", views.buyer_addresses, name="dashboard_buyer_addresses"),
    path("wishlist/toggle/", views.wishlist_toggle, name="wishlist_toggle"),
    path("wishlist/remove/<slug:slug>/", views.wishlist_remove, name="wishlist_remove"),
    path("seller/products/", views.seller_products_view, name="seller_products"),
    path("seller/products/add/", views.seller_product_add, name="seller_product_add"),
    path("seller/products/<int:pk>/edit/", views.seller_product_edit, name="seller_product_edit"),

    path("<str:role>/<str:section>/", views.dashboard_section, name="dashboard_section"),
]
