from django.contrib import messages
from django.core.paginator import Paginator
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import ListView, TemplateView

from catalog.models import Product
from stock.services import DuplicateSubmission, InsufficientStock, change_stock

from .access import StaffRequiredMixin
from .forms import STOCK_FORMS, ReceiveStockForm, StockAdjustmentForm


class DashboardHomeView(StaffRequiredMixin, TemplateView):
    """The staff dashboard home at ``/dashboard/``."""

    template_name = "dashboard/home.html"


class ProductListView(StaffRequiredMixin, ListView):
    """Every product for staff, active or not, sorted by name, 25 per page."""

    template_name = "dashboard/product_list.html"
    context_object_name = "products"
    paginate_by = 25

    def get_queryset(self):
        # Staff see every product, so this deliberately does not use active().
        return Product.objects.select_related("category").order_by("title", "pk")


class ProductStockView(StaffRequiredMixin, TemplateView):
    """One product's stock page: Receive Stock, Stock Adjustment and the full history.

    Both forms post here, told apart by their ``action`` field. Every change
    goes through ``change_stock()``. A success redirects back here, so
    refreshing the page never posts the form again.
    """

    template_name = "dashboard/product_stock.html"
    history_per_page = 25

    def get_product(self) -> Product:
        # Staff see every product, active or not.
        return get_object_or_404(Product.objects.select_related("category"), pk=self.kwargs["pk"])

    def get(self, request, *args, **kwargs):
        self.product = self.get_product()
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.product = self.get_product()
        form_class = STOCK_FORMS.get(request.POST.get("action", ""))
        if form_class is None:
            return HttpResponseBadRequest("Unknown stock action.")

        form = form_class(request.POST)
        if form.is_valid():
            try:
                change_stock(
                    self.product,
                    form.cleaned_data["amount"],
                    kind=form.kind,
                    user=request.user,
                    reason=form.cleaned_data["reason"],
                    submission_token=form.cleaned_data["token"],
                )
            except InsufficientStock as refused:
                form.add_error(
                    "amount",
                    f"That would take stock below zero: there are only "
                    f"{refused.available} in stock.",
                )
            except DuplicateSubmission:
                messages.info(
                    request, "That change was already recorded, so it wasn't applied again."
                )
                return redirect(request.path)
            else:
                messages.success(request, self.success_message(form))
                return redirect(request.path)

        return self.render_to_response(self.get_context_data(**{f"{form.action}_form": form}))

    def success_message(self, form) -> str:
        amount = form.cleaned_data["amount"]
        units = f"{abs(amount)} unit{'s' if abs(amount) != 1 else ''}"
        if form.action == "receive":
            done = f"Received {units}"
        else:
            done = f"Adjusted stock by {amount:+d} ({units} {'added' if amount > 0 else 'removed'})"
        return f"{done} for {self.product.title}. Stock is now {self.product.stock}."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault("receive_form", ReceiveStockForm())
        context.setdefault("adjust_form", StockAdjustmentForm())
        history = self.product.stock_movements.select_related("user")
        context["product"] = self.product
        context["history"] = Paginator(history, self.history_per_page).get_page(
            self.request.GET.get("page")
        )
        return context
