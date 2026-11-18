from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from .images import product_image_path, validate_product_image


class StockStatus(models.TextChoices):
    """What a customer is told about stock. Always shown as these words."""

    IN_STOCK = "in_stock", "In Stock"
    LOW_STOCK = "low_stock", "Low Stock — act soon"
    OUT_OF_STOCK = "out_of_stock", "Out of Stock"


def stock_status(stock: int, threshold: int) -> StockStatus:
    """Return the stock status for ``stock`` units against a low-stock ``threshold``.

    The one rule behind the customer label, the staff badge, the alert count
    and the analytics low-stock list: 0 is Out of Stock, at or below the
    threshold is Low Stock, above it is In Stock.

    The result carries a stable identifier (``.value``, e.g. ``"low_stock"``)
    for styling and queries, and the customer wording (``.label``).
    """
    if stock <= 0:
        return StockStatus.OUT_OF_STOCK
    if stock <= threshold:
        return StockStatus.LOW_STOCK
    return StockStatus.IN_STOCK


class Category(models.Model):
    """A product category (Textbook, Merchandise, Lab Kit). Edited only in /admin/."""

    name = models.CharField(max_length=60, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def __str__(self) -> str:
        return self.name


class ProductQuerySet(models.QuerySet):
    """Product queries. ``active()`` is the shared active-products helper."""

    def active(self) -> "ProductQuerySet":
        """Products customers may see: active ones only, in or out of stock.

        Every customer-facing product query (catalog, search, cart) starts here.
        """
        return self.filter(is_active=True)


class Product(models.Model):
    """Something the shop sells. Sizes are separate products; never hard-deleted."""

    title = models.CharField(max_length=200)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    description = models.TextField(blank=True)
    price = models.DecimalField(
        max_digits=8, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))]
    )
    image = models.ImageField(
        upload_to=product_image_path,
        blank=True,
        validators=[validate_product_image],
        help_text="Optional. A JPEG, PNG or WebP image up to 5 MB.",
    )
    alt_text = models.CharField(
        max_length=200, blank=True, help_text="Describes the image. Defaults to the title."
    )
    # Changed only through the stock helper (Phase 4); read-only everywhere else.
    stock = models.IntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(
        default=5, help_text="Show “Low Stock” at or below this many units."
    )
    is_active = models.BooleanField(
        "active", default=True, help_text="Inactive products are hidden from customers."
    )

    objects = ProductQuerySet.as_manager()

    class Meta:
        ordering = ["title", "pk"]
        constraints = [
            # Second safeguard behind the stock helper: the database itself
            # refuses a negative stock, however it was written.
            models.CheckConstraint(
                condition=models.Q(stock__gte=0), name="catalog_product_stock_gte_0"
            ),
        ]

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs) -> None:
        """Default the alt text to the title, so every image has a text alternative."""
        if not self.alt_text.strip():
            self.alt_text = self.title
        super().save(*args, **kwargs)

    @property
    def stock_status(self) -> StockStatus:
        """This product's stock status, from its stock and its own threshold."""
        return stock_status(self.stock, self.low_stock_threshold)
