import json

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db.models import Avg, Q, Sum
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_POST
from django.utils import timezone

from shop.forms import ProductForm
from shop.models import Product

from .forms import BuyerAddressForm, SellerVerificationForm
from .models import BuyerAddress, Order, SellerVerification, WishlistItem


def get_or_init_verification(user):
    obj, _ = SellerVerification.objects.get_or_create(
        user=user,
        defaults={
            "full_name": user.get_full_name() or user.username,
            "store_name": user.username,
            "phone": getattr(user, "phone", ""),
        },
    )
    return obj


@login_required
def dashboard_home(request):
    user = request.user
    if user.is_staff:
        return redirect("dashboard_admin")
    if user.role == "seller":
        return redirect("dashboard_seller")
    return redirect("dashboard_buyer")


@login_required
def seller_dashboard(request):
    if request.user.role != "seller":
        return redirect("dashboard")
    return dashboard_page(request, "seller", "overview")


@login_required
def buyer_dashboard(request):
    if request.user.role != "buyer":
        return redirect("dashboard")
    return dashboard_page(request, "buyer", "overview")


@staff_member_required
def admin_dashboard(request):
    return dashboard_page(request, "admin", "overview")


SECTION_TITLES = {
    "admin": {
        "overview": "Dashboard Overview",
        "orders": "Orders",
        "products": "Products",
        "users": "Users",
        "featured": "Featured",
        "payments": "Payments",
    },
    "seller": {
        "overview": "Seller Overview",
        "products": "My Products",
        "orders": "Orders",
        "earnings": "Earnings",
        "payouts": "Payouts",
    },
    "buyer": {
        "overview": "Buyer Overview",
        "orders": "My Orders",
        "wishlist": "Wishlist",
        "addresses": "Addresses",
        "settings": "Settings",
    },
    "seller_extra": {
        "verification": "Seller Verification",
    },
}


def _run_auto_confirm():
    """Auto-confirm any delivered orders older than 3 days. Called on every dashboard page load."""
    cutoff = timezone.now() - timezone.timedelta(days=3)
    Order.objects.filter(
        status=Order.STATUS_DELIVERED,
        delivered_at__lte=cutoff,
    ).update(
        status=Order.STATUS_CONFIRMED,
        confirmed_at=timezone.now(),
        auto_confirmed=True,
    )


def dashboard_context(request, role, section):
    # Run auto-confirm on every dashboard page load (lightweight — indexed query)
    _run_auto_confirm()

    User = get_user_model()
    verification = None
    wishlist_count = 0
    wishlist_slugs = []
    order_counts = {}

    if request.user.is_authenticated and role == "seller":
        try:
            verification = request.user.seller_verification
        except SellerVerification.DoesNotExist:
            verification = None
        order_counts = {
            "pending":    Order.objects.filter(seller=request.user, status=Order.STATUS_PENDING).count(),
            "in_transit": Order.objects.filter(seller=request.user, status=Order.STATUS_IN_TRANSIT).count(),
            "delivered":  Order.objects.filter(seller=request.user, status=Order.STATUS_DELIVERED).count(),
            "confirmed":  Order.objects.filter(seller=request.user, status=Order.STATUS_CONFIRMED).count(),
        }

    if request.user.is_authenticated and role == "buyer":
        wishlist_qs = WishlistItem.objects.filter(user=request.user)
        wishlist_count = wishlist_qs.count()
        wishlist_slugs = list(wishlist_qs.values_list("product_slug", flat=True))
        order_counts = {
            "total":      Order.objects.filter(buyer=request.user).count(),
            "in_progress": Order.objects.filter(buyer=request.user, status__in=[Order.STATUS_PENDING, Order.STATUS_IN_TRANSIT, Order.STATUS_DELIVERED]).count(),
            "confirmed":  Order.objects.filter(buyer=request.user, status=Order.STATUS_CONFIRMED).count(),
            "refunded":   Order.objects.filter(buyer=request.user, status=Order.STATUS_REFUNDED).count(),
        }

    if request.user.is_authenticated and role == "admin":
        order_counts = {
            "total":         Order.objects.count(),
            "payout_ready":  Order.objects.filter(status=Order.STATUS_CONFIRMED, payout_released=False).count(),
            "in_transit":    Order.objects.filter(status=Order.STATUS_IN_TRANSIT).count(),
            "delivered":     Order.objects.filter(status=Order.STATUS_DELIVERED).count(),
        }

    return {
        "user": request.user,
        "role": role,
        "section": section,
        "page_title": (SECTION_TITLES.get(role, {}) or {}).get(section, section.title()),
        "total_users": User.objects.count(),
        "total_sellers": User.objects.filter(role="seller").count(),
        "total_buyers": User.objects.filter(role="buyer").count(),
        "verification": verification,
        "wishlist_count": wishlist_count,
        "wishlist_slugs": wishlist_slugs,
        "order_counts": order_counts,
        "today": timezone.localdate(),
    }


