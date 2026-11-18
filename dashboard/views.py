from django.views.generic import ListView, TemplateView

from catalog.models import Product

from .access import StaffRequiredMixin


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
