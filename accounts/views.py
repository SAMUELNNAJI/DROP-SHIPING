from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect
from urllib.parse import urlencode
from django.utils.http import url_has_allowed_host_and_scheme
from .forms import SignUpForm, SignInForm


def signup_view(request):
    """Register a new user as buyer or seller."""
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Welcome to DropHub, {user.username}!")
            # Redirect to the appropriate dashboard based on role
            target = 'dashboard_seller' if user.role == 'seller' else 'dashboard_buyer'
            return redirect(target)
    else:
        form = SignUpForm()
    return render(request, 'auth/signup.html', {
        'form': form,
        'page_title': 'Create Account',
        'auth_mode': 'signup',
    })


def signin_view(request):
    """Sign in an existing user."""
    if request.user.is_authenticated:
        return redirect('dashboard')

    next_url = request.POST.get('next') or request.GET.get('next') or ''
    if request.method == 'POST':
        form = SignInForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            if next_url and url_has_allowed_host_and_scheme(
                next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return redirect(next_url)
            if user.is_staff:
                return redirect('dashboard_admin')
            elif user.role == 'seller':
                return redirect('dashboard_seller')
            else:
                return redirect('dashboard_buyer')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = SignInForm()
    return render(request, 'auth/signin.html', {
        'form': form,
        'page_title': 'Sign In',
        'next': next_url,
        'auth_mode': 'signin',
    })


@login_required
def signout_view(request):
    """Log out the current user."""
    from django.contrib.auth import logout
    logout(request)
    messages.info(request, 'You have been signed out.')
    return redirect('home')


def social_start(request, provider):
    """Start an OAuth flow when provider credentials are configured."""
    provider = provider.lower()
    if provider not in {'google', 'apple'}:
        return redirect('accounts_signin')
    client_id = getattr(settings, f'{provider.upper()}_CLIENT_ID', '')
    if not client_id:
        messages.info(request, f'{provider.title()} sign-in is not configured yet. Add the provider credentials to enable it.')
        return redirect('accounts_signin')
    request.session['social_provider'] = provider
    if provider == 'google':
        params = {
            'client_id': client_id,
            'redirect_uri': request.build_absolute_uri(f'/accounts/social/{provider}/callback/'),
            'response_type': 'code',
            'scope': 'openid email profile',
            'access_type': 'offline',
            'prompt': 'select_account',
        }
        return redirect('https://accounts.google.com/o/oauth2/v2/auth?' + urlencode(params))
    params = {
        'client_id': client_id,
        'redirect_uri': request.build_absolute_uri(f'/accounts/social/{provider}/callback/'),
        'response_type': 'code id_token',
        'response_mode': 'form_post',
        'scope': 'name email',
    }
    return redirect('https://appleid.apple.com/auth/authorize?' + urlencode(params))


@csrf_exempt
def social_callback(request, provider):
    """Return safely until provider token exchange and account linking are configured."""
    if request.GET.get('error') or request.POST.get('error'):
        messages.error(request, 'Social sign-in was cancelled. You can use your DropHub password instead.')
    else:
        messages.info(request, f'{provider.title()} authorization received. Complete provider account linking in the deployment settings.')
    return redirect('accounts_signin')
