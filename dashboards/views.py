import json
from decimal import Decimal

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

from shop.forms import BlogPostForm, ProductForm
from shop.models import BlogPost, Product

from . import payment_views
from .forms import BuyerAddressForm, BoostPlanForm, SellerPayoutMethodForm, SellerVerificationForm
from .models import BuyerAddress, BoostOrder, BoostPlan, CartItem, CurrencyRate, Order, OrderTrackingEvent, PaymentIntent, RefundComplaint, RefundMessage, SellerPayout, SellerPayoutMethod, SellerPayoutRecord, SellerVerification, WishlistItem


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
        "verifications": "Seller Verifications",
        "posts": "Blog Posts",
        "pi-payments": "Pi Payment Verification",
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


@staff_member_required
def admin_posts(request):
    posts = BlogPost.objects.all().order_by("-created_at")
    context = dashboard_context(request, "admin", "posts")
    context.update({
        "posts": posts,
        "post_form": BlogPostForm(),
        "dashboard_template": "dashboards/admin/posts.html",
        "total_posts": posts.count(),
        "published_count": posts.filter(is_published=True).count(),
        "featured_count": posts.filter(is_featured=True).count(),
    })
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return render(request, "dashboards/admin/posts.html", context)
    return render(request, "dashboards/base.html", context)


@staff_member_required
@require_POST
def admin_post_create(request):
    form = BlogPostForm(request.POST, request.FILES)
    if form.is_valid():
        form.save(); messages.success(request, "Blog post created.")
    else: messages.error(request, "Please correct the post form.")
    return redirect("admin_posts")


@staff_member_required
def admin_post_edit(request, pk):
    post = get_object_or_404(BlogPost, pk=pk)
    if request.method == "POST":
        form = BlogPostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()
            messages.success(request, "Blog post updated.")
            return redirect("admin_posts")
        messages.error(request, "Please fix the highlighted fields.")
    else:
        form = BlogPostForm(instance=post)
    all_posts = BlogPost.objects.all().order_by("-created_at")
    context = dashboard_context(request, "admin", "posts")
    context.update({
        "posts": all_posts,
        "post_form": form,
        "editing_post": post,
        "dashboard_template": "dashboards/admin/posts.html",
        "total_posts": all_posts.count(),
        "published_count": all_posts.filter(is_published=True).count(),
        "featured_count": all_posts.filter(is_featured=True).count(),
    })
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return render(request, "dashboards/admin/posts.html", context)
    return render(request, "dashboards/base.html", context)


@staff_member_required
@require_POST
def admin_post_delete(request, pk):
    get_object_or_404(BlogPost, pk=pk).delete(); messages.success(request, "Blog post deleted.")
    return redirect("admin_posts")


def _run_auto_confirm():
    """Auto-confirm delivered orders older than 3 days.

    Throttled to run at most once every 30 minutes via the cache to avoid
    a DB write on every single dashboard page load.
    """
    from django.core.cache import cache
    LOCK_KEY = "auto_confirm_last_run"
    if cache.get(LOCK_KEY):
        return  # Already ran recently — skip
    cache.set(LOCK_KEY, True, timeout=1800)  # 30 minutes
    cutoff = timezone.now() - timezone.timedelta(days=3)
    Order.objects.filter(
        status=Order.STATUS_DELIVERED,
        delivered_at__lte=cutoff,
    ).update(
        status=Order.STATUS_CONFIRMED,
        confirmed_at=timezone.now(),
        auto_confirmed=True,
    )


# ═══════════════════════════════════════════════════════════════
#  ADMIN: Pi payment verification (manual wallet transfers)
# ═══════════════════════════════════════════════════════════════

@staff_member_required
def admin_pi_payments(request):
    """Admin: list all Pi payments awaiting manual wallet verification."""
    context = dashboard_context(request, "admin", "pi-payments")
    qs = PaymentIntent.objects.filter(
        method="pi", status=PaymentIntent.STATUS_PI_PENDING
    ).select_related("user").order_by("-created_at")
    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    recent_processed = PaymentIntent.objects.filter(
        method="pi",
        status__in=[PaymentIntent.STATUS_PAID, PaymentIntent.STATUS_FAILED],
    ).select_related("user").order_by("-updated_at")[:20]

    from django.conf import settings as _settings
    pi_wallet = getattr(_settings, "PI_WALLET_ADDRESS", "") or getattr(_settings, "PI_APP_WALLET", "")

    context.update({
        "pi_payments":       page_obj.object_list,
        "page_obj":          page_obj,
        "recent_processed":  recent_processed,
        "pi_wallet_address": pi_wallet,
        "dashboard_template": "dashboards/admin/pi_payments.html",
    })
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return render(request, "dashboards/admin/pi_payments.html", context)
    return render(request, "dashboards/base.html", context)


@staff_member_required
@require_POST
def admin_pi_confirm(request, pk):
    """Admin: verify Pi transfer in wallet then create orders via finalize_intent."""
    intent = get_object_or_404(
        PaymentIntent, pk=pk, method="pi", status=PaymentIntent.STATUS_PI_PENDING
    )
    try:
        # finalize_intent wraps its own DB transaction and creates orders idempotently
        payment_views.finalize_intent(intent)
        intent.refresh_from_db()
        intent.note = (intent.note or "") + "  ✓ Admin confirmed Pi transfer."
        intent.provider_payload = {
            **(intent.provider_payload or {}),
            "admin_confirmed_at": timezone.now().isoformat(),
            "admin_action": "confirm",
        }
        intent.save(update_fields=["note", "provider_payload", "updated_at"])
        messages.success(
            request,
            f"#{intent.reference} confirmed — {len(intent.order_pks)} order(s) created.",
        )
    except payment_views.CheckoutError as exc:
        messages.error(request, f"#{intent.reference}: {exc}")
    except Exception as exc:
        messages.error(request, f"#{intent.reference}: Unexpected error — {exc}")
    return redirect("admin_pi_payments")

def admin_pi_reject(request, pk):
    """Admin: reject a Pi transfer claim and restore the cart for the buyer."""
    intent = get_object_or_404(
        PaymentIntent, pk=pk, method="pi", status=PaymentIntent.STATUS_PI_PENDING
    )
    cart_snapshot = (intent.provider_payload or {}).get("cart_snapshot", [])
    if cart_snapshot:
        CartItem.objects.filter(user=intent.user).delete()
        for item in cart_snapshot:
            try:
                CartItem.objects.create(
                    user=intent.user,
                    product_id=item["product_pk"],
                    quantity=item["quantity"],
                )
            except (KeyError, Exception):
                continue

    intent.status = PaymentIntent.STATUS_FAILED
    intent.note = (intent.note or "") + "  ✗ Admin rejected — no Pi received."
    intent.save(update_fields=["status", "note", "updated_at"])
    messages.success(request, f"#{intent.reference} rejected — cart restored for buyer.")
    return redirect("admin_pi_payments")


@staff_member_required
@require_POST
def admin_pi_reclaim(request, pk):
    """Admin: reset a failed/cancelled Pi intent back to pending so buyer can retry."""
    intent = get_object_or_404(
        PaymentIntent, pk=pk, method="pi",
        status__in=[PaymentIntent.STATUS_FAILED, PaymentIntent.STATUS_CANCELLED]
    )
    intent.status = PaymentIntent.STATUS_PENDING
    intent.order_pks = []
    intent.note = (intent.note or "") + "  ↻ Reset to pending by admin."
    intent.save(update_fields=["status", "order_pks", "note", "updated_at"])
    messages.success(request, f"#{intent.reference} reset to pending — buyer can claim again.")
    return redirect("admin_pi_payments")


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
        pending_pi = PaymentIntent.objects.filter(
            status=PaymentIntent.STATUS_PI_PENDING
        ).count()
    else:
        pending_pi = 0

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
        "pending_verifications": (
            SellerVerification.objects.filter(status="pending").count() if role == "admin" else 0
        ),
        "pending_pi_payments": pending_pi,
        "open_refund_count": (
            RefundComplaint.objects.filter(status__in=("open", "in_review")).count() if role == "admin" else 0
        ),
        "pending_payout_count": (
            Order.objects.filter(status=Order.STATUS_CONFIRMED, payout_released=False).count() if role == "admin" else 0
        ),
    }


