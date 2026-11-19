"""Cart forms. The server checks every quantity, whatever the browser sends."""

from django import forms

from .models import MAX_LINE_QUANTITY

WHOLE_NUMBER = "Enter a whole number for the quantity."
TOO_LARGE = f"Enter a quantity of at most {MAX_LINE_QUANTITY:,}."


class AddToCartForm(forms.Form):
    """Add to cart: at least 1. The catalog button sends 1."""

    quantity = forms.IntegerField(
        min_value=1,
        max_value=MAX_LINE_QUANTITY,
        error_messages={
            "required": "Enter a quantity of at least 1.",
            "invalid": WHOLE_NUMBER,
            "min_value": "Enter a quantity of at least 1.",
            "max_value": TOO_LARGE,
        },
    )


class LineQuantityForm(forms.Form):
    """Change a cart line. 0 removes it; a negative number is refused, never read as remove."""

    quantity = forms.IntegerField(
        min_value=0,
        max_value=MAX_LINE_QUANTITY,
        error_messages={
            "required": "Enter a quantity, or 0 to remove the item.",
            "invalid": WHOLE_NUMBER,
            "min_value": "Enter a quantity of 0 or more. Use 0 or Remove to take an item out.",
            "max_value": TOO_LARGE,
        },
    )
