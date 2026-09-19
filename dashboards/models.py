from decimal import Decimal

from django.db import models
from django.conf import settings
from django.utils import timezone


class CurrencyRate(models.Model):
    """Admin-managed exchange rates used everywhere money is converted.

    Only one row per ``pair`` is kept (enforced by unique_together).
    All code that needs a live rate must call :func:`get_rate` instead of
    reading hard-coded values so that a single admin update propagates to
    checkout, boost pricing and Paystack/Pi charge amounts.

    Supported pairs
    ---------------
    USD_TO_NGN  –  how many Naira one US dollar buys  (e.g. 1600)
    USD_TO_PI   –  how many Pi one US dollar buys       (e.g. 2.0)
    """

    PAIR_USD_NGN = "USD_TO_NGN"
    PAIR_USD_PI  = "USD_TO_PI"

    PAIR_CHOICES = [
        (PAIR_USD_NGN, "USD → NGN  (Naira per dollar)"),
        (PAIR_USD_PI,  "USD → PI   (Pi per dollar)"),
    ]

    pair = models.CharField(max_length=20, choices=PAIR_CHOICES, unique=True)
    rate = models.DecimalField(max_digits=18, decimal_places=6)
    updated_at = models.DateTimeField(auto_now=True)
    note = models.CharField(max_length=200, blank=True, default="")

    class Meta:
        ordering = ["pair"]
        verbose_name = "Currency Rate"
        verbose_name_plural = "Currency Rates"

    def __str__(self):
        return f"{self.get_pair_display()} = {self.rate}"

    # ── Class-level helpers ────────────────────────────────────

    @classmethod
    def get_rate(cls, pair, fallback):
        """Return the DB rate for *pair*, or *fallback* if not configured yet."""
        try:
            obj = cls.objects.get(pair=pair)
            return Decimal(str(obj.rate))
        except cls.DoesNotExist:
            return Decimal(str(fallback))

    @classmethod
    def ngn_per_usd(cls):
        """Naira per dollar — falls back to the settings value."""
        return cls.get_rate(cls.PAIR_USD_NGN, settings.NGN_PER_USD)

    @classmethod
    def pi_per_usd(cls):
        """Pi per dollar — falls back to the settings value."""
        return cls.get_rate(cls.PAIR_USD_PI, settings.PI_PER_USD)


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
    STATUS_DISPUTED   = "disputed"
    STATUS_CANCELLED  = "cancelled"

    STATUS_CHOICES = [
        (STATUS_PENDING,    "Pending"),
        (STATUS_IN_TRANSIT, "In Transit"),
        (STATUS_DELIVERED,  "Delivered"),
        (STATUS_CONFIRMED,  "Confirmed"),
        (STATUS_REFUNDED,   "Refunded"),
        (STATUS_DISPUTED,   "Delivery disputed"),
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
    # Provider-side reference for the transaction that paid for this order
    # (Paystack reference, PayPal order id or Pi payment id). Empty for orders
    # created before real gateway verification existed.
    payment_reference = models.CharField(max_length=120, blank=True, default="")

    # ── Delivery address (snapshot at order time) ──────────────
    shipping_name    = models.CharField(max_length=160, blank=True, default="")
    shipping_address = models.TextField(blank=True, default="")
    tracking_number  = models.CharField(max_length=100, blank=True, default="")
    delivery_note    = models.TextField(blank=True, default="")
    dispute_reason   = models.TextField(blank=True, default="")
    disputed_at      = models.DateTimeField(null=True, blank=True)

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
        return timezone.now() >= self.delivered_at + timezone.timedelta(hours=48)

    @property
    def confirm_days_left(self):
        """How many whole days remain in the 48-hour buyer confirmation window."""
        if self.status != self.STATUS_DELIVERED or not self.delivered_at:
            return None
        seconds = (self.delivered_at + timezone.timedelta(hours=48) - timezone.now()).total_seconds()
        return max(0, int((seconds + 86399) // 86400))

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
        "disputed":   "statusx--draft",
            "cancelled":  "statusx--draft",
        }
        return mapping.get(self.status, "statusx--held")

    @property
    def payout_ready(self):
        return self.status == self.STATUS_CONFIRMED and not self.payout_released


class OrderTrackingEvent(models.Model):
    """Immutable delivery updates supplied by the seller for buyer tracking."""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="tracking_events")
    status = models.CharField(max_length=30)
    message = models.CharField(max_length=280)
    location = models.CharField(max_length=120, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class SellerPayoutMethod(models.Model):
    """A bank account or wallet the seller wants to receive payouts into."""

    METHOD_BANK   = "bank"
    METHOD_PI     = "pi"
    METHOD_PAYPAL = "paypal"

    METHOD_CHOICES = [
        (METHOD_BANK,   "Bank Transfer"),
        (METHOD_PI,     "Pi Wallet"),
        (METHOD_PAYPAL, "PayPal"),
    ]

    CURRENCY_CHOICES = [
        ("NGN", "NGN — Nigerian Naira"),
        ("USD", "USD — US Dollar"),
        ("GBP", "GBP — British Pound"),
    ]

    user        = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payout_methods")
    method      = models.CharField(max_length=10, choices=METHOD_CHOICES, default=METHOD_BANK)
    # Bank fields
    bank_name   = models.CharField(max_length=120, blank=True, default="")
    account_number = models.CharField(max_length=30, blank=True, default="")
    account_name   = models.CharField(max_length=120, blank=True, default="")
    currency    = models.CharField(max_length=5, choices=CURRENCY_CHOICES, default="NGN")
    # Pi / PayPal
    wallet_address = models.CharField(max_length=200, blank=True, default="")
    is_default  = models.BooleanField(default=False)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_default", "-created_at"]

    def __str__(self):
        if self.method == self.METHOD_BANK:
            return f"{self.bank_name} ••{self.account_number[-4:] if self.account_number else '****'}"
        return f"{self.get_method_display()} — {self.wallet_address or self.user.username}"

    @property
    def masked_account(self):
        if self.account_number and len(self.account_number) >= 4:
            return "••" + self.account_number[-4:]
        return "••••"


class SellerPayout(models.Model):
    """A payout request / release record for a seller."""

    STATUS_PENDING    = "pending"
    STATUS_PROCESSING = "processing"
    STATUS_COMPLETED  = "completed"
    STATUS_FAILED     = "failed"

    STATUS_CHOICES = [
        (STATUS_PENDING,    "Pending"),
        (STATUS_PROCESSING, "Processing"),
        (STATUS_COMPLETED,  "Completed"),
        (STATUS_FAILED,     "Failed"),
    ]

    seller         = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payouts")
    payout_method  = models.ForeignKey(SellerPayoutMethod, on_delete=models.SET_NULL, null=True, blank=True)
    amount         = models.DecimalField(max_digits=12, decimal_places=2)
    currency       = models.CharField(max_length=5, default="USD")
    status         = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_PENDING)
    reference      = models.CharField(max_length=30, unique=True, blank=True)
    note           = models.TextField(blank=True, default="")
    # The orders whose released funds make up this payout (many-to-many via the Order FK)
    created_at     = models.DateTimeField(auto_now_add=True)
    processed_at   = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.reference:
            super().save(*args, **kwargs)
            self.reference = "PO-%05d" % self.pk
            SellerPayout.objects.filter(pk=self.pk).update(reference=self.reference)
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.reference} — ${self.amount} ({self.get_status_display()})"

    @property
    def status_css(self):
        return {
            "pending":    "statusx--held",
            "processing": "statusx--ship",
            "completed":  "statusx--done",
            "failed":     "statusx--draft",
        }.get(self.status, "statusx--held")


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