@login_required
def seller_verification_view(request):
    if request.user.role != "seller":
        return redirect("dashboard")
    verification = get_or_init_verification(request.user)

    if request.method == "POST":
        if verification.status == "verified":
            messages.info(request, "Your account is already verified — no further action is needed.")
            return redirect("dashboard_seller_verification")
        form = SellerVerificationForm(request.POST, request.FILES, instance=verification)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.user = request.user
            # Auto-verify immediately when a document is uploaded.
            # Admin can still reject from the verifications dashboard.
            if obj.document or verification.document:
                obj.status = "verified"
                obj.reviewer_note = ""
                obj.save()
                messages.success(
                    request,
                    "Your account is now verified — you can publish products and request payouts."
                )
            else:
                obj.status = "pending"
                obj.reviewer_note = ""
                obj.save()
                messages.success(
                    request,
                    "Details saved. Upload your ID document to complete verification instantly."
                )
            return redirect("dashboard_seller_verification")
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
    if role == "buyer" and section == "settings":
        return buyer_settings(request)
    if role == "admin" and section == "users":
        return admin_users_view(request)
    if role == "admin" and section == "products":
        return admin_products_view(request)
    if role == "admin" and section == "featured":
        return admin_featured_view(request)
    if role == "admin" and section == "posts":
        return admin_posts(request)
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

    # ── Active boost per product ──────────────────────────────────────
    # Map product_id -> running BoostOrder (paid & not expired) so the table
    # can show exactly which plan is live on each boosted product.
    _now = timezone.now()
    _running = (
        BoostOrder.objects.filter(
            seller=request.user,
            status=BoostOrder.STATUS_PAID,
            expires_at__gt=_now,
        )
        .select_related("plan")
        .order_by("-paid_at", "-created_at")
    )
    _boost_by_product = {}
    for _bo in _running:
        _boost_by_product.setdefault(_bo.product_id, _bo)
    for _p in page_obj.object_list:
        _p.active_boost = _boost_by_product.get(_p.pk)

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
    verification = get_or_init_verification(request.user)
    if verification.status != "verified":
        messages.error(request, "Complete seller verification by uploading your ID document before publishing products.")
        return redirect("dashboard_seller_verification")
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
    try:
        seller_verification = request.user.seller_verification
    except Exception:
        seller_verification = None
    context = dashboard_context(request, "seller", "products")
    context.update({
        "form": form,
        "product": None,
        "page_title": "Add Product",
        "is_verified_seller": seller_verification is not None and seller_verification.status == "verified",
    })
    return _product_form_page(request, context)


@login_required
def seller_product_edit(request, pk):
    if request.user.role != "seller":
        return redirect("dashboard")
    if get_or_init_verification(request.user).status != "verified":
        messages.error(request, "Only verified sellers can publish or edit products. Upload your ID document to get verified instantly.")
        return redirect("dashboard_seller_verification")
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


# --------------------------------------------------------------------------
# Admin: seller verification review
# --------------------------------------------------------------------------

def _admin_verifications_context(request):
    # With auto-verification, sellers go straight to "verified".
    # The review queue shows recently verified sellers so admin can reject if needed.
    # "pending" is kept for legacy/edge cases (submitted without a document).
    pending = SellerVerification.objects.filter(status="pending").select_related("user")
    auto_verified = SellerVerification.objects.filter(status="verified").select_related("user").order_by("-submitted_at")[:50]
    reviewed = SellerVerification.objects.filter(status__in=["rejected", "unverified"]).select_related("user").order_by("-submitted_at")[:50]
    context = dashboard_context(request, "admin", "verifications")
    context.update({
        "page_title": "Seller Verifications",
        "pending_list": pending,
        "pending_count": pending.count(),
        "auto_verified_list": auto_verified,
        "auto_verified_count": auto_verified.count(),
        "reviewed_list": reviewed,
        "verified_count": SellerVerification.objects.filter(status="verified").count(),
        "rejected_count": SellerVerification.objects.filter(status="rejected").count(),
        "dashboard_template": "dashboards/admin/verifications.html",
    })
    return context


@login_required
def admin_verifications_view(request):
    if not request.user.is_staff:
        return redirect("dashboard")
    context = _admin_verifications_context(request)
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return render(request, "dashboards/admin/verifications.html", context)
    return render(request, "dashboards/base.html", context)


@require_POST
@login_required
def admin_verification_action(request, pk, action):
    if not request.user.is_staff:
        return redirect("dashboard")
    verification = get_object_or_404(SellerVerification, pk=pk)
    note = (request.POST.get("reviewer_note") or "").strip()

    if action == "approve":
        verification.status = "verified"
        verification.reviewer_note = note
        messages.success(
            request,
            "Approved %s — %s can now request instant payouts." % (
                verification.store_name or verification.user.username,
                verification.user.username,
            ),
        )
    elif action == "reject":
        verification.status = "rejected"
        verification.reviewer_note = note or "Please upload a clearer document and resubmit."
        messages.warning(
            request,
            "Rejected %s — the seller was asked to resubmit." % (
                verification.store_name or verification.user.username,
            ),
        )
    elif action == "reset":
        verification.status = "unverified"
        verification.reviewer_note = ""
        messages.info(request, "Reset %s to unverified." % (
            verification.store_name or verification.user.username,
        ))
    else:
        messages.error(request, "Unknown action.")
        return redirect("admin_verifications")

    verification.save()
    return redirect("admin_verifications")

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
            messages.success(request, "Address saved successfully.")
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"ok": True})
            return redirect("dashboard_buyer_addresses")
        messages.error(request, "Please correct the highlighted fields.")
    else:
        form = BuyerAddressForm(initial={
            "recipient_name": request.user.get_full_name() or request.user.username,
            "phone": getattr(request.user, "phone", ""),
            "country": "Nigeria",
        })
    context = dashboard_context(request, "buyer", "addresses")
    context.update({"addresses": addresses, "form": form, "dashboard_template": "dashboards/buyer/addresses.html"})
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return render(request, "dashboards/buyer/addresses.html", context)
    return render(request, "dashboards/base.html", context)


@require_POST
@login_required
def buyer_address_delete(request, pk):
    if request.user.role != "buyer":
        return redirect("dashboard")
    address = get_object_or_404(BuyerAddress, pk=pk, user=request.user)
    was_default = address.is_default
    address.delete()
    # Promote next address to default if deleted one was default
    if was_default:
        nxt = BuyerAddress.objects.filter(user=request.user).first()
        if nxt:
            nxt.is_default = True
            nxt.save(update_fields=["is_default"])
    messages.success(request, "Address removed.")
    return redirect("dashboard_buyer_addresses")


@require_POST
@login_required
def buyer_address_set_default(request, pk):
    if request.user.role != "buyer":
        return redirect("dashboard")
    address = get_object_or_404(BuyerAddress, pk=pk, user=request.user)
    BuyerAddress.objects.filter(user=request.user).update(is_default=False)
    address.is_default = True
    address.save(update_fields=["is_default"])
    messages.success(request, f'"{address.label}" is now your default address.')
    return redirect("dashboard_buyer_addresses")


@login_required
def buyer_settings(request):
    if request.user.role != "buyer":
        return redirect("dashboard")
    user = request.user
    profile_errors = {}

    if request.method == "POST":
        action = request.POST.get("action", "profile")

        if action == "profile":
            first_name  = request.POST.get("first_name", "").strip()
            last_name   = request.POST.get("last_name", "").strip()
            email       = request.POST.get("email", "").strip().lower()
            phone       = request.POST.get("phone", "").strip()

            # Validate email uniqueness
            from django.contrib.auth import get_user_model
            User = get_user_model()
            if email and email != user.email:
                if User.objects.exclude(pk=user.pk).filter(email__iexact=email).exists():
                    profile_errors["email"] = "This email is already used by another account."

            if not profile_errors:
                user.first_name = first_name
                user.last_name  = last_name
                if email:
                    user.email = email
                user.phone = phone
                user.save(update_fields=["first_name", "last_name", "email", "phone"])
                messages.success(request, "Profile updated successfully.")
                return redirect("buyer_settings")
            else:
                messages.error(request, "Please fix the highlighted fields.")

        elif action == "password":
            from django.contrib.auth import update_session_auth_hash
            current  = request.POST.get("current_password", "")
            new_pw   = request.POST.get("new_password", "")
            confirm  = request.POST.get("confirm_password", "")

            if not user.check_password(current):
                messages.error(request, "Current password is incorrect.")
            elif len(new_pw) < 8:
                messages.error(request, "New password must be at least 8 characters.")
            elif new_pw != confirm:
                messages.error(request, "New passwords do not match.")
            else:
                user.set_password(new_pw)
                user.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Password changed. You're still logged in.")
                return redirect("buyer_settings")

    context = dashboard_context(request, "buyer", "settings")
    context.update({
        "profile_errors": profile_errors,
        "dashboard_template": "dashboards/buyer/settings.html",
    })
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return render(request, "dashboards/buyer/settings.html", context)
    return render(request, "dashboards/base.html", context)


