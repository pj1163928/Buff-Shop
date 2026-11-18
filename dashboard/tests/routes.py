"""The registry of dashboard routes for the persistent access test.

The access test finds every dashboard route by itself, from Django's URL
resolver. This registry does not decide what gets tested. It is a checklist
the test enforces: a route that is missing here, unnamed, or handles methods
not listed here makes ``test_every_dashboard_route_is_walkable`` fail.

When you add a dashboard route, add one entry here:

* the key is the full URL name, e.g. ``"dashboard:product_edit"``;
* ``methods``: the HTTP methods the view handles (HEAD and OPTIONS are
  implied by Django and not listed);
* ``kwargs``: sample values for every URL argument, e.g. ``{"pk": 1}``. The
  object doesn't need to exist: the staff check runs before any lookup;
* ``superuser_only``: True when plain staff must get 403 as well.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RouteSpec:
    methods: frozenset[str]
    kwargs: dict[str, object] = field(default_factory=dict)
    superuser_only: bool = False


GET = frozenset({"GET"})
GET_POST = frozenset({"GET", "POST"})
POST = frozenset({"POST"})

DASHBOARD_ROUTES: dict[str, RouteSpec] = {
    "dashboard:home": RouteSpec(GET),
    "dashboard:product_list": RouteSpec(GET),
}
