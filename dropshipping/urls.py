"""
URL configuration for dropshipping project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.views.generic import RedirectView

from django.conf import settings
from django.views.static import serve

from shop import views
from shop import views as shop_views
from dashboards import views as dashboard_views
from accounts import views as accounts_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.page, {'slug': 'index'}, name='home'),
    path('shop/', views.page, {'slug': 'shop'}, name='shop'),
    path('products/<int:pk>/', views.product_detail, name='product_detail'),
    path('blog/<slug:slug>/', shop_views.blog_detail, name='blog_detail'),
    path('about/', views.page, {'slug': 'about'}, name='about'),
    path('blog/', shop_views.blog_view, name='blog'),
    path('contact/', views.page, {'slug': 'contact'}, name='contact'),
    path('help/', views.page, {'slug': 'help'}, name='help'),
    path('payouts/', views.page, {'slug': 'payouts'}, name='payouts'),
    path('refund-policy/', views.page, {'slug': 'refund-policy'}, name='refund-policy'),
    path('privacy/', views.page, {'slug': 'privacy'}, name='privacy'),
    path('terms/', views.page, {'slug': 'terms'}, name='terms'),
    # Authentication
    path('accounts/', include('accounts.urls')),
    # Dashboards
    path('dashboards/', include('dashboards.urls')),
    # Canonical signin URL -> Django-powered signin view
    path('signin/', accounts_views.signin_view, name='signin'),
    path('signup/', accounts_views.signup_view, name='signup'),
    path('checkout/', dashboard_views.checkout_view, name='checkout'),
    path('checkout-payment/', dashboard_views.checkout_payment, name='checkout-payment'),
    path('checkout-success/', dashboard_views.checkout_success_view, name='checkout-success'),
    # Canonical nested aliases -> redirect to the flat URLs used across the site
    path('checkout/payment/', RedirectView.as_view(url='/checkout-payment/', permanent=False)),
    path('checkout/success/', RedirectView.as_view(url='/checkout-success/', permanent=False)),
]

if settings.DEBUG or getattr(settings, 'SERVE_MEDIA', False):
    # Uploaded files (seller verification documents, etc.) are not handled by
    # WhiteNoise, so Django serves them here for both local development and the
    # Render deployment. Turn SERVE_MEDIA off once media moves to object
    # storage (S3/Cloudinary) or a dedicated static host.
    urlpatterns += [
        re_path(
            r'^{}/(?P<path>.*)$'.format(settings.MEDIA_URL.strip('/')),
            serve,
            {'document_root': settings.MEDIA_ROOT},
        ),
    ]

if settings.DEBUG:
    # Preview the custom error templates without turning DEBUG off.
    # Visit: /__preview__/400/  /403/  /404/  /500/
    urlpatterns += [
        path('__preview__/400/', shop_views.preview_400, name='preview_400'),
        path('__preview__/403/', shop_views.preview_403, name='preview_403'),
        path('__preview__/404/', shop_views.preview_404, name='preview_404'),
        path('__preview__/500/', shop_views.preview_500, name='preview_500'),
    ]