def dashboard_page(request, role, section):
    context = dashboard_context(request, role, section)
    template = f"dashboards/{role}/{section}.html"

    # ── Seller: overview ──────────────────────────────────────
    if role == "seller" and section == "overview":
        seller = request.user
        all_orders  = Order.objects.filter(seller=seller)
        now         = timezone.now()
        week_ago    = now - timezone.timedelta(days=7)
        prev_week   = week_ago - timezone.timedelta(days=7)

        # Revenue this week vs prev week (confirmed + payout-released orders)
        rev_this  = all_orders.filter(status__in=[Order.STATUS_CONFIRMED], confirmed_at__gte=week_ago).aggregate(s=Sum("total_price"))["s"] or 0
        rev_prev  = all_orders.filter(status__in=[Order.STATUS_CONFIRMED], confirmed_at__gte=prev_week, confirmed_at__lt=week_ago).aggregate(s=Sum("total_price"))["s"] or 0
        rev_delta = float(rev_this - rev_prev)
        rev_pct   = round((rev_delta / float(rev_prev) * 100), 1) if rev_prev else 0

        # All-time totals
        total_revenue = all_orders.filter(status=Order.STATUS_CONFIRMED).aggregate(s=Sum("total_price"))["s"] or 0
        total_orders  = all_orders.count()
        pending_ship  = all_orders.filter(status=Order.STATUS_PENDING).count()
        in_transit    = all_orders.filter(status=Order.STATUS_IN_TRANSIT).count()

        # Available balance = confirmed & payout NOT released
        available_balance = all_orders.filter(status=Order.STATUS_CONFIRMED, payout_released=False).aggregate(s=Sum("total_price"))["s"] or 0
        # In escrow = pending + in_transit
        in_escrow = all_orders.filter(status__in=[Order.STATUS_PENDING, Order.STATUS_IN_TRANSIT, Order.STATUS_DELIVERED]).aggregate(s=Sum("total_price"))["s"] or 0

        # Top products by confirmed orders
        top_products = (
            request.user.products
            .filter(status="live")
            .order_by("-sold")[:5]
        )
        # Low-stock products
        low_stock = (
            request.user.products
            .filter(status="live", stock__lte=5)
            .order_by("stock")[:3]
        )
        # Recent orders
        recent_orders = all_orders.select_related("buyer").order_by("-created_at")[:5]

        # Average order value
        aov = all_orders.aggregate(a=Avg("total_price"))["a"] or 0

        # Needs-attention tasks
        tasks = []
        if pending_ship:
            tasks.append({"icon": "ship", "label": f"Ship {pending_ship} pending order{'s' if pending_ship != 1 else ''}", "sub": "Buyers are waiting — ship today to keep your rating up.", "badge": "urgent"})
        low_stock_count = request.user.products.filter(status="live", stock__lte=5).count()
        if low_stock_count:
            tasks.append({"icon": "warn", "label": f"{low_stock_count} product{'s' if low_stock_count != 1 else ''} running low on stock", "sub": "Restock before they sell out.", "badge": "warn"})
        if available_balance > 0:
            tasks.append({"icon": "payout", "label": f"${available_balance:,.2f} ready for payout", "sub": "Go to Payouts to withdraw your earnings.", "badge": "new"})

        context.update({
            "rev_this": rev_this,
            "rev_prev": rev_prev,
            "rev_pct": rev_pct,
            "total_revenue": total_revenue,
            "total_orders": total_orders,
            "pending_ship": pending_ship,
            "in_transit": in_transit,
            "available_balance": available_balance,
            "in_escrow": in_escrow,
            "aov": aov,
            "top_products": top_products,
            "low_stock": low_stock,
            "recent_orders": recent_orders,
            "overview_tasks": tasks,
        })

    # ── Seller: payouts ───────────────────────────────────────
    if role == "seller" and section == "payouts":
        seller = request.user
        # Financial summary
        confirmed_orders    = Order.objects.filter(seller=seller, status=Order.STATUS_CONFIRMED)
        available_balance   = confirmed_orders.filter(payout_released=False).aggregate(s=Sum("total_price"))["s"] or 0
        in_escrow           = Order.objects.filter(seller=seller, status__in=[Order.STATUS_PENDING, Order.STATUS_IN_TRANSIT, Order.STATUS_DELIVERED]).aggregate(s=Sum("total_price"))["s"] or 0
        lifetime_paid       = SellerPayout.objects.filter(seller=seller, status=SellerPayout.STATUS_COMPLETED).aggregate(s=Sum("amount"))["s"] or 0
        pending_payout      = SellerPayout.objects.filter(seller=seller, status__in=[SellerPayout.STATUS_PENDING, SellerPayout.STATUS_PROCESSING]).aggregate(s=Sum("amount"))["s"] or 0

        payout_methods  = SellerPayoutMethod.objects.filter(user=seller)
        default_method  = payout_methods.filter(is_default=True).first()
        payout_history  = SellerPayout.objects.filter(seller=seller).select_related("payout_method").order_by("-created_at")[:20]
        payout_form     = SellerPayoutMethodForm()
        payout_records  = SellerPayoutRecord.objects.filter(seller=seller).select_related("order","payout_method").order_by("-paid_at")[:20]

        context.update({
            "available_balance":  available_balance,
            "in_escrow":          in_escrow,
            "lifetime_paid":      lifetime_paid,
            "pending_payout":     pending_payout,
            "payout_methods":     payout_methods,
            "default_method":     default_method,
            "payout_history":     payout_history,
            "payout_records":     payout_records,
            "payout_form":        payout_form,
        })

    # ── Seller: earnings ──────────────────────────────────────
    if role == "seller" and section == "earnings":
        products = list(request.user.products.filter(status="live").order_by("-sold", "-created_at"))
        gross_sales = sum((product.price * product.sold for product in products), start=0)
        marketplace_fee = gross_sales * 0.05
        processing_fee = gross_sales * 0.029 + len([p for p in products if p.sold]) * 0.30
        earning_products = [{"product": p, "gross": p.price * p.sold, "net": p.price * p.sold * 0.921} for p in products]
        context.update({"earning_products": earning_products, "gross_sales": gross_sales, "marketplace_fee": marketplace_fee, "processing_fee": processing_fee, "net_earnings": gross_sales - marketplace_fee - processing_fee, "units_sold": sum(p.sold for p in products), "live_product_count": len(products)})

    # ── Seller: orders (via generic section loader) ───────────
    if role == "seller" and section == "orders":
        qs = Order.objects.filter(seller=request.user).select_related("buyer", "product")
        q = (request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(Q(order_number__icontains=q) | Q(product_name__icontains=q) | Q(buyer__username__icontains=q))
        status_filter = request.GET.get("status") or "all"
        if status_filter != "all":
            qs = qs.filter(status=status_filter)
        paginator = Paginator(qs, 15)
        page_obj = paginator.get_page(request.GET.get("page"))
        context.update({"orders": page_obj.object_list, "page_obj": page_obj, "search_q": q, "status_filter": status_filter})

    # ── Buyer: orders ─────────────────────────────────────────
    if role == "buyer" and section == "orders":
        qs = Order.objects.filter(buyer=request.user).select_related("seller", "product")
        context.update({"orders": list(qs)})

    # ── Buyer: wishlist ───────────────────────────────────────
    if role == "buyer" and section == "wishlist":
        context["wishlist_items"] = (WishlistItem.objects.filter(user=request.user) if request.user.is_authenticated else [])

    # ── Admin: orders ─────────────────────────────────────────
    if role == "admin" and section == "orders":
        qs = Order.objects.all().select_related("buyer", "seller", "product").order_by("-created_at")
        q = (request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(Q(order_number__icontains=q) | Q(product_name__icontains=q) | Q(buyer__username__icontains=q) | Q(seller__username__icontains=q))
        status_filter = request.GET.get("status") or "all"
        if status_filter != "all":
            qs = qs.filter(status=status_filter)
        paginator = Paginator(qs, 20)
        page_obj = paginator.get_page(request.GET.get("page"))
        context.update({"orders": page_obj.object_list, "page_obj": page_obj, "search_q": q, "status_filter": status_filter, "payout_ready_count": Order.objects.filter(status=Order.STATUS_CONFIRMED, payout_released=False).count()})

    # ── Admin: overview ───────────────────────────────────────
    if role == "admin" and section == "overview":
        total_revenue = Order.objects.filter(status=Order.STATUS_CONFIRMED).aggregate(s=Sum("total_price"))["s"] or 0
        pending_escrow = Order.objects.filter(status__in=[Order.STATUS_PENDING, Order.STATUS_IN_TRANSIT, Order.STATUS_DELIVERED]).aggregate(s=Sum("total_price"))["s"] or 0
        total_confirmed_orders = Order.objects.filter(status=Order.STATUS_CONFIRMED).count()
        recent_orders = Order.objects.select_related("buyer", "seller").order_by("-created_at")[:8]
        # Payment method split
        pi_revenue = Order.objects.filter(status=Order.STATUS_CONFIRMED, payment_method="pi").aggregate(s=Sum("total_price"))["s"] or 0
        paypal_revenue = Order.objects.filter(status=Order.STATUS_CONFIRMED, payment_method="paypal").aggregate(s=Sum("total_price"))["s"] or 0
        paystack_revenue = Order.objects.filter(status=Order.STATUS_CONFIRMED, payment_method="paystack").aggregate(s=Sum("total_price"))["s"] or 0
        total_for_pct = float(pi_revenue + paypal_revenue + paystack_revenue) or 1
        pending_verifications = SellerVerification.objects.filter(status="pending").count()
        payout_ready = Order.objects.filter(status=Order.STATUS_CONFIRMED, payout_released=False).count()
        context.update({
            "total_revenue": total_revenue,
            "pending_escrow": pending_escrow,
            "total_confirmed_orders": total_confirmed_orders,
            "recent_orders": recent_orders,
            "pi_revenue": pi_revenue,
            "paypal_revenue": paypal_revenue,
            "paystack_revenue": paystack_revenue,
            "pi_pct": round(float(pi_revenue) / total_for_pct * 100),
            "paypal_pct": round(float(paypal_revenue) / total_for_pct * 100),
            "paystack_pct": round(float(paystack_revenue) / total_for_pct * 100),
            "payout_ready": payout_ready,
            "pending_verifications": pending_verifications,
        })

    # ── Admin: payments ───────────────────────────────────────
    if role == "admin" and section == "payments":
        pay_qs = Order.objects.filter(status=Order.STATUS_CONFIRMED).order_by("-confirmed_at")
        q = (request.GET.get("q") or "").strip()
        if q:
            pay_qs = pay_qs.filter(Q(order_number__icontains=q) | Q(buyer__username__icontains=q) | Q(product_name__icontains=q))
        method_f = request.GET.get("method") or "all"
        if method_f != "all":
            pay_qs = pay_qs.filter(payment_method=method_f)
        paginatorp = Paginator(pay_qs, 20)
        page_obj_p = paginatorp.get_page(request.GET.get("page"))
        pi_total     = Order.objects.filter(status=Order.STATUS_CONFIRMED, payment_method="pi").aggregate(s=Sum("total_price"))["s"] or 0
        paypal_total = Order.objects.filter(status=Order.STATUS_CONFIRMED, payment_method="paypal").aggregate(s=Sum("total_price"))["s"] or 0
        paystack_total = Order.objects.filter(status=Order.STATUS_CONFIRMED, payment_method="paystack").aggregate(s=Sum("total_price"))["s"] or 0
        context.update({
            "payments": page_obj_p.object_list,
            "page_obj": page_obj_p,
            "search_q": q,
            "method_filter": method_f,
            "pi_total": pi_total,
            "paypal_total": paypal_total,
            "paystack_total": paystack_total,
            "grand_total": pi_total + paypal_total + paystack_total,
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

@login_required
def seller_orders_view(request):
    """Dedicated seller orders page (also handles AJAX section load)."""
    if request.user.role != "seller":
        return redirect("dashboard")
    context = dashboard_context(request, "seller", "orders")
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
    context.update({
        "orders": page_obj.object_list,
        "page_obj": page_obj,
        "search_q": q,
        "status_filter": status_filter,
    })
    template = "dashboards/seller/orders.html"
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return render(request, template, context)
    context["dashboard_template"] = template
    return render(request, "dashboards/base.html", context)


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
        OrderTrackingEvent.objects.create(order=order, status="in_transit", message="Your order has been shipped and is now in transit.")
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
        order.delivery_note = request.POST.get("delivery_note", "").strip()
        order.save()
        OrderTrackingEvent.objects.create(order=order, status="delivered", message=order.delivery_note or "Seller marked this order as delivered.")
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"ok": True, "status": order.status, "label": order.status_label, "css": order.status_css})
        messages.success(request, f"Order #{order.order_number} marked as delivered. Buyer has 48 hours to confirm.")
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
@login_required
def order_not_delivered(request, pk):
    """Buyer disputes an incorrectly claimed delivery; escrow remains held."""
    order = get_object_or_404(Order, pk=pk, buyer=request.user)
    if order.status == Order.STATUS_DELIVERED:
        order.status = Order.STATUS_DISPUTED
        order.dispute_reason = request.POST.get("reason", "Buyer reports the item was not delivered.").strip()
        order.disputed_at = timezone.now()
        order.save(update_fields=["status", "dispute_reason", "disputed_at", "updated_at"])
        OrderTrackingEvent.objects.create(order=order, status="disputed", message="Buyer reported that the delivery was not received.")
        messages.success(request, "Your delivery report has been sent to the admin team. Escrow remains protected.")
    return redirect("dashboard_section", role="buyer", section="orders")


@require_POST
@login_required
@require_POST
@login_required
def order_request_refund(request, pk):
    """Buyer submits a refund complaint via the modal form."""
    order = get_object_or_404(Order, pk=pk, buyer=request.user)
    if order.status not in (Order.STATUS_DELIVERED, Order.STATUS_DISPUTED, Order.STATUS_IN_TRANSIT):
        messages.error(request, "This order cannot be refunded at this stage.")
        return redirect("dashboard_section", role="buyer", section="orders")

    reason = request.POST.get("reason", "").strip()
    if not reason:
        messages.error(request, "Please describe your complaint before submitting.")
        return redirect("dashboard_section", role="buyer", section="orders")

    # Mark the order as disputed
    order.status = Order.STATUS_DISPUTED
    order.dispute_reason = reason
    order.disputed_at = timezone.now()
    order.save(update_fields=["status", "dispute_reason", "disputed_at", "updated_at"])

    OrderTrackingEvent.objects.create(
        order=order, status="refund_requested",
        message="Buyer requested a refund; admin review is required."
    )

    # Create or update the RefundComplaint record
    complaint, _ = RefundComplaint.objects.get_or_create(
        order=order,
        defaults={"buyer": request.user},
    )
    complaint.buyer              = request.user
    complaint.reason             = reason
    complaint.refund_method      = request.POST.get("refund_method", "").strip()
    complaint.refund_bank_name   = request.POST.get("refund_bank_name", "").strip()
    complaint.refund_account_no  = request.POST.get("refund_account_no", "").strip()
    complaint.refund_account_name = request.POST.get("refund_account_name", "").strip()
    complaint.refund_wallet      = request.POST.get("refund_wallet", "").strip()
    complaint.status             = RefundComplaint.STATUS_OPEN
    complaint.save()

    # Initial message in the thread
    RefundMessage.objects.create(
        complaint=complaint,
        sender=request.user,
        body=reason,
        is_admin=False,
        read_by_admin=False,
        read_by_buyer=True,
    )

    messages.success(request, "Refund complaint submitted. An admin will review and reply shortly.")
    return redirect("dashboard_section", role="buyer", section="orders")


@require_POST
@staff_member_required
def order_release_payout(request, pk):
    """Admin: mark a confirmed order's escrow as paid to the seller.

    Creates a SellerPayoutRecord so the seller can see it on their dashboard.
    """
    order = get_object_or_404(Order, pk=pk)
    if order.status == Order.STATUS_CONFIRMED and not order.payout_released:
        order.payout_released    = True
        order.payout_released_at = timezone.now()
        order.save(update_fields=["payout_released", "payout_released_at", "updated_at"])

        # Create a payout record visible in the seller dashboard
        default_method = SellerPayoutMethod.objects.filter(
            user=order.seller, is_default=True
        ).first()
        note = request.POST.get("note", "").strip() or f"Payout for order #{order.order_number}"
        SellerPayoutRecord.objects.get_or_create(
            order=order,
            defaults={
                "seller":        order.seller,
                "payout_method": default_method,
                "amount":        order.total_price,
                "currency":      "USD",
                "note":          note,
                "paid_by":       request.user,
            }
        )

        OrderTrackingEvent.objects.create(
            order=order, status="payout_released",
            message=f"Admin marked payout as sent to seller ({request.user.username})."
        )

        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"ok": True, "order_number": order.order_number})
        messages.success(request, f"Payout marked as sent for order #{order.order_number}.")
    return redirect("admin_seller_payouts")


