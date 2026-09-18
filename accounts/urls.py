from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path("signup/", views.signup_view, name="signup"),
    path("signin/", views.signin_view, name="accounts_signin"),
    path("signout/", views.signout_view, name="signout"),
    path("password-reset/", auth_views.PasswordResetView.as_view(template_name="auth/password_reset.html", email_template_name="auth/password_reset_email.txt", subject_template_name="auth/password_reset_subject.txt"), name="password_reset"),
    path("password-reset/done/", auth_views.PasswordResetDoneView.as_view(template_name="auth/password_reset_done.html"), name="password_reset_done"),
    path("reset/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(template_name="auth/password_reset_confirm.html"), name="password_reset_confirm"),
    path("reset/done/", auth_views.PasswordResetCompleteView.as_view(template_name="auth/password_reset_complete.html"), name="password_reset_complete"),
    path("social/<str:provider>/", views.social_start, name="social_start"),
    path("social/<str:provider>/callback/", views.social_callback, name="social_callback"),
]
