from django.urls import path
from . import views

urlpatterns = [
    path("signup/", views.signup_view, name="signup"),
    path("signin/", views.signin_view, name="accounts_signin"),
    path("signout/", views.signout_view, name="signout"),
    path("social/<str:provider>/", views.social_start, name="social_start"),
    path("social/<str:provider>/callback/", views.social_callback, name="social_callback"),
]
