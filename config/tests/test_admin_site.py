"""Django's built-in admin is for the superuser only (user story 43)."""

from urllib.parse import urlparse

import pytest
from django.contrib import admin
from django.urls import reverse

from accounts.models import User
from accounts.tests.factories import DEFAULT_PASSWORD, StaffFactory, SuperuserFactory, UserFactory
from catalog.models import Category, Product
from config.admin import SuperuserAdminSite

pytestmark = pytest.mark.django_db

ADMIN_PAGES = [
    "admin:index",
    "admin:accounts_user_changelist",
    "admin:catalog_category_changelist",
    "admin:catalog_product_changelist",
    "admin:catalog_category_add",
]


def make_user(role):
    if role == "customer":
        return UserFactory(is_staff=False, is_superuser=False)
    return StaffFactory(is_superuser=False)


def sent_to_admin_login(response) -> bool:
    return response.status_code == 302 and urlparse(response["Location"]).path == reverse(
        "admin:login"
    )


def test_the_default_admin_site_is_superuser_only_and_keeps_its_registrations():
    assert isinstance(admin.site, SuperuserAdminSite)
    for model in (User, Category, Product):
        assert admin.site.is_registered(model)


@pytest.mark.parametrize("page", ADMIN_PAGES)
def test_anonymous_visitors_are_sent_to_the_admin_login(client, page):
    assert sent_to_admin_login(client.get(reverse(page)))


@pytest.mark.parametrize("role", ["customer", "staff"])
@pytest.mark.parametrize("page", ADMIN_PAGES)
def test_customers_and_plain_staff_are_refused_every_admin_page(client, role, page):
    client.force_login(make_user(role))
    assert sent_to_admin_login(client.get(reverse(page)))


@pytest.mark.parametrize("role", ["customer", "staff"])
def test_customers_and_plain_staff_cannot_change_data_through_admin(client, role):
    client.force_login(make_user(role))
    response = client.post(reverse("admin:catalog_category_add"), {"name": "Snuck In"})
    assert sent_to_admin_login(response)
    assert not Category.objects.filter(name="Snuck In").exists()


def test_logged_in_plain_staff_are_told_they_are_not_authorised(client):
    client.force_login(StaffFactory(is_superuser=False))
    response = client.get(reverse("admin:index"), follow=True)
    assert "not authorized to access this page" in response.content.decode()


@pytest.mark.parametrize("role", ["customer", "staff"])
def test_admin_login_form_refuses_non_superusers(client, role):
    user = make_user(role)
    response = client.post(
        reverse("admin:login"), {"username": user.email, "password": DEFAULT_PASSWORD}
    )
    assert response.status_code == 200
    assert "password for a superuser account" in response.content.decode()
    assert "_auth_user_id" not in client.session


def test_superuser_can_log_in_to_admin_and_use_it(client):
    user = SuperuserFactory()
    response = client.post(
        reverse("admin:login"),
        {"username": user.email, "password": DEFAULT_PASSWORD, "next": reverse("admin:index")},
    )
    assert response.status_code == 302
    for page in ADMIN_PAGES:
        assert client.get(reverse(page)).status_code == 200
    response = client.post(reverse("admin:catalog_category_add"), {"name": "Stationery"})
    assert response.status_code == 302
    assert Category.objects.filter(name="Stationery").exists()
