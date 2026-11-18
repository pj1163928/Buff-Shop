from django.views.generic import ListView

from .models import Product


class ProductListView(ListView):
    """The catalog at ``/``: active products sorted by name, 12 per page.

    Products come only from ``Product.objects.active()``, the shared
    active-products helper. Out-of-stock products are listed and labelled.
    """

    template_name = "catalog/index.html"
    context_object_name = "products"
    paginate_by = 12

    def get_queryset(self):
        # "pk" breaks ties between equal titles, so pages never overlap or skip.
        return Product.objects.active().select_related("category").order_by("title", "pk")
