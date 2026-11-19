"""A fake URL setup for testing the route walk itself (``test_walk.py``).

It has the shapes later phases might add: a nested namespace, a nested include
without a namespace, a superuser-only page, an unguarded page, an unnamed regex
route, and a stray route mounted under ``/dashboard/`` outside the namespace.
"""

from django.http import HttpResponse
from django.urls import include, path, re_path
from django.views import View

from dashboard.access import StaffRequiredMixin, SuperuserRequiredMixin


class StaffPage(StaffRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        return HttpResponse("staff page")


class OwnerPage(SuperuserRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        return HttpResponse("owner page")

    def post(self, request, *args, **kwargs):
        return HttpResponse("owner action")


class UnguardedPage(View):
    def get(self, request, *args, **kwargs):
        return HttpResponse("open to anyone")


def unguarded_function(request):
    return HttpResponse("open to anyone")


order_patterns = (
    [path("<int:pk>/", StaffPage.as_view(), name="detail")],
    "orders",
)

report_patterns = [
    path("weekly/", StaffPage.as_view(), name="weekly"),
]

dashboard_patterns = [
    path("", StaffPage.as_view(), name="home"),
    path("owner/", OwnerPage.as_view(), name="owner"),
    path("plain/", UnguardedPage.as_view(), name="plain"),
    path("orders/", include(order_patterns)),  # nested namespace: dashboard:orders:detail
    path("reports/", include(report_patterns)),  # nested, no namespace: dashboard:weekly
    re_path(r"^legacy/$", unguarded_function),  # unnamed regex route
]

urlpatterns = [
    path("", include("catalog.urls")),  # the site layout links to the shop
    path("accounts/", include("accounts.urls")),
    path("cart/", include("cart.urls")),  # the header links to the cart
    path("dashboard/", include((dashboard_patterns, "dashboard"))),
    path("dashboard-extra/", unguarded_function),  # not under dashboard/
    path("dashboard/stray/", unguarded_function, name="stray"),  # outside the namespace
]