@login_required
def seller_verification_view(request):
    if request.user.role != "seller":
        return redirect("dashboard")
    verification = get_or_init_verification(request.user)
    if request.method == "POST":
        form = SellerVerificationForm(request.POST, request.FILES, instance=verification)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.user = request.user
            if request.FILES.get("document") or obj.document:
                obj.status = "pending"
            obj.save()
            messages.success(request, "Verification submitted — our team will review it within 24 hours.")
            return redirect("dashboard_section", role="seller", section="overview")
        messages.error(request, "Please fix the highlighted fields and try again.")
    else:
        form = SellerVerificationForm(instance=verification)
    context = dashboard_context(request, "seller", "overview")
    context.update({
        "page_title": "Seller Verification",
        "section": "verification",
        "verification": verification,
        "form": form,
        "dashboard_template": "dashboards/seller/verification.html",
    })
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return render(request, "dashboards/seller/verification.html", context)
    return render(request, "dashboards/base.html", context)


@login_required
def dashboard_section(request, role, section):
    if role not in SECTION_TITLES or section not in SECTION_TITLES[role]:
        return redirect("dashboard")
    if role == "admin" and not request.user.is_staff:
        return redirect("dashboard")
    if role != "admin" and request.user.role != role:
        return redirect("dashboard")
    if role == "buyer" and section == "addresses":
        return buyer_addresses(request)
    return dashboard_page(request, role, section)


# --------------------------------------------------------------------------
# Seller product management (catalog / add / edit)
# --------------------------------------------------------------------------

PRODUCTS_PER_PAGE = 8


@login_required
def seller_products_view(request):
    if request.user.role != "seller":
        return redirect("dashboard")

    qs = request.user.products.all().order_by("-created_at")

    q = (request.GET.get("q") or "").strip()
    if q:
        qs = qs.filter(
            Q(name__icontains=q) | Q(store_name__icontains=q) | Q(description__icontains=q)
        )

    category = request.GET.get("category") or "all"
    if category != "all":
        qs = qs.filter(category=category)

    status = request.GET.get("status") or "all"
    if status == "low":
        qs = qs.filter(status="live", stock__lte=Product.LOW_STOCK_THRESHOLD)
    elif status in ("live", "draft"):
        qs = qs.filter(status=status)

    everything = request.user.products.all()
    live = everything.filter(status="live")
    agg = live.aggregate(units=Sum("stock"), avg=Avg("rating"), reviews=Sum("reviews_count"))
    kpis = {
        "live_count": live.count(),
        "draft_count": everything.filter(status="draft").count(),
        "total_count": everything.count(),
        "in_stock_units": agg["units"] or 0,
        "low_stock_count": live.filter(stock__lte=Product.LOW_STOCK_THRESHOLD).count(),
        "avg_rating": agg["avg"] or 0,
        "reviews_total": agg["reviews"] or 0,
    }

    paginator = Paginator(qs, PRODUCTS_PER_PAGE)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = dashboard_context(request, "seller", "products")
    context.update({
        "page_obj": page_obj,
        "products": page_obj.object_list,
        "kpis": kpis,
        "categories": Product.CATEGORY_CHOICES,
        "search_q": q,
        "active_category": category,
        "active_status": status,
    })
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return render(request, "dashboards/seller/products.html", context)
    context["dashboard_template"] = "dashboards/seller/products.html"
    return render(request, "dashboards/base.html", context)


def _product_form_page(request, context, template="dashboards/seller/product_form.html"):
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return render(request, template, context)
    context["dashboard_template"] = template
    return render(request, "dashboards/base.html", context)


@login_required
def seller_product_add(request):
    if request.user.role != "seller":
        return redirect("dashboard")
    initial = {"status": "live", "store_name": request.user.username}
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.seller = request.user
            if not product.store_name:
                product.store_name = request.user.username
            product.save()
            messages.success(
                request,
                "\u201c%s\u201d added \u2014 it is now live on the shop page." % product.name,
            )
            return redirect("seller_products")
        messages.error(request, "Please fix the highlighted fields and try again.")
    else:
        form = ProductForm(initial=initial)
    context = dashboard_context(request, "seller", "products")
    context.update({
        "form": form,
        "product": None,
        "page_title": "Add Product",
    })
    return _product_form_page(request, context)


@login_required
def seller_product_edit(request, pk):
    if request.user.role != "seller":
        return redirect("dashboard")
    product = get_object_or_404(Product, pk=pk, seller=request.user)
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            product = form.save()
            messages.success(request, "\u201c%s\u201d updated." % product.name)
            return redirect("seller_products")
        messages.error(request, "Please fix the highlighted fields and try again.")
    else:
        form = ProductForm(instance=product)
    context = dashboard_context(request, "seller", "products")
    context.update({
        "form": form,
        "product": product,
        "page_title": "Edit Product",
    })
    return _product_form_page(request, context)

