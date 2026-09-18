from django.contrib import admin

from .models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "seller", "category", "price", "stock", "status", "sold", "updated_at")
    list_filter = ("category", "status")
    search_fields = ("name", "store_name", "seller__username")
    list_editable = ("price", "stock", "status")

