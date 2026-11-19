"""The per-user database cart.

A cart only ever records what a customer intends to buy. **It never changes
product stock** and reserves nothing: adding, updating and removing touch cart
lines only. Stock is deducted at checkout, through ``change_stock()``.

Quantities are capped at the product's current stock whenever they are written,
so a customer can't build a line the shop couldn't fill at that moment.
"""

from dataclasses import dataclass
from decimal import Decimal

from django.conf import settings
from django.db import models, transaction
from django.db.models import F, Sum

from catalog.models import Product

# The largest value a PositiveIntegerField holds on every database Django supports.
MAX_LINE_QUANTITY = 2_147_483_647


class ProductUnavailable(Exception):
    """The product is inactive (discontinued), so it can't be put in a cart."""


class LineNotInCart(Exception):
    """The cart has no line for that product, so there is nothing to update."""


@dataclass(frozen=True)
class CartUpdate:
    """What ``Cart.add()`` or ``Cart.set_quantity()`` did to one line.

    * ``quantity``: what the line holds now; 0 means the product isn't in the cart.
    * ``capped``: the quantity asked for was more than the stock, so it was lowered.
    * ``removed``: the product isn't in the cart after this call (asked for 0, or
      capped to 0 because it is out of stock).
    * ``available``: the product's stock when the line was written.
    """

    product: Product
    quantity: int
    capped: bool
    removed: bool
    available: int


def _check_quantity(quantity: int, *, minimum: int) -> None:
    """Refuse anything but a whole number from ``minimum`` to ``MAX_LINE_QUANTITY``."""
    if isinstance(quantity, bool) or not isinstance(quantity, int):
        raise ValueError("A quantity must be a whole number.")
    if not minimum <= quantity <= MAX_LINE_QUANTITY:
        raise ValueError(f"A quantity must be from {minimum} to {MAX_LINE_QUANTITY}.")


def _available_stock(product: Product) -> int:
    """The product's stock, read fresh from the database through the active-products helper.

    Call it inside the transaction that writes the line: in IMMEDIATE mode that
    transaction holds SQLite's write lock, so stock can't change in between.
    Raises ``ProductUnavailable`` if the product is inactive.
    """
    stock = Product.objects.active().filter(pk=product.pk).values_list("stock", flat=True).first()
    if stock is None:
        raise ProductUnavailable(product.pk)
    return stock


class CartManager(models.Manager):
    def for_user(self, user) -> "Cart":
        """The user's cart, created on first use. Safe if two requests create it at once."""
        cart, _ = self.get_or_create(user=user)
        return cart