@require_POST
@staff_member_required
def order_admin_refund(request, pk):
    """Admin resolves a delivery dispute by returning the escrowed payment."""
    order = get_object_or_404(Order, pk=pk)
    if order.status == Order.STATUS_DISPUTED and not order.payout_released:
        order.status = Order.STATUS_REFUNDED
        order.save(update_fields=["status", "updated_at"])
        OrderTrackingEvent.objects.create(order=order, status="refunded", message="Admin approved the refund. Escrow payment will be returned to the buyer.")
        messages.success(request, f"Refund approved for {order.order_number}.")
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


# ═══════════════════════════════════════════════════════════════
#  PAYOUT VIEWS
# ═══════════════════════════════════════════════════════════════

@require_POST
@login_required
def seller_save_payout_method(request):
    """Save or update a seller's payout method (bank / Pi / PayPal)."""
    if request.user.role != "seller":
        return JsonResponse({"error": "Forbidden."}, status=403)

    form = SellerPayoutMethodForm(request.POST)
    if form.is_valid():
        method = form.save(commit=False)
        method.user = request.user
        # If marked as default, unset all others
        if method.is_default or not SellerPayoutMethod.objects.filter(user=request.user).exists():
            SellerPayoutMethod.objects.filter(user=request.user).update(is_default=False)
            method.is_default = True
        method.save()
        messages.success(request, "Payout method saved successfully.")
    else:
        for field, errs in form.errors.items():
            messages.error(request, f"{field}: {errs[0]}")

    return redirect("dashboard_section", role="seller", section="payouts")


