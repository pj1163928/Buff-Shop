"""The one safe stock helper. Every stock change in the app goes through ``change_stock()``.

Two independent safeguards keep stock at zero or above, and each holds on its own:

1. the helper's single conditional UPDATE, which the database applies only if
   the result stays at zero or above (it never relies on ``select_for_update()``,
   which SQLite ignores);
2. the ``catalog_product_stock_gte_0`` CHECK constraint on the product table.
"""

import uuid

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from accounts.models import User
from catalog.models import Product

from .models import MovementKind, StockMovement

# The most units one change may add or remove. Catches typos such as an extra
# zero, and keeps absurd numbers away from the database.
MAX_STOCK_CHANGE = 10_000
MAX_REASON_LENGTH = 200

# The direction each kind of change must go in. Adjustments may go either way.
_MUST_ADD = {MovementKind.RECEIVE, MovementKind.CANCEL}
_MUST_REMOVE = {MovementKind.CHECKOUT}


class InsufficientStock(Exception):
    """The change would take stock below zero, so nothing was changed.

    ``available`` is the product's stock at the moment the change was refused.
    """

    def __init__(self, product: Product, change: int, available: int):
        self.product = product
        self.change = change
        self.available = available
        super().__init__(f"Can't change {product} by {change:+d}: only {available} in stock.")


class DuplicateSubmission(Exception):
    """This form submission was already recorded, so nothing was changed again."""


def _check_request(change: int, kind: MovementKind, reason: str) -> None:
    """Refuse a change the caller should never have asked for (a programming error)."""
    if isinstance(change, bool) or not isinstance(change, int):
        raise ValueError("The stock change must be a whole number.")
    if change == 0:
        raise ValueError("A stock change of 0 changes nothing.")
    if abs(change) > MAX_STOCK_CHANGE:
        raise ValueError(f"A stock change can't be more than {MAX_STOCK_CHANGE:,} units.")
    if kind not in MovementKind.values:
        raise ValueError(f"Unknown kind of stock change: {kind!r}.")
    if kind in _MUST_ADD and change < 0:
        raise ValueError(f"A {kind} must add stock.")
    if kind in _MUST_REMOVE and change > 0:
        raise ValueError(f"A {kind} must remove stock.")
    if kind == MovementKind.ADJUST and not reason:
        raise ValueError("A stock adjustment needs a reason.")
    if len(reason) > MAX_REASON_LENGTH:
        raise ValueError(f"The reason can't be longer than {MAX_REASON_LENGTH} characters.")


def change_stock(
    product: Product,
    change: int,
    *,
    kind: MovementKind,
    user: User,
    reason: str = "",
    submission_token: uuid.UUID | None = None,
) -> StockMovement:
    """Change ``product``'s stock by ``change`` units and record exactly one history row.

    The stock update and its history row are one transaction: both happen or
    neither does. Stock never changes without a history row.

    Args:
        product: the product to change. Its ``stock`` attribute is refreshed
            on success.
        change: units to add (positive) or remove (negative); never 0, and at
            most ``MAX_STOCK_CHANGE`` either way.
        kind: receive and cancel must add, checkout must remove, adjust may
            go either way.
        user: who made the change (staff, or the customer for checkout/cancel).
        reason: required for an adjustment, optional otherwise.
        submission_token: a one-time token from the form that asked for the
            change. A token that was already used is refused.

    Returns:
        The new ``StockMovement``.

    Raises:
        InsufficientStock: the change would take stock below zero. Nothing changed.
        DuplicateSubmission: ``submission_token`` was already used. Nothing changed.
        ValueError: the request breaks one of the rules above. Nothing changed.
    """
    reason = reason.strip()
    _check_request(change, kind, reason)

    with transaction.atomic():
        # IMMEDIATE mode: this transaction holds SQLite's write lock from here
        # to the end, so no other writer can act between these statements.
        if (
            submission_token is not None
            and StockMovement.objects.filter(submission_token=submission_token).exists()
        ):
            raise DuplicateSubmission("This change was already recorded.")

        # One conditional UPDATE, checked by the database itself:
        # WHERE id = ? AND stock >= -change, i.e. stock + change >= 0.
        updated = Product.objects.filter(pk=product.pk, stock__gte=-change).update(
            stock=F("stock") + change
        )
        if updated != 1:
            available = Product.objects.values_list("stock", flat=True).get(pk=product.pk)
            raise InsufficientStock(product, change, available)

        resulting = Product.objects.values_list("stock", flat=True).get(pk=product.pk)
        # If this insert fails, the exception leaves the atomic block and the
        # stock UPDATE above is rolled back with it.
        movement = StockMovement.objects.create(
            product=product,
            change=change,
            resulting_stock=resulting,
            kind=kind,
            user=user,
            created_at=timezone.now(),
            reason=reason,
            submission_token=submission_token,
        )
    product.stock = resulting
    return movement
