"""
Management command: python manage.py seed_blog_posts

Seeds the 12 static blog articles from the legacy blog.html template into
the BlogPost DB table. Safe to run multiple times — uses get_or_create on slug.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from shop.models import BlogPost


POSTS = [
    # ── Spotlight / Featured ──────────────────────────────────────────────
    {
        "title": "How 3 sellers hit $10K/month with Pi Network checkouts",
        "category": "pi-commerce",
        "tag_label": "SPOTLIGHT PLAYBOOK",
        "excerpt": "Meet the Lagos, Nairobi and Manila storefronts that dropped traditional card friction for instant Pi settlement — and watched their checkout completion rate surge by 22%.",
        "body": (
            "<p>Traditional payment gateways often impose severe high-risk holds and cross-border currency "
            "conversion fees of up to 4.5%. For independent dropshippers targeting emerging markets in "
            "Southeast Asia and Africa, this friction kills conversion rates before orders even finalize.</p>"
            "<p>By adopting DropHub's native Pi Network wallet integration alongside built-in escrow, three "
            "merchant storefronts eliminated payment decline anxiety. Orders settle in real-time, holding "
            "funds safely in buyer protection escrow until tracking confirms delivery.</p>"
            "<h3>Key Takeaways</h3>"
            "<ul>"
            "<li>Zero cross-border processing markup fees on Pi settlements</li>"
            "<li>Instant buyer trust via automated release escrow</li>"
            "<li>Average customer retention increased by 34% in Q1</li>"
            "</ul>"
        ),
        "image_url": "https://images.unsplash.com/photo-1556742049-0cfed4f6a45d?w=900&q=80&auto=format&fit=crop",
        "author_name": "Elena Rostova",
        "author_role": "Head of Seller Growth",
        "author_avatar_url": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100&q=80&auto=format&fit=crop",
        "read_minutes": 8,
        "likes": 342,
        "is_featured": True,
        "published_at": "2026-05-12T10:00:00Z",
    },
    # ── Article 1 ─────────────────────────────────────────────────────────
    {
        "title": "Pi Network wallets: the 2026 playbook for sellers",
        "category": "pi-commerce",
        "tag_label": "PI COMMERCE",
        "excerpt": "Fees, speed, and why checkout abandonment halves when you accept Pi Network natively in your online storefront.",
        "body": (
            "<p>Accepting Pi Network payments natively slashes checkout abandonment by removing the friction "
            "of traditional card declines. This playbook walks through SDK setup, escrow integration, and "
            "real-world conversion data from DropHub merchants.</p>"
            "<p>With Pi's zero-fee settlement model, sellers in high-risk regions see their effective "
            "take-home rate jump from ~94% to over 99% per transaction.</p>"
        ),
        "image_url": "https://images.unsplash.com/photo-1563013544-824ae1b704d3?w=600&q=80&auto=format&fit=crop",
        "author_name": "Marcus Vance",
        "author_role": "Pi Commerce Specialist",
        "author_avatar_url": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=80&q=80&auto=format&fit=crop",
        "read_minutes": 6,
        "likes": 142,
        "is_featured": False,
        "published_at": "2026-05-02T10:00:00Z",
    },
    # ── Article 2 ─────────────────────────────────────────────────────────
    {
        "title": "Escrow in plain English: protecting every purchase",
        "category": "escrow-trust",
        "tag_label": "ESCROW & TRUST",
        "excerpt": "The step-by-step financial path from customer payment to verified seller payout — demystified for first-time buyers.",
        "body": (
            "<p>Escrow sounds complex, but DropHub's implementation is deliberately simple: buyer pays, "
            "funds are locked, seller ships, buyer confirms, funds release. No chargebacks, no disputes, "
            "no surprises.</p>"
            "<p>This guide covers the 48-hour confirmation window, auto-confirm rules, and what happens "
            "when a delivery goes wrong.</p>"
        ),
        "image_url": "https://images.unsplash.com/photo-1450133064473-71024230f91b?w=600&q=80&auto=format&fit=crop",
        "author_name": "Sarah Jenkins",
        "author_role": "Trust & Safety Lead",
        "author_avatar_url": "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=80&q=80&auto=format&fit=crop",
        "read_minutes": 5,
        "likes": 98,
        "is_featured": False,
        "published_at": "2026-04-21T10:00:00Z",
    },
    # ── Article 3 ─────────────────────────────────────────────────────────
    {
        "title": "DropHub is now live in 26 new global markets",
        "category": "news",
        "tag_label": "NEWS",
        "excerpt": "New regional currency gateways, local fulfillment hubs across Asia & Africa, and 12-language customer support.",
        "body": (
            "<p>DropHub has officially expanded into 26 new countries, adding regional currency gateways "
            "for NGN, KES, PHP, VND, GHS and more. Local fulfillment partnerships in Lagos, Nairobi, "
            "Manila, and Jakarta mean delivery times drop from 14 days to under 5 days for most orders.</p>"
            "<p>12-language customer support is now available around the clock.</p>"
        ),
        "image_url": "https://images.unsplash.com/photo-1526304640581-d334cdbbf45e?w=600&q=80&auto=format&fit=crop",
        "author_name": "DropHub Team",
        "author_role": "Official Announcement",
        "author_avatar_url": "/static/Logo.png",
        "read_minutes": 3,
        "likes": 215,
        "is_featured": False,
        "published_at": "2026-04-08T10:00:00Z",
    },
    # ── Article 4 ─────────────────────────────────────────────────────────
    {
        "title": "What the most-loved products of Q1 have in common",
        "category": "playbook",
        "tag_label": "PLAYBOOK",
        "excerpt": "We crunched order data across 240,000 marketplace orders so you don't have to guess your next winning inventory item.",
        "body": (
            "<p>After analysing 240,000 confirmed orders in Q1 2026, three clear patterns emerge for "
            "top-selling products: strong visual thumbnails, competitive pricing within 15% of the market "
            "median, and sellers with a verified badge.</p>"
            "<p>This article breaks down each factor with actionable steps to replicate them in your store.</p>"
        ),
        "image_url": "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=600&q=80&auto=format&fit=crop",
        "author_name": "David Kim",
        "author_role": "Data & Analytics",
        "author_avatar_url": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=80&q=80&auto=format&fit=crop",
        "read_minutes": 4,
        "likes": 184,
        "is_featured": False,
        "published_at": "2026-03-14T10:00:00Z",
    },
    # ── Article 5 ─────────────────────────────────────────────────────────
    {
        "title": "Handling returns without killing your margin",
        "category": "playbook",
        "tag_label": "PLAYBOOK",
        "excerpt": "Insurance tactics, restocking rules, and the escrow playbook for painless, dispute-free cross-border refunds.",
        "body": (
            "<p>Returns are inevitable. The sellers who win treat returns as a customer retention "
            "opportunity, not a cost centre. This guide covers return insurance, restocking fee policies, "
            "and how DropHub's escrow dispute resolution keeps margins intact.</p>"
        ),
        "image_url": "https://images.unsplash.com/photo-1553729459-afe8f2e2882d?w=600&q=80&auto=format&fit=crop",
        "author_name": "Amara Okafor",
        "author_role": "Seller Success Manager",
        "author_avatar_url": "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=80&q=80&auto=format&fit=crop",
        "read_minutes": 9,
        "likes": 76,
        "is_featured": False,
        "published_at": "2026-02-28T10:00:00Z",
    },
    # ── Article 6 ─────────────────────────────────────────────────────────
    {
        "title": "Scaling TikTok Shop & DropHub: the dual funnel strategy",
        "category": "case-study",
        "tag_label": "CASE STUDY",
        "excerpt": "How organic social proof on short-form video drives high-intent traffic straight into zero-fee escrow storefronts.",
        "body": (
            "<p>Combining TikTok's viral discovery engine with DropHub's escrow checkout creates a "
            "powerful dual funnel. Viewers convert at 3.2× higher rates when landing directly on a "
            "DropHub product page from a TikTok link compared to a generic landing page.</p>"
        ),
        "image_url": "https://images.unsplash.com/photo-1611162617213-7d7a39e9b1d7?w=600&q=80&auto=format&fit=crop",
        "author_name": "Lucas Rivera",
        "author_role": "Growth Marketing",
        "author_avatar_url": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=80&q=80&auto=format&fit=crop",
        "read_minutes": 7,
        "likes": 310,
        "is_featured": False,
        "published_at": "2026-02-15T10:00:00Z",
    },
    # ── Article 7 ─────────────────────────────────────────────────────────
    {
        "title": "Negotiating supplier MOQs like a top 1% dropshipper",
        "category": "playbook",
        "tag_label": "PLAYBOOK",
        "excerpt": "Scripts, negotiation frameworks, and leverage tactics to cut minimum order quantities by 70% with overseas factories.",
        "body": (
            "<p>Most dropshippers accept supplier MOQs at face value. The top 1% negotiate. This guide "
            "provides word-for-word scripts for email negotiations, Alibaba chat tactics, and how to "
            "leverage competitor quotes to cut MOQs by up to 70%.</p>"
        ),
        "image_url": "https://images.unsplash.com/photo-1586528116311-ad8dd3c8310d?w=600&q=80&auto=format&fit=crop",
        "author_name": "Elena Rostova",
        "author_role": "Head of Seller Growth",
        "author_avatar_url": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=80&q=80&auto=format&fit=crop",
        "read_minutes": 6,
        "likes": 129,
        "is_featured": False,
        "published_at": "2026-01-29T10:00:00Z",
    },
    # ── Article 8 ─────────────────────────────────────────────────────────
    {
        "title": "Cryptocurrency in e-commerce: why 2026 is the tipping point",
        "category": "pi-commerce",
        "tag_label": "PI COMMERCE",
        "excerpt": "An in-depth analysis of borderless micro-transactions and how Web3 settlement is dramatically lowering merchant barrier to entry.",
        "body": (
            "<p>2026 marks the year crypto checkout crossed the mainstream threshold. Pi Network's "
            "accessibility-first design brought 50M+ users to the table, while DropHub's escrow layer "
            "removed the trust barrier that had kept merchants on the sidelines.</p>"
        ),
        "image_url": "https://images.unsplash.com/photo-1621416894569-0f39ed31d247?w=600&q=80&auto=format&fit=crop",
        "author_name": "Marcus Vance",
        "author_role": "Pi Commerce Specialist",
        "author_avatar_url": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=80&q=80&auto=format&fit=crop",
        "read_minutes": 8,
        "likes": 195,
        "is_featured": False,
        "published_at": "2026-01-12T10:00:00Z",
    },
    # ── Article 9 ─────────────────────────────────────────────────────────
    {
        "title": "Building a sustainable brand beyond generic dropshipping",
        "category": "case-study",
        "tag_label": "CASE STUDY",
        "excerpt": "Custom packaging, memorable unboxing experiences, and building customer loyalty that turns one-time shoppers into repeat fans.",
        "body": (
            "<p>Generic dropshipping is a race to the bottom. The merchants thriving in 2026 invest in "
            "custom packaging inserts, branded thank-you cards, and post-purchase email flows that turn "
            "a $29 transaction into a $240 lifetime customer value.</p>"
        ),
        "image_url": "https://images.unsplash.com/photo-1441986300917-64674bd600d8?w=600&q=80&auto=format&fit=crop",
        "author_name": "Sarah Jenkins",
        "author_role": "Trust & Safety Lead",
        "author_avatar_url": "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=80&q=80&auto=format&fit=crop",
        "read_minutes": 10,
        "likes": 240,
        "is_featured": False,
        "published_at": "2026-01-03T10:00:00Z",
    },
    # ── Article 10 ────────────────────────────────────────────────────────
    {
        "title": "Zero dispute resolution: automated buyer protection",
        "category": "escrow-trust",
        "tag_label": "ESCROW & TRUST",
        "excerpt": "How automated carrier tracking releases escrow funds seamlessly without manual seller intervention or buyer friction.",
        "body": (
            "<p>DropHub's automated escrow release engine monitors carrier tracking events in real-time. "
            "When a delivery is confirmed, funds release within 2 hours — no seller action required. "
            "Disputed orders trigger a structured mediation flow that resolves 97% of cases without "
            "involving support staff.</p>"
        ),
        "image_url": "https://images.unsplash.com/photo-1554224155-8d04cb21cd6c?w=600&q=80&auto=format&fit=crop",
        "author_name": "Amara Okafor",
        "author_role": "Seller Success Manager",
        "author_avatar_url": "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=80&q=80&auto=format&fit=crop",
        "read_minutes": 5,
        "likes": 167,
        "is_featured": False,
        "published_at": "2025-12-18T10:00:00Z",
    },
    # ── Article 11 ────────────────────────────────────────────────────────
    {
        "title": "Pi payment checkout SDK: 5-minute integration guide",
        "category": "pi-commerce",
        "tag_label": "PI COMMERCE",
        "excerpt": "Step-by-step developer tutorial for embedding DropHub's Pi payment gateway into custom WooCommerce & Shopify stores.",
        "body": (
            "<p>Integrating DropHub's Pi checkout SDK takes under 5 minutes. Add the script tag, "
            "initialise with your seller API key, and the checkout button handles everything else — "
            "wallet verification, escrow lock, and delivery release hooks included.</p>"
        ),
        "image_url": "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=600&q=80&auto=format&fit=crop",
        "author_name": "Marcus Vance",
        "author_role": "Pi Commerce Specialist",
        "author_avatar_url": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=80&q=80&auto=format&fit=crop",
        "read_minutes": 4,
        "likes": 289,
        "is_featured": False,
        "published_at": "2025-12-04T10:00:00Z",
    },
    # ── Article 12 ────────────────────────────────────────────────────────
    {
        "title": "Mastering cross-border logistics & customs clearance",
        "category": "playbook",
        "tag_label": "PLAYBOOK",
        "excerpt": "How top merchants handle duties, tax IDs (IOSS/VAT), and 5-day express shipping routes from hubs in Manila and Lagos.",
        "body": (
            "<p>Cross-border logistics is where most new dropshippers stumble. IOSS registration for EU "
            "shipments, HS code classification, and choosing the right last-mile carrier for each "
            "destination country are all covered in this comprehensive playbook.</p>"
        ),
        "image_url": "https://images.unsplash.com/photo-1578575437130-527eed3abbec?w=600&q=80&auto=format&fit=crop",
        "author_name": "Elena Rostova",
        "author_role": "Head of Seller Growth",
        "author_avatar_url": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=80&q=80&auto=format&fit=crop",
        "read_minutes": 8,
        "likes": 156,
        "is_featured": False,
        "published_at": "2025-11-22T10:00:00Z",
    },
]


class Command(BaseCommand):
    help = "Seed the 12 static blog posts from blog.html into the BlogPost DB table."

    def handle(self, *args, **options):
        created = 0
        updated = 0
        for data in POSTS:
            pub = data.pop("published_at", None)
            if pub:
                pub = parse_datetime(pub)
                if pub and timezone.is_naive(pub):
                    pub = timezone.make_aware(pub)
            obj, was_created = BlogPost.objects.get_or_create(
                title=data["title"],
                defaults={**data, "published_at": pub},
            )
            if was_created:
                created += 1
            else:
                # update fields so re-runs keep data fresh
                for k, v in data.items():
                    setattr(obj, k, v)
                obj.published_at = pub
                obj.save()
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Blog seed complete: {created} created, {updated} updated."
            )
        )