class BoostPlan(models.Model):
    """A boost offer type defined by the admin (e.g. "Pro Feature", $29.99 / 7 days)."""

    name = models.CharField(max_length=60, unique=True)
    duration_days = models.PositiveIntegerField(default=7)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=200, blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["price"]

    def __str__(self):
        return "%s — $%s / %dd" % (self.name, self.price, self.duration_days)

    # Multi-currency helpers. BoostPlan.price is stored in USD.
    @property
    def price_ngn(self):
        try:
            rate = float(CurrencyRate.ngn_per_usd())
            return "\u20a6{:,.0f}".format(float(self.price) * rate)
        except (TypeError, ValueError):
            return ""

    @property
    def price_pi(self):
        try:
            rate = float(CurrencyRate.pi_per_usd())
            return "\u03c0{:,.2f}".format(float(self.price) * rate)
        except (TypeError, ValueError):
            return ""


class BoostOrder(models.Model):
    """A seller's purchase of a boost plan for one product."""

    STATUS_PENDING = "pending"
    STATUS_PAID = "paid"
    STATUS_EXPIRED = "expired"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Awaiting payment"),
        (STATUS_PAID, "Active"),
        (STATUS_EXPIRED, "Expired"),
    ]

    PAYMENT_CHOICES = [
        ("pi", "Pi Network"),
        ("paypal", "PayPal"),
        ("paystack", "Paystack"),
    ]

    CURRENCY_CHOICES = [
        ("USD", "USD — US Dollar"),
        ("NGN", "NGN — Nigerian Naira"),
        ("PI", "Pi Network"),
    ]

    # Maps a payment method to the currency the seller actually pays in.
    PAYMENT_CURRENCY = {
        "paypal":   "USD",
        "pi":       "PI",
        "paystack": "NGN",
    }

    CURRENCY_SYMBOLS = {"USD": "$", "NGN": "\u20a6", "PI": "\u03c0"}

    @classmethod
    def rates_to_usd(cls):
        """Live conversion rates: how many units of each currency equal 1 USD.

        Reads from the DB (admin-managed) and falls back to settings values.
        """
        return {
            "USD": Decimal("1"),
            "NGN": CurrencyRate.ngn_per_usd(),
            "PI":  CurrencyRate.pi_per_usd(),
        }

    # Legacy class attribute kept for backwards compatibility — prefer rates_to_usd()
    RATES_TO_USD = {"USD": Decimal("1"), "NGN": Decimal("1600"), "PI": Decimal("2")}

    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="boost_orders",
    )
    product = models.ForeignKey(
        "shop.Product",
        on_delete=models.CASCADE,
        related_name="boost_orders",
    )
    plan = models.ForeignKey(BoostPlan, on_delete=models.PROTECT, related_name="orders")

    # Snapshot so the record survives plan edits
    plan_name = models.CharField(max_length=60)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    duration_days = models.PositiveIntegerField(default=7)

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)
    payment_method = models.CharField(max_length=10, choices=PAYMENT_CHOICES, default="paypal")
    # Currency of `amount` — derived from the payment method used.
    currency = models.CharField(max_length=5, choices=CURRENCY_CHOICES, default="USD")
    reference = models.CharField(max_length=20, unique=True, blank=True)

    paid_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.reference:
            super().save(*args, **kwargs)
            self.reference = "BH-%05d" % self.pk
            BoostOrder.objects.filter(pk=self.pk).update(reference=self.reference)
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        return "%s — %s (%s)" % (self.reference, self.plan_name, self.get_status_display())

    @property
    def amount_display(self):
        """Amount formatted with the symbol of the currency it was paid in."""
        try:
            amount = float(self.amount)
        except (TypeError, ValueError):
            return ""
        symbol = self.CURRENCY_SYMBOLS.get(self.currency, "$")
        if self.currency == "NGN":
            return "{}{:,.0f}".format(symbol, amount)
        return "{}{:,.2f}".format(symbol, amount)

    @property
    def is_running(self):
        return self.status == self.STATUS_PAID and self.expires_at and self.expires_at > timezone.now()

    @property
    def days_left(self):
        if not self.is_running:
            return 0
        return max(0, (self.expires_at - timezone.now()).days)


