import pytest
from django.urls import reverse

from accounts.models import User
from accounts.tests.factories import SuperuserFactory, UserFactory

pytestmark = pytest.mark.django_db


def test_admin_add_user_normalises_email_and_blocks_case_duplicate(client):
    client.force_login(SuperuserFactory())
    url = reverse("admin:accounts_user_add")
    data = {
        "email": "New.Staff@WTAMU.edu",
        "first_name": "New",
        "last_name": "Staff",
        "usable_password": "true",
        "password1": "Canyon-Sunset-1910",
        "password2": "Canyon-Sunset-1910",
    }
    response = client.post(url, data)
    assert response.status_code == 302, response.context["adminform"].form.errors
    assert User.objects.filter(email="new.staff@wtamu.edu").exists()

    response = client.post(url, {**data, "email": "new.staff@wtamu.EDU"})
    assert response.status_code == 200
    assert User.objects.filter(email__iexact="new.staff@wtamu.edu").count() == 1


def test_admin_user_list_and_change_pages_load(client):
    client.force_login(SuperuserFactory())
    customer = UserFactory()
    assert client.get(reverse("admin:accounts_user_changelist")).status_code == 200
    change = reverse("admin:accounts_user_change", args=[customer.pk])
    assert client.get(change).status_code == 200
