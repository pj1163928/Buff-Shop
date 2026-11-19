from django.contrib import admin

from .models import Cart, CartLine


class CartLineInline(admin.TabularInline):
    model = CartLine
    extra = 0
    raw_id_fields = ("product",)


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    """Superuser-only emergency view of customers' carts. Carts never change stock."""

    list_display = ("user", "created_at")
    search_fields = ("user__email",)
    raw_id_fields = ("user",)
    inlines = [CartLineInline]