@require_POST
@login_required
def seller_delete_payout_method(request, pk):
    """Delete one of the seller's payout methods."""
    if request.user.role != "seller":
        return JsonResponse({"error": "Forbidden."}, status=403)
    method = get_object_or_404(SellerPayoutMethod, pk=pk, user=request.user)
    method.delete()
    # If no default left, promote the most recent one
    remaining = SellerPayoutMethod.objects.filter(user=request.user)
    if remaining.exists() and not remaining.filter(is_default=True).exists():
        first = remaining.first()
        first.is_default = True
        first.save(update_fields=["is_default"])
    messages.success(request, "Payout method removed.")
    return redirect("dashboard_section", role="seller", section="payouts")


@require_POST
@login_required
def seller_set_default_payout_method(request, pk):
    """Set a payout method as the default."""
    if request.user.role != "seller":
        return JsonResponse({"error": "Forbidden."}, status=403)
    method = get_object_or_404(SellerPayoutMethod, pk=pk, user=request.user)
    SellerPayoutMethod.objects.filter(user=request.user).update(is_default=False)
    method.is_default = True
    method.save(update_fields=["is_default"])
    messages.success(request, f"{method} set as default payout method.")
    return redirect("dashboard_section", role="seller", section="payouts")


@require_POST
@login_required
def seller_request_payout(request):
    """Seller requests a manual payout of their available balance."""
    if request.user.role != "seller":
        return JsonResponse({"error": "Forbidden."}, status=403)

    # Calculate available balance
    available = Order.objects.filter(
        seller=request.user,
        status=Order.STATUS_CONFIRMED,
        payout_released=False,
    ).aggregate(s=Sum("total_price"))["s"] or 0

    if available <= 0:
        messages.warning(request, "You have no available balance to withdraw.")
        return redirect("dashboard_section", role="seller", section="payouts")

    minimum = 10  # $10 minimum payout
    if float(available) < minimum:
        messages.warning(request, f"Minimum payout is ${minimum:.2f}. Your balance is ${available:.2f}.")
        return redirect("dashboard_section", role="seller", section="payouts")

    # Check for already-pending payout
    if SellerPayout.objects.filter(seller=request.user, status__in=[SellerPayout.STATUS_PENDING, SellerPayout.STATUS_PROCESSING]).exists():
        messages.info(request, "You already have a payout in progress. Please wait for it to complete.")
        return redirect("dashboard_section", role="seller", section="payouts")

    default_method = SellerPayoutMethod.objects.filter(user=request.user, is_default=True).first()
    if not default_method:
        messages.error(request, "Please add a payout method before requesting a withdrawal.")
        return redirect("dashboard_section", role="seller", section="payouts")

    payout = SellerPayout.objects.create(
        seller=request.user,
        payout_method=default_method,
        amount=available,
        currency="USD",
        status=SellerPayout.STATUS_PENDING,
        note="Seller-initiated withdrawal",
    )
    # Mark those confirmed orders as payout_released
    Order.objects.filter(
        seller=request.user,
        status=Order.STATUS_CONFIRMED,
        payout_released=False,
    ).update(payout_released=True, payout_released_at=timezone.now())

    messages.success(request, f"Payout of ${available:,.2f} requested (ref: {payout.reference}). Estimated arrival: 1–2 business days.")
    return redirect("dashboard_section", role="seller", section="payouts")


# ═══════════════════════════════════════════════════════════════
#  ADMIN: USERS
# ═══════════════════════════════════════════════════════════════

@staff_member_required
def admin_users_view(request):
    User = get_user_model()
    qs   = User.objects.all().order_by("-date_joined")

    q = (request.GET.get("q") or "").strip()
    if q:
        qs = qs.filter(
            Q(username__icontains=q) | Q(email__icontains=q) |
            Q(first_name__icontains=q) | Q(last_name__icontains=q)
        )

    role_filter = request.GET.get("role") or "all"
    if role_filter == "buyer":
        qs = qs.filter(role="buyer")
    elif role_filter == "seller":
        qs = qs.filter(role="seller")
    elif role_filter == "admin":
        qs = qs.filter(is_staff=True)

    paginator = Paginator(qs, 20)
    page_obj  = paginator.get_page(request.GET.get("page"))

    context = dashboard_context(request, "admin", "users")
    context.update({
        "users_list":   page_obj.object_list,
        "page_obj":     page_obj,
        "search_q":     q,
        "role_filter":  role_filter,
        "buyers_count":  User.objects.filter(role="buyer").count(),
        "sellers_count": User.objects.filter(role="seller").count(),
        "admins_count":  User.objects.filter(is_staff=True).count(),
        "dashboard_template": "dashboards/admin/users.html",
    })
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return render(request, "dashboards/admin/users.html", context)
    return render(request, "dashboards/base.html", context)


@require_POST
@staff_member_required
def admin_user_toggle_active(request, pk):
    User   = get_user_model()
    target = get_object_or_404(User, pk=pk)
    if target == request.user:
        return JsonResponse({"error": "Cannot deactivate yourself."}, status=400)
    target.is_active = not target.is_active
    target.save(update_fields=["is_active"])
    return JsonResponse({"ok": True, "is_active": target.is_active})


@require_POST
@staff_member_required
def admin_user_delete(request, pk):
    User = get_user_model()
    target = get_object_or_404(User, pk=pk)
    if target == request.user or target.is_staff:
        return JsonResponse({"error": "This administrator cannot be deleted."}, status=400)
    # Preserve financial history; account removal is a safe access revocation.
    target.is_active = False
    target.save(update_fields=["is_active"])
    messages.success(request, f"{target.username}'s account has been suspended. Order records were retained.")
    return JsonResponse({"ok": True, "is_active": False})


# ═══════════════════════════════════════════════════════════════
#  ADMIN: PRODUCTS
# ═══════════════════════════════════════════════════════════════

@staff_member_required
def admin_products_view(request):
    qs = Product.objects.all().select_related("seller").order_by("-created_at")

    q = (request.GET.get("q") or "").strip()
    if q:
        qs = qs.filter(
            Q(name__icontains=q) | Q(store_name__icontains=q) |
            Q(seller__username__icontains=q)
        )

    cat_filter = request.GET.get("category") or "all"
    if cat_filter != "all":
        qs = qs.filter(category=cat_filter)

    status_filter = request.GET.get("status") or "all"
    if status_filter == "live":
        qs = qs.filter(status="live")
    elif status_filter == "draft":
        qs = qs.filter(status="draft")

    paginator = Paginator(qs, 20)
    page_obj  = paginator.get_page(request.GET.get("page"))

    context = dashboard_context(request, "admin", "products")
    context.update({
        "products":      page_obj.object_list,
        "page_obj":      page_obj,
        "search_q":      q,
        "cat_filter":    cat_filter,
        "status_filter": status_filter,
        "categories":    Product.CATEGORY_CHOICES,
        "total_live":    Product.objects.filter(status="live").count(),
        "total_draft":   Product.objects.filter(status="draft").count(),
        "dashboard_template": "dashboards/admin/products.html",
    })
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return render(request, "dashboards/admin/products.html", context)
    return render(request, "dashboards/base.html", context)


