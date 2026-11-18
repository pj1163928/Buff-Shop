"""The route walk behind the persistent dashboard access test.

``discover_dashboard_routes()`` finds every dashboard route from Django's URL
resolver, following nested ``include()`` files to any depth. A route counts as
a dashboard route when it is inside the ``dashboard`` namespace or its path
starts with ``dashboard/``, so a stray route mounted from another URL file is
found too.

``plan_walk()`` turns the routes into URLs to request:

* a registered route is built from its sample kwargs in ``routes.py``;
* a route that needs no arguments is requested by its path directly, even if
  it is unregistered, so a forgotten guard fails the access tests as well as
  the registry check;
* a route that can't be built is returned as a failure, never skipped.
"""

from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

from django.http import HttpResponse
from django.test import Client
from django.urls import NoReverseMatch, Resolver404, URLResolver, get_resolver, resolve, reverse
from django.views import View

from dashboard.access import StaffRequiredMixin, SuperuserRequiredMixin

from .routes import DASHBOARD_ROUTES, RouteSpec

# GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS, TRACE
ALL_METHODS = [method.upper() for method in View.http_method_names]


@dataclass(frozen=True)
class DiscoveredRoute:
    name: str | None  # full URL name, e.g. "dashboard:home"; None if unnamed
    path: str  # the route's path when it has no arguments, e.g. "/dashboard/products/"
    has_params: bool  # whether the URL needs arguments (anywhere in its include chain)
    callback: Callable

    @property
    def label(self) -> str:
        return self.name or self.path


@dataclass(frozen=True)
class WalkTarget:
    label: str  # the route's name, or its path if unnamed
    url: str
    spec: RouteSpec | None  # None when the route isn't registered


def _segment(pattern) -> str:
    """One pattern's piece of the path, without regex anchors."""
    return str(pattern).removeprefix("^").removesuffix("$")


def discover_dashboard_routes() -> list[DiscoveredRoute]:
    """Every URL pattern in the dashboard namespace or under ``/dashboard/``."""
    found: list[DiscoveredRoute] = []

    def walk(patterns, prefix: str, namespaces: list[str], params: bool) -> None:
        for entry in patterns:
            path = prefix + _segment(entry.pattern)
            has_params = params or entry.pattern.regex.groups > 0
            if isinstance(entry, URLResolver):
                inner = [*namespaces, entry.namespace] if entry.namespace else namespaces
                walk(entry.url_patterns, path, inner, has_params)
            elif namespaces[:1] == ["dashboard"] or path.startswith("dashboard/"):
                name = ":".join([*namespaces, entry.name]) if entry.name else None
                found.append(DiscoveredRoute(name, "/" + path, has_params, entry.callback))

    walk(get_resolver().url_patterns, "", [], False)
    return found


def _resolves_to(url: str, route: DiscoveredRoute) -> bool:
    try:
        return resolve(url).func is route.callback
    except Resolver404:
        return False


def plan_walk(
    registry: dict[str, RouteSpec] = DASHBOARD_ROUTES,
) -> tuple[list[WalkTarget], list[str]]:
    """The URLs to request, and the routes that couldn't be built (as failure messages)."""
    targets: list[WalkTarget] = []
    unbuildable: list[str] = []
    for route in discover_dashboard_routes():
        spec = registry.get(route.name) if route.name else None
        url = None
        if spec is not None:
            try:
                url = reverse(route.name, kwargs=spec.kwargs)
            except NoReverseMatch:
                url = None
        if url is None and not route.has_params:
            url = route.path
        if url is None or not _resolves_to(url, route):
            unbuildable.append(
                f"{route.label}: couldn't be checked; register working sample kwargs "
                "in dashboard/tests/routes.py"
            )
            continue
        targets.append(WalkTarget(route.label, url, spec))
    return targets, unbuildable


def handled_methods(view_class: type[View]) -> frozenset[str]:
    """The HTTP methods a class-based view defines a handler for.

    HEAD and OPTIONS are left out: Django provides them for every view.
    """
    return frozenset(
        method.upper()
        for method in view_class.http_method_names
        if method not in ("head", "options") and hasattr(view_class, method)
    )


def find_walk_problems(registry: dict[str, RouteSpec] = DASHBOARD_ROUTES) -> list[str]:
    """Every rule a discovered dashboard route breaks, in words.

    Each route must be named, class-based, guarded by ``StaffRequiredMixin``,
    and registered with sample kwargs that build its URL, its exact methods,
    and the right ``superuser_only``. Stale registry entries are reported too.
    """
    problems = []
    discovered = discover_dashboard_routes()
    for route in discovered:
        if route.name is None:
            problems.append(f"{route.path}: has no URL name; name it in the dashboard namespace")
            continue
        view_class = getattr(route.callback, "view_class", None)
        if view_class is None:
            problems.append(f"{route.name}: is not a class-based view")
            continue
        if not issubclass(view_class, StaffRequiredMixin):
            problems.append(f"{route.name}: does not use StaffRequiredMixin")
        spec = registry.get(route.name)
        if spec is None:
            problems.append(f"{route.name}: is not registered in dashboard/tests/routes.py")
            continue
        try:
            reverse(route.name, kwargs=spec.kwargs)
        except NoReverseMatch:
            problems.append(f"{route.name}: its registered kwargs {spec.kwargs} can't build a URL")
        if handled_methods(view_class) != spec.methods:
            problems.append(
                f"{route.name}: handles {sorted(handled_methods(view_class))} "
                f"but is registered with {sorted(spec.methods)}"
            )
        if issubclass(view_class, SuperuserRequiredMixin) != spec.superuser_only:
            problems.append(f"{route.name}: superuser_only doesn't match its access mixin")

    discovered_names = {route.name for route in discovered}
    for name in sorted(registry.keys() - discovered_names):
        problems.append(f"{name}: is registered but no such dashboard route exists")
    return problems


def is_login_redirect(response: HttpResponse, url: str) -> bool:
    """Whether ``response`` sends the visitor to log in, coming back to ``url``."""
    if response.status_code != 302:
        return False
    location = urlparse(response["Location"])
    return location.path == reverse("accounts:login") and parse_qs(location.query).get("next") == [
        url
    ]


def anonymous_failures(client: Client, targets: list[WalkTarget]) -> list[str]:
    """Each request (every method) that did not send an anonymous visitor to log in."""
    failures = []
    for target in targets:
        for method in ALL_METHODS:
            response = client.generic(method, target.url)
            if not is_login_redirect(response, target.url):
                failures.append(
                    f"{method} {target.url} ({target.label}) gave {response.status_code}"
                )
    return failures


def forbidden_failures(client: Client, targets: list[WalkTarget]) -> list[str]:
    """Each request (every method) that did not get exactly 403."""
    failures = []
    for target in targets:
        for method in ALL_METHODS:
            response = client.generic(method, target.url)
            if response.status_code != 403:
                failures.append(
                    f"{method} {target.url} ({target.label}) gave {response.status_code}"
                )
    return failures


def admitted_failures(client: Client, targets: list[WalkTarget]) -> list[str]:
    """Each registered method (plus HEAD and OPTIONS) that refused the logged-in user."""
    failures = []
    for target in targets:
        methods = set(target.spec.methods) | {"OPTIONS"}
        if "GET" in methods:
            methods.add("HEAD")
        for method in sorted(methods):
            response = client.generic(method, target.url)
            if response.status_code == 403 or is_login_redirect(response, target.url):
                failures.append(f"{method} {target.url} ({target.label}) refused the user")
    return failures
