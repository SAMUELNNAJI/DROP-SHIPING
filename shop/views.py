import re

from django.http import Http404, HttpResponse
from django.template.loader import render_to_string

# Every page of the store, keyed by the template name.
PAGES = {
    'index': 'Home',
    'shop': 'Shop',
    'about': 'About',
    'blog': 'Blog',
    'contact': 'Contact',
    'help': 'Help Center',
    'payouts': 'Payouts',
    'refund-policy': 'Refund Policy',
    'signin': 'Sign In',
    'checkout': 'Checkout',
    'checkout-payment': 'Checkout — Payment',
    'checkout-success': 'Order Confirmed',
    'privacy': 'Privacy Policy',
    'terms': 'Terms of Service',
}


def page(request, slug):
    """Generic view that renders any of the static store pages."""
    if slug not in PAGES:
        raise Http404(f'Unknown page: {slug}')

    context = {'page_title': PAGES[slug], 'slug': slug}
    html = render_to_string(f'{slug}.html', context, request=request)

    # Store pages currently carry their own navbar markup.  Replace their
    # guest-only actions after rendering so the header remains consistent with
    # the account pages until those templates are consolidated.
    if request.user.is_authenticated:
        if request.user.is_superuser:
            dashboard_url = '/dashboards/admin/'
        elif request.user.role == 'seller':
            dashboard_url = '/dashboards/seller/'
        else:
            dashboard_url = '/dashboards/buyer/'

        dashboard = (
            f'<a href="{dashboard_url}" class="btn-sell"><span>Dashboard</span>'
            '<svg class="btn-sell-arrow" width="18" height="18" viewBox="0 0 24 24" '
            'fill="none" stroke="#fff" stroke-width="1.8" stroke-linecap="round" '
            'stroke-linejoin="round"><rect x="3" y="3" width="7" height="7" rx="1.5"/>'
            '<rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" '
            'width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" '
            'rx="1.5"/></svg></a>'
        )
        mobile_dashboard = dashboard.replace('class="btn-sell"', 'class="mmenu-cta"')
        html = re.sub(r'<a href="[^"]*" class="nav-signin[^>]*>.*?</a>', '', html, flags=re.DOTALL)
        html = re.sub(r'<a href="[^"]*" class="btn-sell"[^>]*>.*?</a>', dashboard, html, flags=re.DOTALL)
        html = re.sub(r'<a href="[^"]*" class="mmenu-signin"[^>]*>.*?</a>', '', html, flags=re.DOTALL)
        html = re.sub(r'<a href="[^"]*" class="mmenu-cta"[^>]*>.*?</a>', mobile_dashboard, html, flags=re.DOTALL)

    return HttpResponse(html)
