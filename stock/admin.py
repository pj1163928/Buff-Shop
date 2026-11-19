from django.contrib import admin

from .models import StockMovement


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    """View-only. Stock history is append-only, written by ``change_stock()`` alone."""

    list_display = ("created_at", "product", "kind", "change", "resulting_stock", "user", "reason")
    list_filter = ("kind",)
    search_fields = ("product__title", "reason", "user__email")
    list_select_related = ("product", "user")

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False
