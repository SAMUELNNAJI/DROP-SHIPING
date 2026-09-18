from django.contrib import admin
from .models import SellerVerification


@admin.register(SellerVerification)
class SellerVerificationAdmin(admin.ModelAdmin):
    list_display = ("store_name", "user", "status", "id_type", "submitted_at")
    list_filter = ("status", "id_type")
    search_fields = ("store_name", "full_name", "user__username", "id_number")
