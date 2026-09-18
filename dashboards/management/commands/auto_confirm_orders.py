"""
Management command: auto_confirm_orders
=======================================
Finds all orders with status=delivered where delivered_at is older than 48 hours
and the buyer has not manually confirmed, then marks them as confirmed.

Usage:
    python manage.py auto_confirm_orders

Schedule this with a cron job or a task scheduler (e.g. every hour):
    # crontab -e
    0 * * * * /path/to/venv/bin/python /path/to/manage.py auto_confirm_orders

On Render.com or similar PaaS, add a cron job in the dashboard pointing to this command.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from dashboards.models import Order


class Command(BaseCommand):
    help = "Auto-confirm delivered orders older than 48 hours where buyer has not confirmed."

    def handle(self, *args, **options):
        cutoff = timezone.now() - timezone.timedelta(hours=48)
        qs = Order.objects.filter(
            status=Order.STATUS_DELIVERED,
            delivered_at__lte=cutoff,
            confirmed_at__isnull=True,
        )
        count = qs.count()
        if count == 0:
            self.stdout.write("No orders to auto-confirm.")
            return

        qs.update(
            status=Order.STATUS_CONFIRMED,
            confirmed_at=timezone.now(),
            auto_confirmed=True,
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Auto-confirmed {count} order{'s' if count != 1 else ''}."
            )
        )
