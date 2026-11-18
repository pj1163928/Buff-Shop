"""Tests of the route walk itself, against the fake URLs in ``walk_fixture_urls.py``.

If the walk stopped following nested URL files, skipped routes it couldn't
build, or missed an unguarded page, the real access test could pass while
checking too little. These tests make sure it can't.
"""

import pytest

from accounts.tests.factories import StaffFactory, SuperuserFactory

from .routes import GET, GET_POST, RouteSpec
from .walk import (
    admitted_failures,
    anonymous_failures,
    discover_dashboard_routes,
    find_walk_problems,
    forbidden_failures,
    plan_walk,
)

pytestmark = [pytest.mark.django_db, pytest.mark.urls("dashboard.tests.walk_fixture_urls")]


def test_discovery_follows_nested_url_files():
    found = {route.label: route for route in discover_dashboard_routes()}
    assert set(found) == {
        "dashboard:home",
        "dashboard:owner",
        "dashboard:plain",
        "dashboard:orders:detail",
        "dashboard:weekly",
        "/dashboard/legacy/",
        "stray",
    }
    assert found["dashboard:orders:detail"].has_params
    assert found["dashboard:weekly"].path == "/dashboard/reports/weekly/"


def test_unregistered_routes_without_arguments_are_still_requested():
    targets, unbuildable = plan_walk(registry={})
    assert {t.url for t in targets} == {
        "/dashboard/",
        "/dashboard/owner/",
        "/dashboard/plain/",
        "/dashboard/reports/weekly/",
        "/dashboard/legacy/",
        "/dashboard/stray/",
    }
    # The one route that needs an argument is reported, never silently skipped.
    assert unbuildable == [
        "dashboard:orders:detail: couldn't be checked; register working sample kwargs "
        "in dashboard/tests/routes.py"
    ]


def test_registered_kwargs_build_routes_with_arguments():
    targets, unbuildable = plan_walk(
        registry={"dashboard:orders:detail": RouteSpec(GET, {"pk": 7})}
    )
    assert "/dashboard/orders/7/" in {t.url for t in targets}
    assert unbuildable == []


def test_the_access_walk_catches_unguarded_routes(client):
    targets, _ = plan_walk(registry={})
    failed_urls = {line.split()[1] for line in anonymous_failures(client, targets)}
    assert failed_urls == {"/dashboard/plain/", "/dashboard/legacy/", "/dashboard/stray/"}


def test_superuser_only_routes_refuse_plain_staff_but_admit_the_superuser(client):
    registry = {"dashboard:owner": RouteSpec(GET_POST, superuser_only=True)}
    owner_only = [t for t in plan_walk(registry)[0] if t.spec]

    client.force_login(StaffFactory(is_superuser=False))
    assert forbidden_failures(client, owner_only) == []

    client.force_login(SuperuserFactory())
    assert admitted_failures(client, owner_only) == []


def test_find_walk_problems_names_every_broken_rule():
    registry = {
        "dashboard:home": RouteSpec(GET),  # correct
        "dashboard:owner": RouteSpec(GET),  # wrong methods, and not marked superuser_only
        "dashboard:plain": RouteSpec(GET),  # no staff check
        "dashboard:orders:detail": RouteSpec(GET, {"slug": "x"}),  # kwargs can't build it
        "dashboard:gone": RouteSpec(GET),  # stale
    }
    assert sorted(find_walk_problems(registry)) == sorted(
        [
            "dashboard:owner: handles ['GET', 'POST'] but is registered with ['GET']",
            "dashboard:owner: superuser_only doesn't match its access mixin",
            "dashboard:plain: does not use StaffRequiredMixin",
            "dashboard:orders:detail: its registered kwargs {'slug': 'x'} can't build a URL",
            "dashboard:weekly: is not registered in dashboard/tests/routes.py",
            "/dashboard/legacy/: has no URL name; name it in the dashboard namespace",
            "stray: is not a class-based view",
            "dashboard:gone: is registered but no such dashboard route exists",
        ]
    )
