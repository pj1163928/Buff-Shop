"""Every staff page lives here, under ``/dashboard/``.

Each new route must also be registered in ``dashboard/tests/routes.py``, or the
access test fails.
"""

from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.DashboardHomeView.as_view(), name="home"),
    path("products/", views.ProductListView.as_view(), name="product_list"),
]
