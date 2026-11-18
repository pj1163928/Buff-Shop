from django.contrib import admin

from .models import Category, Product


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Categories are edited only here (no dashboard pages)."""

    list_display = ("name",)
    search_fields = ("name",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """Emergency data tool. Stock is read-only: it changes only through recorded actions."""

    list_display = ("title", "category", "price", "stock", "low_stock_threshold", "is_active")
    list_filter = ("category", "is_active")
    search_fields = ("title", "description")
    readonly_fields = ("stock",)