@require_POST
@staff_member_required
def admin_product_toggle_status(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.status = "draft" if product.status == "live" else "live"
    product.save(update_fields=["status"])
    return JsonResponse({"ok": True, "status": product.status})


@require_POST
@staff_member_required
def admin_product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.delete()
    messages.success(request, f'"{product.name}" has been deleted.')
    return redirect("admin_products_view")


# ═══════════════════════════════════════════════════════════════
#  ADMIN: FEATURED / BOOST PLANS
# ═══════════════════════════════════════════════════════════════

@staff_member_required
def admin_featured_view(request):
    boost_plans = BoostPlan.objects.all()

    q = (request.GET.get("q") or "").strip()
    boosts_qs = BoostOrder.objects.select_related("seller", "product", "plan").order_by("-created_at")
    if q:
        boosts_qs = boosts_qs.filter(
            Q(product__name__icontains=q) | Q(seller__username__icontains=q) | Q(plan_name__icontains=q)
        )
    status_f = request.GET.get("status") or "all"
    if status_f != "all":
        boosts_qs = boosts_qs.filter(status=status_f)

    paginator = Paginator(boosts_qs, 15)
    page_obj  = paginator.get_page(request.GET.get("page"))

    form = BoostPlanForm()
    context = dashboard_context(request, "admin", "featured")
    context.update({
        "boost_plans":   boost_plans,
        "boost_orders":  page_obj.object_list,
        "page_obj":      page_obj,
        "search_q":      q,
        "status_filter": status_f,
        "boost_form":    form,
        "active_count":  BoostOrder.objects.filter(status=BoostOrder.STATUS_PAID).count(),
        "dashboard_template": "dashboards/admin/featured.html",
    })
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return render(request, "dashboards/admin/featured.html", context)
    return render(request, "dashboards/base.html", context)


@require_POST
@staff_member_required
def admin_boost_plan_create(request):
    form = BoostPlanForm(request.POST)
    if form.is_valid():
        form.save()
        messages.success(request, "Boost plan created.")
    else:
        for errs in form.errors.values():
            messages.error(request, errs[0])
    return redirect("admin_featured_view")


@require_POST
@staff_member_required
def admin_boost_plan_delete(request, pk):
    plan = get_object_or_404(BoostPlan, pk=pk)
    plan.is_active = False
    plan.save(update_fields=["is_active"])
    messages.success(request, f'"{plan.name}" deactivated.')
    return redirect("admin_featured_view")


@require_POST
@staff_member_required
def admin_boost_order_remove(request, pk):
    bo = get_object_or_404(BoostOrder, pk=pk)
    bo.status = BoostOrder.STATUS_EXPIRED
    bo.save(update_fields=["status"])
    messages.success(request, f"Boost {bo.reference} expired.")
    return redirect("admin_featured_view")


# ═══════════════════════════════════════════════════════════════
#  SELLER: BOOST CHECKOUT
# ═══════════════════════════════════════════════════════════════

@login_required
def seller_boost_checkout(request, product_pk):
    """Seller picks a boost plan and pays for it."""
    if request.user.role != "seller":
        return redirect("dashboard")
    product = get_object_or_404(Product, pk=product_pk, seller=request.user)
    plans   = BoostPlan.objects.filter(is_active=True)

    if request.method == "POST":
        plan_pk        = request.POST.get("plan")
        payment_method = request.POST.get("payment_method", "paypal")
        plan = get_object_or_404(BoostPlan, pk=plan_pk, is_active=True)

        # The seller pays in the currency of the payment method they chose
        # (PayPal → USD, Pi Network → PI, Paystack → NGN).
        currency = BoostOrder.PAYMENT_CURRENCY.get(payment_method, "USD")
        live_rates = BoostOrder.rates_to_usd()
        amount   = plan.price * live_rates[currency]
        amount   = amount.quantize(Decimal("0.01"))

        boost = BoostOrder.objects.create(
            seller         = request.user,
            product        = product,
            plan           = plan,
            plan_name      = plan.name,
            amount         = amount,
            currency       = currency,
            duration_days  = plan.duration_days,
            status         = BoostOrder.STATUS_PAID,   # demo: instant activation
            payment_method = payment_method,
            paid_at        = timezone.now(),
            expires_at     = timezone.now() + timezone.timedelta(days=plan.duration_days),
        )
        messages.success(
            request,
            f'"{product.name}" is now boosted with {plan.name} for {plan.duration_days} days — '
            f'{boost.amount_display} charged via {boost.get_payment_method_display()}.'
        )
        return redirect("seller_products")

    context = dashboard_context(request, "seller", "products")
    context.update({
        "product":        product,
        "plans":          plans,
        "page_title":     f"Boost: {product.name}",
        "ngn_per_usd":    float(CurrencyRate.ngn_per_usd()),
        "pi_per_usd":     float(CurrencyRate.pi_per_usd()),
        "dashboard_template": "boost_checkout.html",
    })
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return render(request, "boost_checkout.html", context)
    return render(request, "dashboards/base.html", context)


# ═══════════════════════════════════════════════════════════════
#  CART API  (DB-backed for logged-in buyers)
# ═══════════════════════════════════════════════════════════════

@require_POST
@login_required
def cart_add(request, product_pk):
    """Add or increment a product in the DB cart."""
    product = get_object_or_404(Product, pk=product_pk, status="live")
    qty     = max(1, int(request.POST.get("quantity", 1)))

    item, created = CartItem.objects.get_or_create(
        user=request.user, product=product,
        defaults={"quantity": qty},
    )
    if not created:
        item.quantity += qty
        item.save(update_fields=["quantity"])

    total_qty = CartItem.objects.filter(user=request.user).aggregate(s=Sum("quantity"))["s"] or 0
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"ok": True, "cart_count": total_qty})
    return redirect(request.META.get("HTTP_REFERER", "/shop/"))


@require_POST
@login_required
def cart_update(request, product_pk):
    """Set exact quantity; 0 removes the item."""
    item    = get_object_or_404(CartItem, user=request.user, product_id=product_pk)
    qty     = int(request.POST.get("quantity", 1))
    if qty <= 0:
        item.delete()
    else:
        item.quantity = qty
        item.save(update_fields=["quantity"])
    total_qty = CartItem.objects.filter(user=request.user).aggregate(s=Sum("quantity"))["s"] or 0
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"ok": True, "cart_count": total_qty})
    return redirect("/checkout/")


@require_POST
@login_required
def cart_remove(request, product_pk):
    CartItem.objects.filter(user=request.user, product_id=product_pk).delete()
    total_qty = CartItem.objects.filter(user=request.user).aggregate(s=Sum("quantity"))["s"] or 0
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"ok": True, "cart_count": total_qty})
    return redirect("/checkout/")


def cart_context(request):
    """Return cart items + totals for a logged-in buyer (used in checkout view)."""
    from dropshipping import payments as _pay
    if request.user.is_authenticated:
        items    = CartItem.objects.filter(user=request.user).select_related("product")
        subtotal = sum(it.line_total for it in items)
        count    = sum(it.quantity for it in items)
    else:
        items    = []
        subtotal = 0
        count    = 0
    # Live exchange rates (from DB via CurrencyRate, fall back to settings)
    ngn_per_usd = float(_pay.usd_to_ngn(1))
    pi_per_usd  = float(_pay.usd_to_pi(1))
    escrow_pct  = int(getattr(__import__('django.conf', fromlist=['settings']).settings,
                               'CHECKOUT_ESCROW_FEE_RATE', Decimal('0.02')) * 100)
    platform_pct = int(getattr(__import__('django.conf', fromlist=['settings']).settings,
                                'CHECKOUT_PLATFORM_FEE_RATE', Decimal('0.01')) * 100)
    return {
        "cart_items":    items,
        "cart_subtotal": subtotal,
        "cart_count":    count,
        "ngn_per_usd":   ngn_per_usd,
        "pi_per_usd":    pi_per_usd,
        "escrow_pct":    escrow_pct,
        "platform_pct":  platform_pct,
    }


def checkout_view(request):
    """Checkout page — injects real DB cart for logged-in buyers."""
    from django.middleware.csrf import get_token
    get_token(request)
    ctx = {"page_title": "Checkout", "slug": "checkout"}
    ctx.update(cart_context(request))
    # Flag cart items that can no longer be fulfilled so the buyer sees the
    # problem here — before paying (see payment_views.cart_issues).
    if request.user.is_authenticated:
        ctx["addresses"] = BuyerAddress.objects.filter(user=request.user)
        from .payment_views import cart_issues
        ctx["cart_issues"] = cart_issues(request.user)
    return render(request, "checkout.html", ctx)


