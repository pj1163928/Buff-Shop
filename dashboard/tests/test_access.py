"""The persistent dashboard access test.

Every dashboard route is discovered from Django's URL resolver (see
``walk.py``), so routes added in later phases are checked without anyone
remembering to. Every route is requested with every HTTP method Django knows,
because protecting a page's GET says nothing about its other methods.

When you add a dashboard route, register it in ``routes.py``.
"""

import pytest

from accounts.tests.factories import StaffFactory, SuperuserFactory, UserFactory

from .walk import (
    admitted_failures,
    anonymous_failures,
    discover_dashboard_routes,
    find_walk_problems,
    forbidden_failures,
    plan_walk,
)

pytestmark = pytest.mark.django_db


# --- TDD: the three access rules ------------------------------------------------


def test_dashboard_routes_redirect_anonymous_to_login(client):
    targets, unbuildable = plan_walk()
    assert targets, "the walk found no dashboard routes, so it would check nothing"

    failures = unbuildable + anonymous_failures(client, targets)

    assert failures == [], "anonymous requests were not sent to log in"


def test_dashboard_routes_forbid_customers(client):
    customer = UserFactory(is_staff=False, is_superuser=False)
    assert not customer.is_staff and not customer.is_superuser  # a plain customer, explicitly
    client.force_login(customer)
    targets, unbuildable = plan_walk()
    assert targets, "the walk found no dashboard routes, so it would check nothing"

    failures = unbuildable + forbidden_failures(client, targets)

    assert failures == [], "logged-in customers were not refused with 403"


def test_every_dashboard_route_is_walkable():
    assert discover_dashboard_routes(), "the walk found no dashboard routes"
    assert find_walk_problems() == [], "fix these dashboard routes (see routes.py)"


# --- Roles that are let in, and superuser-only routes ---------------------------


def test_superuser_only_routes_forbid_plain_staff(client):
    client.force_login(StaffFactory(is_superuser=False))
    targets, _ = plan_walk()
    superuser_only = [t for t in targets if t.spec and t.spec.superuser_only]
    assert forbidden_failures(client, superuser_only) == []


def test_staff_are_let_in_on_every_staff_route(client):
    client.force_login(StaffFactory(is_superuser=False))
    targets, _ = plan_walk()
    staff_routes = [t for t in targets if t.spec and not t.spec.superuser_only]
    assert staff_routes
    assert admitted_failures(client, staff_routes) == []


def test_superuser_is_let_in_on_every_route(client):
    client.force_login(SuperuserFactory())
    targets, _ = plan_walk()
    assert admitted_failures(client, [t for t in targets if t.spec]) == []
