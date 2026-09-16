from django.db import models
from django.conf import settings
from django.utils import timezone


class BuyerAddress(models.Model):
    """A saved delivery address belonging to a buyer."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="addresses")
    label = models.CharField(max_length=40, default="Home")
    recipient_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=30)
    line1 = models.CharField(max_length=160)
    line2 = models.CharField(max_length=160, blank=True)
    city = models.CharField(max_length=80)
    state = models.CharField(max_length=80, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=80, default="Nigeria")
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_default", "-updated_at"]

    def __str__(self):
        return f"{self.user.username} — {self.label}"


class WishlistItem(models.Model):
    """A product saved to a buyer's wishlist.

    Because the shop catalogue is currently static HTML (not DB-backed),
    we store the product's display data inline so the wishlist renders
    correctly even when the buyer navigates away from the shop page.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="wishlist_items",
    )
    # Stable slug used to identify the card on the shop page for heart-state sync
    product_slug = models.SlugField(max_length=120)

    # Snapshot of display data from the shop card
    name = models.CharField(max_length=200)
    store_name = models.CharField(max_length=120, default="", blank=True)
    category = models.CharField(max_length=60, default="", blank=True)
    price = models.CharField(max_length=30, default="", blank=True)   # kept as string to match display
    old_price = models.CharField(max_length=30, default="", blank=True, null=True)
    image_url = models.URLField(blank=True, default="")
    image_static = models.CharField(max_length=200, blank=True, default="")  # /static/img/… paths
    badge = models.CharField(max_length=40, blank=True, default="")
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "product_slug")
        ordering = ["-added_at"]

    def __str__(self):
        return "%s — %s" % (self.user.username, self.name)

    @property
    def display_image(self):
        """Return the best available image src."""
        if self.image_url:
            return self.image_url
        if self.image_static:
            return self.image_static
        return ""