@login_required
def checkout_payment(request):
    """Payment selection for authenticated buyers only.

    ``login_required`` redirects guests to the sign-in page with this URL in
    its ``next`` parameter, so they return here immediately after signing in.
    """
    # Redirect sellers / admins who land here by mistake
    if getattr(request.user, "role", "") not in ("buyer", ""):
        messages.error(request, "Please use a buyer account to complete a purchase.")
        return redirect("shop")

    ctx = {"page_title": "Choose payment", "slug": "checkout-payment"}
    # Real cart, real totals and the payment rails that are actually configured
    # (see dashboards/payment_views.py — nothing is charged without one of them).
    ctx.update(payment_views.checkout_context(request))
    # Same pre-payment availability check as /checkout/ — Pay itself will also
    # refuse to start while any item is unfulfillable.
    if request.user.is_authenticated:
        ctx["cart_issues"] = payment_views.cart_issues(request.user)

    return render(request, "checkout-payment.html", ctx)


@require_POST
@login_required
def cart_sync(request):
    """Accept a JSON array of localStorage cart items and upsert them into the
    DB CartItem table for the logged-in buyer.

    Expected body:
        [{"product_pk": 12, "quantity": 2}, ...]

    Returns:
        {"ok": true, "count": <total items in DB cart>}
    """
    if request.user.role != "buyer":
        return JsonResponse({"error": "Buyer account required."}, status=403)
    try:
        import json as _json
        payload = _json.loads(request.body)
    except (ValueError, TypeError):
        return JsonResponse({"error": "Invalid JSON body."}, status=400)

    if not isinstance(payload, list):
        return JsonResponse({"error": "Expected a list of cart items."}, status=400)

    # Resolve every payload entry into a desired {product_pk: (product, qty)} map.
    desired = {}
    for entry in payload:
        raw = str(entry.get("product_pk") or entry.get("pk") or entry.get("id") or "").strip()
        try:
            qty = max(1, int(entry.get("quantity") or entry.get("qty") or 1))
        except (ValueError, TypeError):
            continue

        # Resolve the product: numeric PK first, then name/slug (older
        # localStorage carts stored a slugified name as the id, which used
        # to leave the DB cart empty and made payment fail with
        # "Your cart is empty.")
        product = None
        if raw.isdigit():
            product = Product.objects.filter(pk=int(raw), status="live").first()
        if product is None and raw and not raw.isdigit():
            import re as _re
            target = _re.sub(r"[^a-z0-9]+", "_", raw.lower()).strip("_")
            for prod in Product.objects.filter(status="live").only("id", "name"):
                candidate = _re.sub(r"[^a-z0-9]+", "_", (prod.name or "").lower()).strip("_")
                if candidate == target:
                    product = prod
                    break
        if product is not None:
            desired[product.pk] = (product, qty)

    # The browser cart (localStorage dropdown) is the source of truth for a
    # signed-in buyer: mirror it exactly into the DB and report whether
    # anything differed, so checkout pages can reload once to re-render.
    changed = False
    existing = {item.product_id: item for item in CartItem.objects.filter(user=request.user)}

    # Remove DB items the buyer no longer has in the browser cart.
    for pid, item in existing.items():
        if pid not in desired:
            item.delete()
            changed = True

    # Upsert the rest with the exact browser quantity.
    for pid, (product, qty) in desired.items():
        item = existing.get(pid)
        if item is None:
            CartItem.objects.create(user=request.user, product=product, quantity=qty)
            changed = True
        elif item.quantity != qty:
            item.quantity = qty
            item.save(update_fields=["quantity"])
            changed = True

    count = CartItem.objects.filter(user=request.user).aggregate(s=Sum("quantity"))["s"] or 0
    return JsonResponse({"ok": True, "synced": len(desired), "count": int(count), "changed": changed})


# Payments used to be "completed" here without contacting a provider, which
# meant anyone could create an escrow order for free.  The whole flow now lives
# in dashboards/payment_views.py (Paystack / PayPal / Pi) and orders are only
# created after the provider confirms the money.
#
# ``/dashboards/checkout/complete/`` is kept as an alias of ``payment_start`` so
# older pages that still post to it keep working — they simply start a real
# payment instead of creating an order.


@login_required
def checkout_success_view(request):
    """Order confirmation page — shows real order data from the session."""
    pks    = request.session.pop("last_order_pks", [])
    method = request.session.pop("last_order_payment_method", "")
    awaiting = request.session.pop("last_payment_awaiting_confirmation", False)
    intent_ref = request.session.pop("last_intent_reference", "")

    orders = (
        list(Order.objects.filter(pk__in=pks, buyer=request.user))
        if pks else []
    )

    # Pi payments awaiting admin verification have no orders yet — pull the
    # expected subtotal total from the stored intent so the buyer sees real amounts.
    if not orders and awaiting and method == "pi" and intent_ref:
        try:
            intent = PaymentIntent.objects.filter(
                reference=intent_ref, user=request.user, method="pi"
            ).first()
            if intent and intent.status == PaymentIntent.STATUS_PI_PENDING:
                subtotal = intent.subtotal_usd
                total = intent.amount_usd
                # Build lightweight "pending" order objects so the template's
                # order loop still renders the cart items from the snapshot.
                snapshot = (intent.provider_payload or {}).get("cart_snapshot", [])
                from shop.models import Product
                orders = []
                for item in snapshot:
                    try:
                        product = Product.objects.get(pk=item["product_pk"])
                    except Product.DoesNotExist:
                        continue
                    orders.append(type("PendingOrder", (), {
                        "pk": None, "order_number": "—",
                        "product_name": item["product_name"],
                        "product_image": product.image_src,
                        "store_name": product.get_store_display(),
                        "total_price": product.price * item["quantity"],
                        "quantity": item["quantity"],
                        "unit_price": product.price,
                        "payment_method": "pi",
                        "display_price": None,
                    })())
                totals = payment_views.cart_totals(subtotal)
                totals["total"] = total
        except Exception:
            pass
    else:
        totals = payment_views.cart_totals(sum((o.total_price for o in orders), Decimal("0")))

    # ── Show the summary in the currency the buyer actually paid with ──
    # Paystack charges Naira, Pi charges π, PayPal charges US dollars.
    from dropshipping import payments as payments_mod

    if method == "paystack":
        symbol, show_cents = "\u20a6", False          # ₦ — whole Naira
        convert = payments_mod.usd_to_ngn
        currency_name = "Nigerian Naira (\u20a6)"
    elif method == "pi":
        symbol, show_cents = "\u03c0", True            # π — 2 decimals
        convert = payments_mod.usd_to_pi
        currency_name = "Pi Network (\u03c0)"
    else:
        symbol, show_cents = "$", True                 # USD — 2 decimals
        convert = lambda value: payments_mod.money(value)
        currency_name = "US Dollar ($)"

    def paid_fmt(value):
        amount = convert(value)
        if show_cents:
            return f"{symbol}{amount:,.2f}"
        return f"{symbol}{amount:,.0f}"

    # Each order line shows the amount in the paid currency too.
    for order in orders:
        order.display_price = paid_fmt(order.total_price)

    ctx = {
        "page_title":              "Order Confirmed",
        "orders":                  orders,
        "payment_method":          method or (orders[0].payment_method if orders else ""),
        "payment_awaiting_review": awaiting,
        "order_subtotal":          totals["subtotal"],
        "order_escrow_fee":        totals["escrow"],
        "order_platform_fee":      totals["platform"],
        "order_total":             totals["total"],
        # Amounts already converted into the currency the buyer paid with.
        "paid_currency_name":      currency_name,
        "paid_symbol":             symbol,
        "paid_subtotal":           paid_fmt(totals["subtotal"]),
        "paid_escrow_fee":         paid_fmt(totals["escrow"]),
        "paid_platform_fee":       paid_fmt(totals["platform"]),
        "paid_total":              paid_fmt(totals["total"]),
    }
    return render(request, "checkout-success.html", ctx)


# ═══════════════════════════════════════════════════════════════
#  ADMIN: VERIFICATION DETAIL
# ═══════════════════════════════════════════════════════════════

@staff_member_required
def admin_verification_detail(request, pk):
    """Show full verification document for a specific seller — admin only."""
    verification = get_object_or_404(SellerVerification.objects.select_related("user"), pk=pk)
    context = dashboard_context(request, "admin", "verifications")
    context.update({
        "page_title": f"Verification — {verification.user.username}",
        "verification": verification,
        "dashboard_template": "dashboards/admin/verification_detail.html",
    })
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return render(request, "dashboards/admin/verification_detail.html", context)
    return render(request, "dashboards/base.html", context)


# ═══════════════════════════════════════════════════════════════
#  ADMIN: CURRENCY RATES
# ═══════════════════════════════════════════════════════════════