class Cart(models.Model):
    """One cart per user, stored in the database so it follows them across devices."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cart"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    objects = CartManager()

    def __str__(self) -> str:
        return f"Cart for {self.user}"

    def add(self, product: Product, quantity: int = 1) -> CartUpdate:
        """Add ``quantity`` (at least 1) of an active ``product``, capped at its stock.

        The line ends at ``min(current + quantity, stock)``; if the product is
        out of stock, any line for it is removed. Never changes stock.

        Safe when requests race: the stock read and the writes share one
        transaction (which holds SQLite's write lock in IMMEDIATE mode); a
        second request creating the same line at once falls back to updating
        it (the database keeps one line per cart and product); and the line is
        changed by conditional UPDATEs on its current database value, never on
        a quantity loaded earlier.

        Raises ``ProductUnavailable`` for an inactive product and ``ValueError``
        for a quantity that isn't a whole number from 1 to ``MAX_LINE_QUANTITY``.
        """
        _check_quantity(quantity, minimum=1)
        with transaction.atomic():
            available = _available_stock(product)
            lines = CartLine.objects.filter(cart=self, product=product)
            if available == 0:
                lines.delete()
                return CartUpdate(product, 0, capped=True, removed=True, available=0)

            line, created = CartLine.objects.get_or_create(
                cart=self, product=product, defaults={"quantity": min(quantity, available)}
            )
            if created:
                capped = quantity > available
            else:
                # Add only while the result stays within stock; otherwise fill to stock.
                # SQL: SET quantity = quantity + n WHERE quantity <= stock - n
                capped = not lines.filter(quantity__lte=available - quantity).update(
                    quantity=F("quantity") + quantity
                )
                if capped:
                    lines.update(quantity=available)
            new_quantity = lines.values_list("quantity", flat=True).get()
        return CartUpdate(product, new_quantity, capped=capped, removed=False, available=available)

    def set_quantity(self, product: Product, quantity: int) -> CartUpdate:
        """Set the line for ``product`` to ``quantity``, capped at its stock; 0 removes it.

        If the cap brings it to 0 (out of stock), the line is removed. Never
        changes stock. The stock read and the write share one transaction.

        Raises ``ValueError`` for a quantity that isn't a whole number from 0
        to ``MAX_LINE_QUANTITY`` (a negative number is refused, never read as
        "remove"), ``ProductUnavailable`` for an inactive product, and
        ``LineNotInCart`` if there is no line to set. Removing a line that is
        already gone succeeds, so a double-clicked Remove is harmless.
        """
        _check_quantity(quantity, minimum=0)
        with transaction.atomic():
            available = _available_stock(product)
            lines = CartLine.objects.filter(cart=self, product=product)
            if quantity == 0:
                lines.delete()
                return CartUpdate(product, 0, capped=False, removed=True, available=available)
            if not lines.exists():
                raise LineNotInCart(product.pk)
            capped = quantity > available
            quantity = min(quantity, available)
            if quantity == 0:  # out of stock: a line is never kept at 0
                lines.delete()
                return CartUpdate(product, 0, capped=True, removed=True, available=available)
            lines.update(quantity=quantity)
        return CartUpdate(product, quantity, capped=capped, removed=False, available=available)


class CartLineQuerySet(models.QuerySet):
    """Cart line queries. ``contents()`` and ``item_count()`` are what customers see.

    Both always apply ``active()``, so a discontinued product is never shown,
    totalled or counted (the cart page, its htmx updates and the header count
    all go through them). Its line is kept, not deleted, so it comes back if
    staff reactivate the product.
    """

    def for_user(self, user) -> "CartLineQuerySet":
        return self.filter(cart__user=user)

    def active(self) -> "CartLineQuerySet":
        """Lines whose product passes the shared active-products helper."""
        return self.filter(product__in=Product.objects.active())

    def contents(self) -> "CartContents":
        """The active lines, sorted by product name, with their totals."""
        lines = (
            self.active()
            .select_related("product__category")
            .order_by("product__title", "product__pk")
        )
        return CartContents(list(lines))

    def item_count(self) -> int:
        """Total active units (2 hoodies + 3 kits = 5), in one query."""
        return self.active().aggregate(units=Sum("quantity"))["units"] or 0


class CartLine(models.Model):
    """One product in a cart, with how many the customer wants."""

    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="lines")
    # A cart isn't history, so a line goes if its product is ever deleted.
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="cart_lines")
    quantity = models.PositiveIntegerField()

    objects = CartLineQuerySet.as_manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["cart", "product"], name="cart_cartline_unique_product"
            ),
            # A line with nothing in it is deleted, never kept at 0.
            models.CheckConstraint(
                condition=models.Q(quantity__gte=1), name="cart_cartline_quantity_gte_1"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.quantity} × {self.product}"

    @property
    def line_total(self) -> Decimal:
        """Quantity times the product's current price (prices are fixed at checkout)."""
        return self.product.price * self.quantity

    @property
    def over_stock(self) -> bool:
        """Stock fell below this quantity after it was set (it's capped when next written)."""
        return self.quantity > self.product.stock


@dataclass(frozen=True)
class CartContents:
    """The lines a customer sees, and their totals."""

    lines: list[CartLine]

    @property
    def total(self) -> Decimal:
        return sum((line.line_total for line in self.lines), Decimal("0.00"))

    @property
    def item_count(self) -> int:
        return sum(line.quantity for line in self.lines)