class Order(models.Model):
    """An order placed by a buyer for a seller's product.

    Status flow:
        pending  →  in_transit  →  delivered  →  confirmed
                                                      ↑
                                         (auto after 3 days)

    Once confirmed, admin sees it as payout-ready and can release funds.
    """

    STATUS_PENDING    = "pending"
    STATUS_IN_TRANSIT = "in_transit"
    STATUS_DELIVERED  = "delivered"
    STATUS_CONFIRMED  = "confirmed"   # buyer (or auto) confirmed receipt
    STATUS_REFUNDED   = "refunded"
    STATUS_CANCELLED  = "cancelled"

    STATUS_CHOICES = [
        (STATUS_PENDING,    "Pending"),
        (STATUS_IN_TRANSIT, "In Transit"),
        (STATUS_DELIVERED,  "Delivered"),
        (STATUS_CONFIRMED,  "Confirmed"),
        (STATUS_REFUNDED,   "Refunded"),
        (STATUS_CANCELLED,  "Cancelled"),
    ]

    PAYMENT_CHOICES = [
        ("pi",       "Pi Network"),
        ("paypal",   "PayPal"),
        ("paystack", "Paystack"),
    ]

    # ── Relations ──────────────────────────────────────────────
    buyer  = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="orders",
    )
    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="sales",
    )
    product = models.ForeignKey(
        "shop.Product",
        on_delete=models.PROTECT,
        related_name="orders",
        null=True, blank=True,
    )

    # ── Snapshot fields (so order survives product edits) ──────
    product_name  = models.CharField(max_length=200)
    product_image = models.URLField(blank=True, default="")
    store_name    = models.CharField(max_length=120, default="", blank=True)

    # ── Financials ─────────────────────────────────────────────
    unit_price  = models.DecimalField(max_digits=10, decimal_places=2)
    quantity    = models.PositiveIntegerField(default=1)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    currency    = models.CharField(max_length=10, default="USD")
    payment_method = models.CharField(
        max_length=10, choices=PAYMENT_CHOICES, default="paypal"
    )

    # ── Delivery address (snapshot at order time) ──────────────
    shipping_name    = models.CharField(max_length=160, blank=True, default="")
    shipping_address = models.TextField(blank=True, default="")
    tracking_number  = models.CharField(max_length=100, blank=True, default="")

    # ── Status & lifecycle ─────────────────────────────────────
    status = models.CharField(
        max_length=12, choices=STATUS_CHOICES, default=STATUS_PENDING
    )

    # Seller marks "in_transit"
    shipped_at   = models.DateTimeField(null=True, blank=True)
    # Seller marks "delivered"
    delivered_at = models.DateTimeField(null=True, blank=True)
    # Buyer (or auto) confirms receipt
    confirmed_at = models.DateTimeField(null=True, blank=True)
    # Whether it was auto-confirmed (not manually by buyer)
    auto_confirmed = models.BooleanField(default=False)
    # Admin releases payout
    payout_released    = models.BooleanField(default=False)
    payout_released_at = models.DateTimeField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Human-readable order number (e.g. DH-10291)
    order_number = models.CharField(max_length=20, unique=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.order_number:
            # Generate a sequential-looking order number after first save
            super().save(*args, **kwargs)
            self.order_number = "DH-%05d" % self.pk
            Order.objects.filter(pk=self.pk).update(order_number=self.order_number)
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        return "#%s — %s → %s" % (self.order_number, self.buyer.username, self.product_name)

    # ── Helpers ────────────────────────────────────────────────
    @property
    def days_since_delivered(self):
        if not self.delivered_at:
            return None
        delta = (timezone.now() - self.delivered_at).days
        return delta

    @property
    def auto_confirm_due(self):
        """True when buyer hasn't confirmed and 3 days have passed since delivered."""
        if self.status != self.STATUS_DELIVERED:
            return False
        return (self.days_since_delivered or 0) >= 3

    @property
    def confirm_days_left(self):
        """How many days the buyer has left to manually confirm (max 3)."""
        if self.status != self.STATUS_DELIVERED or not self.delivered_at:
            return None
        remaining = 3 - (self.days_since_delivered or 0)
        return max(0, remaining)

    @property
    def status_label(self):
        return dict(self.STATUS_CHOICES).get(self.status, self.status.title())

    @property
    def status_css(self):
        mapping = {
            "pending":    "statusx--held",
            "in_transit": "statusx--ship",
            "delivered":  "statusx--warn",
            "confirmed":  "statusx--done",
            "refunded":   "statusx--draft",
            "cancelled":  "statusx--draft",
        }
        return mapping.get(self.status, "statusx--held")

    @property
    def payout_ready(self):
        return self.status == self.STATUS_CONFIRMED and not self.payout_released


class SellerVerification(models.Model):
    STATUS_CHOICES = [
        ("unverified", "Unverified"),
        ("pending", "Under review"),
        ("verified", "Verified"),
        ("rejected", "Needs attention"),
    ]
    ID_CHOICES = [
        ("national_id", "National ID (NIN slip / card)"),
        ("passport", "International Passport"),
        ("drivers_license", "Driver's License"),
        ("voters_card", "Voter's Card"),
    ]
    user = models.OneToOneField("accounts.User", on_delete=models.CASCADE, related_name="seller_verification")
    full_name = models.CharField(max_length=120, default="")
    store_name = models.CharField(max_length=120, default="")
    phone = models.CharField(max_length=20, default="")
    address = models.CharField(max_length=255, default="")
    city = models.CharField(max_length=80, default="")
    country = models.CharField(max_length=80, default="Nigeria")
    id_type = models.CharField(max_length=20, choices=ID_CHOICES, default="national_id")
    id_number = models.CharField(max_length=60, default="")
    document = models.FileField(upload_to="seller_docs/", blank=True, null=True)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="unverified")
    reviewer_note = models.TextField(blank=True, default="")
    submitted_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "%s — %s" % (self.store_name, self.get_status_display())

