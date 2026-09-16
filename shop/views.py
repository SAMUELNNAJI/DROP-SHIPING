import re

from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.db.models import Q
from django.template.loader import render_to_string

from .models import Product


SHOP_SORTS = (
    ("default", "Featured"),
    ("newest", "Newest"),
    ("price-asc", "Price: Low to High"),
    ("price-desc", "Price: High to Low"),
    ("rating", "Top Rated"),
)

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
    """Generic view for static store pages.  The shop page is handled separately."""
    if slug == "shop":
        return shop_page(request)

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

def filter_shop_products(request):
    """Apply GET filters (q, category, price range, rating, sort) to live products."""
    qs = Product.objects.filter(status="live").select_related("seller")
    data = request.GET

    q = (data.get("q") or "").strip()
    if q:
        qs = qs.filter(
            Q(name__icontains=q)
            | Q(store_name__icontains=q)
            | Q(description__icontains=q)
        )

    cat = (data.get("category") or "all").strip().lower()
    valid_slugs = [s for s, _ in Product.CATEGORY_CHOICES]
    if cat and cat != "all" and cat in valid_slugs:
        qs = qs.filter(category=cat)

    try:
        min_p = float(data.get("min_price") or 0)
        max_p = float(data.get("max_price") or 10_000_000)
        if max_p < 1_000_000:
            qs = qs.filter(price__gte=min_p, price__lte=max_p)
    except (TypeError, ValueError):
        pass

    try:
        min_rating = float(data.get("rating") or 0)
        if min_rating:
            qs = qs.filter(rating__gte=min_rating)
    except (TypeError, ValueError):
        pass

    in_stock = data.get("in_stock")
    if in_stock:
        qs = qs.filter(stock__gt=0)

    sort = (data.get("sort") or "default").strip()
    if sort == "price-asc":
        qs = qs.order_by("price")
    elif sort == "price-desc":
        qs = qs.order_by("-price")
    elif sort == "rating":
        qs = qs.order_by("-rating", "-sold")
    elif sort == "newest":
        qs = qs.order_by("-created_at")
    else:
        qs = qs.order_by("-sold", "-rating", "-created_at")

    return qs, {
        "q": q,
        "category": cat,
        "min_price": data.get("min_price", "0"),
        "max_price": data.get("max_price", "200"),
        "rating": data.get("rating", ""),
        "in_stock": in_stock,
        "sort": sort,
    }


def shop_page(request):
    """Dynamic shop: DB products (live) + shared categories + working search/filter/sort."""
    qs, active = filter_shop_products(request)
    products = list(qs[:60])
    total_live = Product.objects.filter(status="live").count()

    # Wishlist hearts: only buyers get working hearts; guests and non-buyers
    # (sellers/admins) get the sign-in popup instead.  Server-rendered state
    # keeps the two flows unambiguous.
    if request.user.is_authenticated and getattr(request.user, "role", "") == "buyer":
        from dashboards.models import WishlistItem

        user_state = "buyer"
        wishlist_slugs = list(
            WishlistItem.objects.filter(user=request.user).values_list("product_slug", flat=True)
        )
    elif request.user.is_authenticated:
        user_state = "auth"
        wishlist_slugs = []
    else:
        user_state = "guest"
        wishlist_slugs = []

    from django.middleware.csrf import get_token

    get_token(request)  # ensure the csrftoken cookie exists for heart POSTs

    context = {
        'page_title': 'Shop',
        'slug': 'shop',
        'products': products,
        'product_count': len(products),
        'total_live': total_live,
        'categories': Product.CATEGORY_CHOICES,
        'sorts': SHOP_SORTS,
        'active': active,
        'user_state': user_state,
        'wishlist_slugs': wishlist_slugs,
    }
    html = render_to_string('shop.html', context, request=request)

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


def product_detail(request, pk):
    """Public product page. Draft products remain visible only to their seller."""
    product = get_object_or_404(Product.objects.select_related("seller"), pk=pk)
    if product.status != "live" and (not request.user.is_authenticated or request.user != product.seller):
        raise Http404("Product not found")
    return render(request, "product_detail.html", {"product": product, "page_title": product.name})

