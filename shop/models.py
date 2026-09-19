from django.conf import settings
from django.db import models
from django.utils.text import slugify


def _get_currency_rate():
    """Lazy import to avoid circular imports."""
    from dashboards.models import CurrencyRate
    return CurrencyRate


class Product(models.Model):
    """Marketplace product listed by a seller. Fields map 1:1 onto the shop card."""

    CATEGORY_CHOICES = [
        ("electronics", "Electronics"),
        ("fashion", "Fashion"),
        ("home", "Home & Living"),
        ("beauty", "Beauty"),
        ("sports", "Sports"),
    ]

    STATUS_CHOICES = [
        ("live", "Live"),
        ("draft", "Draft"),
    ]

    BADGE_CHOICES = [
        ("", "Auto"),
        ("NEW", "NEW"),
        ("HOT", "HOT"),
        ("BESTSELLER", "BESTSELLER"),
        ("SALE", "SALE"),
    ]

    LOW_STOCK_THRESHOLD = 5

    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="products",
    )
    name = models.CharField(max_length=160)
    store_name = models.CharField(max_length=120, default="", blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="electronics")
    price = models.DecimalField(max_digits=10, decimal_places=2)
    old_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stock = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="live")
    badge = models.CharField(max_length=12, choices=BADGE_CHOICES, default="", blank=True)
    description = models.TextField(blank=True, default="")
    image = models.ImageField(upload_to="products/", blank=True, null=True)
    image_url = models.URLField(blank=True, default="")
    rating = models.FloatField(default=5.0)
    reviews_count = models.PositiveIntegerField(default=0)
    sold = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return "%s - $%s (%s)" % (self.name, self.price, self.get_status_display())

    @property
    def category_label(self):
        return dict(self.CATEGORY_CHOICES).get(self.category, self.category.title())

    @property
    def category_slug(self):
        return self.category

    @property
    def is_low_stock(self):
        return self.status == "live" and self.stock <= self.LOW_STOCK_THRESHOLD

    @property
    def display_status(self):
        if self.status == "draft":
            return "Draft"
        if self.is_low_stock:
            return "Low stock"
        return "Live"

    @property
    def status_class(self):
        mapping = {"Live": "live", "Low stock": "low", "Draft": "draft"}
        return mapping.get(self.display_status, "live")

    @property
    def discount_pct(self):
        try:
            if self.old_price and float(self.old_price) > float(self.price) and float(self.old_price) > 0:
                return int(round((float(self.old_price) - float(self.price)) / float(self.old_price) * 100))
        except (TypeError, ValueError):
            pass
        return 0

    @property
    def badge_label(self):
        if self.discount_pct:
            return "SAVE %d%%" % self.discount_pct
        if self.badge:
            return self.badge
        return ""

    @property
    def badge_class(self):
        label = self.badge_label
        if not label:
            if self.is_low_stock:
                return "pc-badge--amber"
            return "pc-badge--green"
        if label.startswith("SAVE") or "HOT" in label:
            return "pc-badge--red"
        if "BEST" in label:
            return "pc-badge--amber"
        return "pc-badge--green"

    @property
    def card_chip(self):
        if self.is_low_stock:
            return "Low Stock"
        if self.badge == "BESTSELLER":
            return "Bestseller"
        try:
            if self.sold and int(self.sold) >= 20:
                return "Trending"
        except (TypeError, ValueError):
            pass
        if self.badge:
            return self.badge.title()
        return "New"

    @property
    def price_ngn(self):
        try:
            from dashboards.models import CurrencyRate
            rate = float(CurrencyRate.ngn_per_usd())
            return "\u20a6{:,.0f}".format(float(self.price) * rate)
        except (TypeError, ValueError):
            return ""

    @property
    def price_pi(self):
        try:
            from dashboards.models import CurrencyRate
            rate = float(CurrencyRate.pi_per_usd())
            return "\u03c0{:,.2f}".format(float(self.price) * rate)
        except (TypeError, ValueError):
            return ""

    @property
    def image_src(self):
        try:
            if self.image and getattr(self.image, "url", None):
                return self.image.url
        except (ValueError, AttributeError):
            pass
        if self.image_url:
            return self.image_url
        return "/static/img/headphones.jpg"

    @property
    def slug(self):
        """URL-friendly slug matching the wishlist heart's client-side slug."""
        return slugify(self.name) or "product"

    @property
    def initials(self):
        words = [w for w in (self.name or "").split() if w]
        if not words:
            return "PR"
        if len(words) == 1:
            return words[0][:2].upper()
        return (words[0][0] + words[1][0]).upper()

    @property
    def stars(self):
        try:
            full = int(round(float(self.rating)))
        except (TypeError, ValueError):
            full = 5
        full = max(0, min(5, full))
        return ("\u2605" * full) + ("\u2606" * (5 - full))

    @property
    def reviews_display(self):
        n = self.reviews_count or 0
        if n >= 1000:
            return "%.1fK" % (n / 1000.0)
        return str(n)

    def get_store_display(self):
        seller = getattr(self, "seller", None)
        if self.store_name:
            return self.store_name
        if seller is not None:
            return getattr(seller, "username", "Store")
        return "Store"



class BlogPost(models.Model):
    """A blog/news article created by admin staff."""

    CATEGORY_CHOICES = [
        ("playbook",     "Seller Playbooks"),
        ("pi-commerce",  "Pi Commerce"),
        ("escrow-trust", "Escrow & Trust"),
        ("news",         "Marketplace News"),
        ("case-study",   "Case Studies"),
    ]

    title        = models.CharField(max_length=220)
    slug         = models.SlugField(max_length=240, unique=True, blank=True)
    category     = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="news")
    tag_label    = models.CharField(max_length=60, blank=True, default="",
                                    help_text="Short tag shown on the card, e.g. 'PI COMMERCE'")
    excerpt      = models.TextField(blank=True, default="")
    body         = models.TextField(blank=True, default="",
                                    help_text="HTML or plain text. Displayed on the detail page.")
    image_url    = models.URLField(blank=True, default="",
                                   help_text="Unsplash/external cover image URL")
    image        = models.ImageField(upload_to="blog/", blank=True, null=True,
                                     help_text="Uploaded cover image (overrides image_url)")
    author_name  = models.CharField(max_length=120, default="DropHub Team")
    author_role  = models.CharField(max_length=160, blank=True, default="",
                                    help_text="e.g. 'Head of Seller Growth'")
    author_avatar_url = models.URLField(blank=True, default="")
    read_minutes = models.PositiveSmallIntegerField(default=5)
    likes        = models.PositiveIntegerField(default=0)
    is_featured  = models.BooleanField(default=False,
                                        help_text="Show as the spotlight featured article")
    is_published = models.BooleanField(default=True)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-published_at", "-created_at"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title) or "post"
            slug = base
            n = 1
            while BlogPost.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = "%s-%d" % (base, n)
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def cover_src(self):
        try:
            if self.image and getattr(self.image, "url", None):
                return self.image.url
        except (ValueError, AttributeError):
            pass
        return self.image_url or "https://images.unsplash.com/photo-1556742049-0cfed4f6a45d?w=900&q=80&auto=format&fit=crop"

    @property
    def published_display(self):
        from django.utils.formats import date_format
        dt = self.published_at or self.created_at
        if not dt:
            return ""
        try:
            return date_format(dt, "M j, Y")
        except Exception:
            return str(dt)[:10]

    @property
    def category_display(self):
        return dict(self.CATEGORY_CHOICES).get(self.category, self.category.title())
