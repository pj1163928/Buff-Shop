from django.utils.functional import SimpleLazyObject

from .models import CartLine


def cart_item_count(request) -> dict:
    """``cart_item_count`` for the header's "Cart (N)": active units, not lines.

    Lazy, so the one aggregate query runs only if a template shows the count,
    and at most once per request. A view that has already loaded the cart
    passes its own ``cart_item_count``, which wins, so the cart page costs no
    extra query. Anonymous visitors have no cart and cost nothing.
    """
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {}
    return {
        "cart_item_count": SimpleLazyObject(lambda: CartLine.objects.for_user(user).item_count())
    }