@login_required
def buyer_addresses(request):
    if request.user.role != "buyer":
        return redirect("dashboard")
    addresses = BuyerAddress.objects.filter(user=request.user)
    if request.method == "POST":
        form = BuyerAddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            if address.is_default or not addresses.exists():
                BuyerAddress.objects.filter(user=request.user).update(is_default=False)
                address.is_default = True
            address.save()
            messages.success(request, "Your delivery address has been saved.")
            return redirect("dashboard_buyer_addresses")
        messages.error(request, "Please correct the address details below.")
    else:
        form = BuyerAddressForm(initial={"recipient_name": request.user.get_full_name() or request.user.username, "phone": getattr(request.user, "phone", ""), "country": "Nigeria"})
    context = dashboard_context(request, "buyer", "addresses")
    context.update({"addresses": addresses, "form": form, "dashboard_template": "dashboards/buyer/addresses.html"})
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return render(request, "dashboards/buyer/addresses.html", context)
    return render(request, "dashboards/base.html", context)


def dashboard_page(request, role, section):
    context = dashboard_context(request, role, section)
    template = f"dashboards/{role}/{section}.html"

    if role == "seller" and section == "earnings":
        products = list(request.user.products.filter(status="live").order_by("-sold", "-created_at"))
        gross_sales = sum((product.price * product.sold for product in products), start=0)
        marketplace_fee = gross_sales * 0.05
        processing_fee = gross_sales * 0.029 + len([product for product in products if product.sold]) * 0.30
        earning_products = [{"product": product, "gross": product.price * product.sold, "net": product.price * product.sold * 0.921} for product in products]
        context.update({"earning_products": earning_products, "gross_sales": gross_sales, "marketplace_fee": marketplace_fee, "processing_fee": processing_fee, "net_earnings": gross_sales - marketplace_fee - processing_fee, "units_sold": sum(product.sold for product in products), "live_product_count": len(products)})

    if role == "seller" and section == "orders":
        qs = Order.objects.filter(seller=request.user).select_related("buyer", "product")
        q = (request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(order_number__icontains=q) |
                Q(product_name__icontains=q) |
                Q(buyer__username__icontains=q)
            )
        status_filter = request.GET.get("status") or "all"
        if status_filter != "all":
            qs = qs.filter(status=status_filter)
        paginator = Paginator(qs, 15)
        page_obj = paginator.get_page(request.GET.get("page"))
        context.update({"orders": page_obj.object_list, "page_obj": page_obj, "search_q": q, "status_filter": status_filter})

    if role == "buyer" and section == "orders":
        qs = Order.objects.filter(buyer=request.user).select_related("seller", "product")
        orders_list = list(qs)
        context.update({"orders": orders_list})

    if role == "buyer" and section == "wishlist":
        context["wishlist_items"] = (
            WishlistItem.objects.filter(user=request.user)
            if request.user.is_authenticated else []
        )

    if role == "admin" and section == "orders":
        qs = Order.objects.all().select_related("buyer", "seller", "product").order_by("-created_at")
        q = (request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(order_number__icontains=q) |
                Q(product_name__icontains=q) |
                Q(buyer__username__icontains=q) |
                Q(seller__username__icontains=q)
            )
        status_filter = request.GET.get("status") or "all"
        if status_filter != "all":
            qs = qs.filter(status=status_filter)
        paginator = Paginator(qs, 20)
        page_obj = paginator.get_page(request.GET.get("page"))
        context.update({
            "orders": page_obj.object_list,
            "page_obj": page_obj,
            "search_q": q,
            "status_filter": status_filter,
            "payout_ready_count": Order.objects.filter(status=Order.STATUS_CONFIRMED, payout_released=False).count(),
        })

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return render(request, template, context)
    context["dashboard_template"] = template
    return render(request, "dashboards/base.html", context)