@staff_member_required
def admin_currency_rates(request):
    """Admin page to view and update USD→NGN and USD→PI exchange rates.

    The rates stored here are the single source of truth for all money
    conversions across checkout, boost pricing and payment provider charges.
    They override the env-var defaults in settings.py.
    """
    if request.method == "POST":
        errors = []
        for pair in (CurrencyRate.PAIR_USD_NGN, CurrencyRate.PAIR_USD_PI):
            raw = request.POST.get(pair, "").strip()
            if not raw:
                continue
            try:
                from decimal import Decimal as _D, InvalidOperation
                value = _D(raw)
                if value <= 0:
                    raise ValueError("Rate must be positive.")
                note = request.POST.get(f"{pair}_note", "").strip()
                obj, _ = CurrencyRate.objects.update_or_create(
                    pair=pair,
                    defaults={"rate": value, "note": note},
                )
            except (InvalidOperation, ValueError) as exc:
                errors.append(f"{pair}: {exc}")

        # After saving rates, sync them into the live settings so the
        # running process uses them immediately (no restart needed).
        try:
            from django.conf import settings as _settings
            _settings.NGN_PER_USD = CurrencyRate.ngn_per_usd()
            _settings.PI_PER_USD  = CurrencyRate.pi_per_usd()
        except Exception:
            pass  # settings sync is best-effort — DB values are authoritative

        if errors:
            for e in errors:
                messages.error(request, e)
        else:
            messages.success(request, "Exchange rates updated successfully.")
        return redirect("admin_currency_rates")

    rates = {obj.pair: obj for obj in CurrencyRate.objects.all()}
    ngn_obj = rates.get(CurrencyRate.PAIR_USD_NGN)
    pi_obj  = rates.get(CurrencyRate.PAIR_USD_PI)

    context = dashboard_context(request, "admin", "currency_rates")
    context.update({
        "page_title":        "Currency Rates",
        "section":           "currency_rates",
        "ngn_obj":           ngn_obj,
        "pi_obj":            pi_obj,
        "current_ngn":       CurrencyRate.ngn_per_usd(),
        "current_pi":        CurrencyRate.pi_per_usd(),
        "PAIR_USD_NGN":      CurrencyRate.PAIR_USD_NGN,
        "PAIR_USD_PI":       CurrencyRate.PAIR_USD_PI,
        "dashboard_template": "dashboards/admin/currency_rates.html",
    })
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return render(request, "dashboards/admin/currency_rates.html", context)
    return render(request, "dashboards/base.html", context)


# ═══════════════════════════════════════════════════════════════
#  BUYER: reply to refund complaint thread
# ═══════════════════════════════════════════════════════════════

@require_POST
@login_required
def buyer_refund_reply(request, complaint_pk):
    """Buyer posts a reply message in their refund complaint thread."""
    complaint = get_object_or_404(RefundComplaint, pk=complaint_pk, buyer=request.user)
    body = request.POST.get("body", "").strip()
    if body:
        RefundMessage.objects.create(
            complaint=complaint,
            sender=request.user,
            body=body,
            is_admin=False,
            read_by_buyer=True,
            read_by_admin=False,
        )
        # Mark all admin messages as read by buyer while we're here
        complaint.messages.filter(is_admin=True).update(read_by_buyer=True)
    return redirect("dashboard_section", role="buyer", section="orders")


# ═══════════════════════════════════════════════════════════════
#  ADMIN: refund complaints list + detail/messaging
# ═══════════════════════════════════════════════════════════════

@staff_member_required
def admin_refund_complaints(request):
    """List all refund complaints with filter by status."""
    status_filter = request.GET.get("status", "open")
    qs = RefundComplaint.objects.select_related(
        "order", "order__seller", "order__product", "buyer"
    ).prefetch_related(
        "messages", "order__seller__payout_methods"
    )
    if status_filter and status_filter != "all":
        qs = qs.filter(status=status_filter)

    counts = {
        "open":      RefundComplaint.objects.filter(status="open").count(),
        "in_review": RefundComplaint.objects.filter(status="in_review").count(),
        "resolved":  RefundComplaint.objects.filter(status="resolved").count(),
        "rejected":  RefundComplaint.objects.filter(status="rejected").count(),
        "all":       RefundComplaint.objects.count(),
    }

    context = dashboard_context(request, "admin", "refunds")
    context.update({
        "page_title":        "Refund Complaints",
        "section":           "refunds",
        "complaints":        qs,
        "status_filter":     status_filter,
        "counts":            counts,
        "status_choices":    RefundComplaint.STATUS_CHOICES,
        "dashboard_template": "dashboards/admin/refund_complaints.html",
    })
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return render(request, "dashboards/admin/refund_complaints.html", context)
    return render(request, "dashboards/base.html", context)


@login_required
def admin_refund_complaint_detail(request, pk):
    """Admin views and messages a single refund complaint."""
    complaint = get_object_or_404(
        RefundComplaint.objects.select_related(
            "order", "order__seller", "order__product", "buyer"
        ).prefetch_related(
            "messages__sender", "order__seller__payout_methods"
        ),
        pk=pk,
    )

    if request.method == "POST":
        action = request.POST.get("action", "message")

        if action == "message" and request.user.is_staff:
            body = request.POST.get("body", "").strip()
            if body:
                RefundMessage.objects.create(
                    complaint=complaint,
                    sender=request.user,
                    body=body,
                    is_admin=True,
                    read_by_admin=True,
                    read_by_buyer=False,
                )
                # Move to in_review automatically when admin first replies
                if complaint.status == RefundComplaint.STATUS_OPEN:
                    complaint.status = RefundComplaint.STATUS_IN_REVIEW
                    complaint.save(update_fields=["status", "updated_at"])
                messages.success(request, "Reply sent to buyer.")

        elif action == "resolve" and request.user.is_staff:
            complaint.status = RefundComplaint.STATUS_RESOLVED
            complaint.admin_note = request.POST.get("admin_note", "").strip()
            complaint.save(update_fields=["status", "admin_note", "updated_at"])
            # Also mark order as refunded
            order = complaint.order
            order.status = Order.STATUS_REFUNDED
            order.save(update_fields=["status", "updated_at"])
            OrderTrackingEvent.objects.create(
                order=order, status="refunded",
                message="Admin approved refund after reviewing complaint."
            )
            RefundMessage.objects.create(
                complaint=complaint,
                sender=request.user,
                body=f"✅ Your refund has been approved. {complaint.admin_note}".strip(),
                is_admin=True,
                read_by_admin=True,
                read_by_buyer=False,
            )
            messages.success(request, f"Refund approved for order #{order.order_number}.")

        elif action == "reject" and request.user.is_staff:
            complaint.status = RefundComplaint.STATUS_REJECTED
            complaint.admin_note = request.POST.get("admin_note", "").strip()
            complaint.save(update_fields=["status", "admin_note", "updated_at"])
            RefundMessage.objects.create(
                complaint=complaint,
                sender=request.user,
                body=f"❌ Your refund request has been rejected. {complaint.admin_note}".strip(),
                is_admin=True,
                read_by_admin=True,
                read_by_buyer=False,
            )
            messages.success(request, "Refund complaint rejected.")

        return redirect("admin_refund_complaint_detail", pk=pk)

    # Mark buyer messages as read by admin
    complaint.messages.filter(is_admin=False).update(read_by_admin=True)

    context = dashboard_context(request, "admin", "refunds")
    context.update({
        "page_title":        f"Refund #{complaint.pk}",
        "section":           "refunds",
        "complaint":         complaint,
        "dashboard_template": "dashboards/admin/refund_complaint_detail.html",
    })
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return render(request, "dashboards/admin/refund_complaint_detail.html", context)
    return render(request, "dashboards/base.html", context)


# ═══════════════════════════════════════════════════════════════
#  ADMIN: seller payouts — confirmed orders awaiting payment
# ═══════════════════════════════════════════════════════════════

@staff_member_required
def admin_seller_payouts(request):
    """Admin page showing confirmed orders that need to be paid to sellers,
    plus a history of orders already marked paid."""

    pending_orders = (
        Order.objects.filter(status=Order.STATUS_CONFIRMED, payout_released=False)
        .select_related("seller", "product", "buyer")
        .prefetch_related("seller__payout_methods")
        .order_by("-confirmed_at")
    )

    paid_records = (
        SellerPayoutRecord.objects.select_related("order", "seller", "payout_method", "paid_by")
        .order_by("-paid_at")[:50]
    )

    # Total pending amount
    from django.db.models import Sum as _Sum
    pending_total = pending_orders.aggregate(t=_Sum("total_price"))["t"] or 0

    context = dashboard_context(request, "admin", "seller_payouts")
    context.update({
        "page_title":        "Seller Payouts",
        "section":           "seller_payouts",
        "pending_orders":    pending_orders,
        "paid_records":      paid_records,
        "pending_total":     pending_total,
        "dashboard_template": "dashboards/admin/seller_payouts.html",
    })
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return render(request, "dashboards/admin/seller_payouts.html", context)
    return render(request, "dashboards/base.html", context)
