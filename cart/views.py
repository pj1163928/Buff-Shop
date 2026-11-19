"""The cart pages. Logged-in users only: anonymous visitors are sent to log in.

Every product lookup goes through ``Product.objects.active()``, so a
discontinued product can't be added, updated or shown.
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic import TemplateView

from catalog.models import Product

from .forms import AddToCartForm, LineQuantityForm
from .models import Cart, CartLine, CartUpdate, LineNotInCart, ProductUnavailable


def _units(n: int) -> str:
    return f"{n} {'is' if n == 1 else 'are'}"


def update_message(update: CartUpdate) -> str:
    """Tell the customer, in words, what happened to one line."""
    title = update.product.title
    if update.removed and update.capped:
        return f"{title} is out of stock, so it isn't in your cart."
    if update.removed:
        return f"Removed {title} from your cart."
    if update.capped:
        return (
            f"Only {_units(update.available)} in stock, so {title} "
            f"was set to {update.quantity}, the most you can order."
        )
    return f"{title}: quantity is now {update.quantity}."


def cart_context(user) -> dict:
    """What the cart page and its htmx partial render."""
    contents = CartLine.objects.for_user(user).contents()
    # Overrides the context processor's lazy count, so the header costs no extra query.
    return {"cart": contents, "cart_item_count": contents.item_count}


class CartView(LoginRequiredMixin, TemplateView):
    """The cart page at ``/cart/``: active lines only, with line and cart totals."""

    template_name = "cart/detail.html"

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), **cart_context(self.request.user)}


class AddToCartView(LoginRequiredMixin, View):
    """POST only. Adds an active product to the cart, then returns to the page it came from."""

    http_method_names = ["post"]

    def post(self, request, product_id: int):
        product = get_object_or_404(Product.objects.active(), pk=product_id)
        form = AddToCartForm(request.POST)
        if not form.is_valid():
            messages.error(request, form.errors["quantity"][0])
            return redirect(self.next_url())
        try:
            update = Cart.objects.for_user(request.user).add(product, form.cleaned_data["quantity"])
        except ProductUnavailable as unavailable:  # discontinued since the lookup above
            raise Http404 from unavailable

        if update.removed:
            messages.warning(request, update_message(update))
        elif update.capped:
            messages.warning(
                request,
                f"Only {_units(update.available)} in stock, and your cart already has "
                f"{update.quantity} {product.title}, the most you can order.",
            )
        else:
            messages.success(
                request, f"Added {product.title} to your cart. You have {update.quantity}."
            )
        return redirect(self.next_url())

    def next_url(self) -> str:
        """Back to the catalog page the button was on, if that's a safe local URL."""
        next_url = self.request.POST.get("next", "")
        if url_has_allowed_host_and_scheme(
            next_url,
            allowed_hosts={self.request.get_host()},
            require_https=self.request.is_secure(),
        ):
            return next_url
        return reverse("catalog:index")


class CartLineView(LoginRequiredMixin, View):
    """POST only. Sets one line's quantity (0 removes it).

    With htmx it returns the updated cart and, out of band, the message and
    totals for the live region and the header count. Without JavaScript it is a
    normal form post that redirects back to the cart with a message.
    """

    http_method_names = ["post"]

    def post(self, request, product_id: int):
        product = get_object_or_404(Product.objects.active(), pk=product_id)
        form = LineQuantityForm(request.POST)
        if form.is_valid():
            try:
                update = Cart.objects.for_user(request.user).set_quantity(
                    product, form.cleaned_data["quantity"]
                )
            except (LineNotInCart, ProductUnavailable) as missing:
                raise Http404 from missing
            message = update_message(update)
            level = messages.WARNING if update.capped else messages.SUCCESS
        else:
            message = form.errors["quantity"][0]
            level = messages.ERROR

        if request.headers.get("HX-Request") == "true":
            context = {
                **cart_context(request.user),
                "status": message,
                "status_tag": messages.DEFAULT_TAGS[level],
            }
            return TemplateResponse(request, "cart/_update.html", context)
        messages.add_message(request, level, message)
        return redirect("cart:detail")
