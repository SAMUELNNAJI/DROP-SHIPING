"""
Global template context processors for DropHub.

drophub_rates — injects live currency rates into every template so pages
can render correct NGN / Pi amounts without an extra DB query per view.
The rates are read once per request from CurrencyRate (DB) with a fallback
to the settings values, so nothing breaks if the table is empty.
"""

from decimal import Decimal


def drophub_rates(request):
    """Return NGN and Pi rates as plain floats for use in templates and JS."""
    try:
        from dashboards.models import CurrencyRate
        ngn = float(CurrencyRate.ngn_per_usd())
        pi  = float(CurrencyRate.pi_per_usd())
    except Exception:
        from django.conf import settings
        ngn = float(getattr(settings, 'NGN_PER_USD', Decimal('1600')))
        pi  = float(getattr(settings, 'PI_PER_USD',  Decimal('2')))

    return {
        'drophub_ngn_per_usd': ngn,
        'drophub_pi_per_usd':  pi,
    }
