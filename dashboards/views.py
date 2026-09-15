from django.contrib import messages
from django.contrib.auth import get_user_model
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required

from .forms import SellerVerificationForm
from .models import SellerVerification


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


def dashboard_context(request, role, section):
    User = get_user_model()
    verification = None
    if request.user.is_authenticated and role == "seller":
        try:
            verification = request.user.seller_verification
        except SellerVerification.DoesNotExist:
            verification = None
    return {
        "user": request.user,
        "role": role,
        "section": section,
        "page_title": (SECTION_TITLES.get(role, {}) or {}).get(section, section.title()),
        "total_users": User.objects.count(),
        "total_sellers": User.objects.filter(role="seller").count(),
        "total_buyers": User.objects.filter(role="buyer").count(),
        "verification": verification,
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
    return dashboard_page(request, role, section)


def dashboard_page(request, role, section):
    context = dashboard_context(request, role, section)
    template = f"dashboards/{role}/{section}.html"
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return render(request, template, context)
    context["dashboard_template"] = template
    return render(request, "dashboards/base.html", context)
