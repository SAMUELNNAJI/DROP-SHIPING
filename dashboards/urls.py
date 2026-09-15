from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard_home, name="dashboard"),
    path("seller/", views.seller_dashboard, name="dashboard_seller"),
    path("buyer/", views.buyer_dashboard, name="dashboard_buyer"),
    path("admin/", views.admin_dashboard, name="dashboard_admin"),
    path("seller/verification/", views.seller_verification_view, name="dashboard_seller_verification"),
    path("<str:role>/<str:section>/", views.dashboard_section, name="dashboard_section"),
]
