"""Forms for the staff dashboard."""

import uuid

from django import forms

from stock.models import MovementKind
from stock.services import MAX_REASON_LENGTH, MAX_STOCK_CHANGE


class StockChangeForm(forms.Form):
    """Shared by Receive Stock and Stock Adjustment.

    Every form carries a one-time submission token, so posting it twice (a
    double click, or the browser resending it) applies the change only once.
    The page holds both forms, so each has its own prefix and ``action``.
    """

    action: str
    kind: MovementKind

    token = forms.UUIDField(widget=forms.HiddenInput, required=False)

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("prefix", self.action)
        super().__init__(*args, **kwargs)
        if not self.is_bound:
            self.initial["token"] = uuid.uuid4()

    def clean(self):
        cleaned = super().clean()
        # The token is hidden, so a problem with it is reported for the whole form.
        if not cleaned.get("token"):
            self.add_error(None, "This form is out of date. Reload the page and try again.")
        return cleaned


class ReceiveStockForm(StockChangeForm):
    """Receive Stock: a positive amount, with an optional note."""

    action = "receive"
    kind = MovementKind.RECEIVE

    amount = forms.IntegerField(
        label="Amount received",
        min_value=1,
        max_value=MAX_STOCK_CHANGE,
        help_text=f"Units delivered: a whole number from 1 to {MAX_STOCK_CHANGE:,}.",
        error_messages={
            "min_value": "Enter an amount of at least 1.",
            "max_value": f"Enter an amount of at most {MAX_STOCK_CHANGE:,}.",
        },
    )
    reason = forms.CharField(
        label="Note",
        required=False,
        max_length=MAX_REASON_LENGTH,
        help_text="Optional, such as a delivery or invoice reference.",
    )


class StockAdjustmentForm(StockChangeForm):
    """Stock Adjustment: a positive or negative amount, with a required reason."""

    action = "adjust"
    kind = MovementKind.ADJUST

    amount = forms.IntegerField(
        label="Change in stock",
        min_value=-MAX_STOCK_CHANGE,
        max_value=MAX_STOCK_CHANGE,
        help_text="Add units with a positive number. Remove units with a minus sign, e.g. -2.",
        error_messages={
            "min_value": f"Remove at most {MAX_STOCK_CHANGE:,} units at a time.",
            "max_value": f"Add at most {MAX_STOCK_CHANGE:,} units at a time.",
        },
    )
    reason = forms.CharField(
        label="Reason",
        max_length=MAX_REASON_LENGTH,
        help_text="Why the count changed, e.g. “2 damaged in storage” or “Recount”.",
        error_messages={"required": "Enter a reason for the adjustment."},
    )

    def clean_amount(self) -> int:
        amount = self.cleaned_data["amount"]
        if amount == 0:
            raise forms.ValidationError("Enter a change other than 0.")
        return amount


STOCK_FORMS: dict[str, type[StockChangeForm]] = {
    form.action: form for form in (ReceiveStockForm, StockAdjustmentForm)
}
