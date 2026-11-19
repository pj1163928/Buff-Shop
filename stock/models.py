"""Stock history. Every row is written by ``stock.services.change_stock()``.

History is append-only: a row can never be edited or deleted, through the
model or through a bulk queryset call. A wrong count is corrected by a new
adjustment, never by rewriting the past.
"""

from django.conf import settings
from django.db import models
from django.utils import timezone

from catalog.models import Product


class ImmutableHistoryError(Exception):
    """Raised on any attempt to edit or delete a stock history row."""


class MovementKind(models.TextChoices):
    """Why stock changed. Each kind has a fixed direction (see ``change_stock``)."""

    CHECKOUT = "checkout", "Checkout"
    CANCEL = "cancel", "Cancellation"
    RECEIVE = "receive", "Received"
    ADJUST = "adjust", "Adjustment"


class StockMovementQuerySet(models.QuerySet):
    """Read-only in bulk: ``update()``, ``bulk_update()`` and ``delete()`` refuse."""

    def update(self, **kwargs):
        raise ImmutableHistoryError("Stock history can't be edited. Record a new adjustment.")

    def bulk_update(self, objs, fields, batch_size=None):
        raise ImmutableHistoryError("Stock history can't be edited. Record a new adjustment.")

    def delete(self):
        raise ImmutableHistoryError("Stock history can't be deleted.")


class StockMovement(models.Model):
    """One change to one product's stock: who, when, how much, why, and the result."""

    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="stock_movements")
    change = models.IntegerField(help_text="Units added (positive) or removed (negative).")
    resulting_stock = models.PositiveIntegerField(help_text="The product's stock after this.")
    kind = models.CharField(max_length=10, choices=MovementKind.choices)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="stock_movements"
    )
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    reason = models.CharField(max_length=200, blank=True)
    # One per form submission, so a repeated submit can't apply the change twice.
    # Empty for changes that are guarded elsewhere (checkout has its own token).
    submission_token = models.UUIDField(null=True, blank=True, editable=False)
    # Phase 6 adds a nullable link to the order for checkout and cancel rows.

    objects = StockMovementQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at", "-pk"]
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(change=0), name="stock_movement_change_not_zero"
            ),
            models.UniqueConstraint(
                fields=["submission_token"], name="stock_movement_unique_submission_token"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.product} {self.change:+d} ({self.get_kind_display()})"

    def save(self, *args, **kwargs) -> None:
        """Insert only: an existing history row is never saved again."""
        if not self._state.adding:
            raise ImmutableHistoryError("Stock history can't be edited. Record a new adjustment.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ImmutableHistoryError("Stock history can't be deleted.")
