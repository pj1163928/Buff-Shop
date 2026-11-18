from django.views.generic import TemplateView


class IndexView(TemplateView):
    """Home page. A placeholder until Phase 2 replaces it with the catalog list."""

    template_name = "catalog/index.html"