@require_POST
@login_required
def wishlist_toggle(request):
    """Add or remove a product from the authenticated buyer's wishlist.

    Expects a JSON body with:
        slug        — unique identifier for the shop card (e.g. "wireless-noise-cancelling-headphones")
        name        — product display name
        store_name  — seller / store label
        category    — category label
        price       — display price string  (e.g. "$89.99")
        old_price   — original price string (optional)
        image_url   — absolute URL image src (optional)
        image_static — /static/img/… path  (optional)
        badge       — badge text            (optional)

    Returns JSON: { "saved": true|false, "count": <wishlist_count> }
    """
    if request.user.role != "buyer":
        return JsonResponse({"error": "Only buyers can use the wishlist."}, status=403)

    try:
        data = json.loads(request.body)
    except (ValueError, KeyError):
        return JsonResponse({"error": "Invalid payload."}, status=400)

    slug = (data.get("slug") or "").strip()
    if not slug:
        return JsonResponse({"error": "slug is required."}, status=400)

    item, created = WishlistItem.objects.get_or_create(
        user=request.user,
        product_slug=slug,
        defaults={
            "name": data.get("name", ""),
            "store_name": data.get("store_name", ""),
            "category": data.get("category", ""),
            "price": data.get("price", ""),
            "old_price": data.get("old_price", ""),
            "image_url": data.get("image_url", ""),
            "image_static": data.get("image_static", ""),
            "badge": data.get("badge", ""),
        },
    )

    if not created:
        # Already saved — remove it (toggle off)
        item.delete()
        saved = False
    else:
        saved = True

    count = WishlistItem.objects.filter(user=request.user).count()
    return JsonResponse({"saved": saved, "count": count})


@require_POST
@login_required
def wishlist_remove(request, slug):
    """Remove a specific item from the wishlist (used from the dashboard wishlist page)."""
    if request.user.role != "buyer":
        return JsonResponse({"error": "Forbidden."}, status=403)

    WishlistItem.objects.filter(user=request.user, product_slug=slug).delete()

    # Support both AJAX and plain form POST
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        count = WishlistItem.objects.filter(user=request.user).count()
        return JsonResponse({"removed": True, "count": count})

    return redirect("dashboard_section", role="buyer", section="wishlist")


# ═══════════════════════════════════════════════════════════════
#  ORDER ACTION VIEWS
# ═══════════════════════════════════════════════════════════════

@require_POST
@login_required
def order_mark_in_transit(request, pk):
    """Seller: mark order as in-transit (shipped)."""
    order = get_object_or_404(Order, pk=pk, seller=request.user)
    if order.status == Order.STATUS_PENDING:
        tracking = request.POST.get("tracking_number", "").strip()
        order.status = Order.STATUS_IN_TRANSIT
        order.shipped_at = timezone.now()
        if tracking:
            order.tracking_number = tracking
        order.save()
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"ok": True, "status": order.status, "label": order.status_label, "css": order.status_css})
        messages.success(request, f"Order #{order.order_number} marked as In Transit.")
    return redirect("seller_orders")


@require_POST
@login_required
def order_mark_delivered(request, pk):
    """Seller: mark order as delivered."""
    order = get_object_or_404(Order, pk=pk, seller=request.user)
    if order.status == Order.STATUS_IN_TRANSIT:
        order.status = Order.STATUS_DELIVERED
        order.delivered_at = timezone.now()
        order.save()
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"ok": True, "status": order.status, "label": order.status_label, "css": order.status_css})
        messages.success(request, f"Order #{order.order_number} marked as Delivered. Buyer has 3 days to confirm.")
    return redirect("seller_orders")


@require_POST
@login_required
def order_buyer_confirm(request, pk):
    """Buyer: manually confirm receipt of a delivered order."""
    order = get_object_or_404(Order, pk=pk, buyer=request.user)
    if order.status == Order.STATUS_DELIVERED:
        order.status = Order.STATUS_CONFIRMED
        order.confirmed_at = timezone.now()
        order.auto_confirmed = False
        order.save()
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"ok": True, "order_number": order.order_number})
        messages.success(request, f"Thank you for confirming #{order.order_number}! Payment will be released to the seller.")
    return redirect("dashboard_section", role="buyer", section="orders")


@require_POST
@staff_member_required
def order_release_payout(request, pk):
    """Admin: release escrow payout for a confirmed order."""
    order = get_object_or_404(Order, pk=pk)
    if order.status == Order.STATUS_CONFIRMED and not order.payout_released:
        order.payout_released = True
        order.payout_released_at = timezone.now()
        order.save()
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"ok": True, "order_number": order.order_number})
        messages.success(request, f"Payout released for order #{order.order_number}.")
    return redirect("dashboard_section", role="admin", section="orders")


@login_required
def order_detail(request, pk):
    """Detail view — accessible by buyer, seller, or admin."""
    user = request.user
    if user.is_staff:
        order = get_object_or_404(Order, pk=pk)
    elif user.role == "seller":
        order = get_object_or_404(Order, pk=pk, seller=user)
    else:
        order = get_object_or_404(Order, pk=pk, buyer=user)

    role = "admin" if user.is_staff else user.role
    context = dashboard_context(request, role, "orders")
    context.update({"order": order, "page_title": f"Order #{order.order_number}"})
    template = f"dashboards/{role}/order_detail.html"
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return render(request, template, context)
    context["dashboard_template"] = template
    return render(request, "dashboards/base.html", context)