class CartItem(models.Model):
    """A buyer's shopping-cart line."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cart_items",
    )
    product = models.ForeignKey(
        "shop.Product",
        on_delete=models.CASCADE,
        related_name="cart_items",
    )
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "product")
        ordering = ["-added_at"]

    def __str__(self):
        return "%s × %s" % (self.quantity, self.product.name)

    @property
    def line_total(self):
        try:
            return float(self.product.price) * self.quantity
        except (TypeError, ValueError):
            return 0


class PaymentIntent(models.Model):
    """One attempt to pay a cart total through a real payment provider.

    The row is created *before* the buyer is handed to Paystack / PayPal / Pi
    and is only marked ``paid`` after the provider itself confirms the money
    (Paystack ``/transaction/verify``, PayPal capture, Pi ``complete``).  Orders
    are created at that moment, so a cancelled or forged browser callback can
    never produce a protected order.
    """

    STATUS_PENDING   = "pending"         # started, waiting for the provider
    STATUS_PAID      = "paid"            # provider confirmed the money
    STATUS_FAILED    = "failed"          # provider rejected it
    STATUS_CANCELLED = "cancelled"       # buyer closed the window / went back
    STATUS_PI_PENDING = "pi_pending"     # manual Pi transfer reported, awaiting admin verification

    STATUS_CHOICES = [
        (STATUS_PENDING,    "Awaiting payment"),
        (STATUS_PAID,       "Paid"),
        (STATUS_FAILED,     "Failed"),
        (STATUS_CANCELLED,  "Cancelled"),
        (STATUS_PI_PENDING, "Pi transfer pending review"),
    ]

    PURPOSE_CHECKOUT = "checkout"
    PURPOSE_BOOST    = "boost"

    PURPOSE_CHOICES = [
        (PURPOSE_CHECKOUT, "Marketplace checkout"),
        (PURPOSE_BOOST,    "Product boost"),
    ]

    # Same three rails as an order, so the two models can never drift apart.
    METHOD_CHOICES = Order.PAYMENT_CHOICES

    user   = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payment_intents",
    )
    # Our own reference — always quoted to the buyer and sent to the provider.
    reference = models.CharField(max_length=40, unique=True)
    method    = models.CharField(max_length=10, choices=METHOD_CHOICES)
    purpose   = models.CharField(max_length=12, choices=PURPOSE_CHOICES, default=PURPOSE_CHECKOUT)

    # Cart subtotal in USD (what the orders will record) plus the fees the
    # buyer actually pays, converted into the currency of the chosen rail.
    subtotal_usd = models.DecimalField(max_digits=10, decimal_places=2)
    amount_usd   = models.DecimalField(max_digits=10, decimal_places=2)
    currency     = models.CharField(max_length=5, default="USD")
    amount       = models.DecimalField(max_digits=12, decimal_places=2)

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)
    # Paystack reference / PayPal order id / Pi payment id.
    provider_reference = models.CharField(max_length=120, blank=True, default="")
    # PKs of the orders created once the payment succeeded.
    order_pks = models.JSONField(default=list, blank=True)
    # Trimmed provider payloads, kept for reconciliation and disputes.
    provider_payload = models.JSONField(default=dict, blank=True)
    note = models.CharField(max_length=200, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at    = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return "%s — %s %s (%s)" % (
            self.reference, self.amount, self.currency, self.get_status_display()
        )

    @property
    def is_paid(self):
        return self.status == self.STATUS_PAID

    @property
    def is_pi_pending(self):
        return self.status == self.STATUS_PI_PENDING


