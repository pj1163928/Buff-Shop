import pytest
from django.urls import reverse

from accounts.models import User
from accounts.tests.factories import UserFactory

pytestmark = pytest.mark.django_db

SIGNUP = reverse("accounts:signup")
GOOD = {
    "first_name": "Pat",
    "last_name": "Buff",
    "email": "pat@wtamu.edu",
    "password1": "Canyon-Sunset-1910",
    "password2": "Canyon-Sunset-1910",
}


def test_signup_page_shows_labelled_fields(client):
    response = client.get(SIGNUP)
    assert response.status_code == 200
    html = response.content.decode()
    for field_id, label in [
        ("id_first_name", "First name"),
        ("id_last_name", "Last name"),
        ("id_email", "Email address"),
        ("id_password1", "Password"),
        ("id_password2", "Password confirmation"),
    ]:
        assert f'for="{field_id}"' in html
        assert label in html


def test_signup_creates_customer_and_logs_them_in(client):
    response = client.post(SIGNUP, GOOD, follow=True)
    user = User.objects.get(email="pat@wtamu.edu")
    assert user.first_name == "Pat" and user.last_name == "Buff"
    assert not user.is_staff and not user.is_superuser
    assert response.context["user"] == user
    assert response.redirect_chain[-1][0] == reverse("catalog:index")
    assert "Welcome to the Buff Shop, Pat!" in response.content.decode()
    # A fresh sign-up is not "remembered": the session ends at browser close.
    assert client.session.get_expire_at_browser_close()


@pytest.mark.parametrize("missing", ["first_name", "last_name", "email", "password1", "password2"])
def test_signup_requires_all_fields(client, missing):
    data = {**GOOD, missing: ""}
    response = client.post(SIGNUP, data)
    assert response.status_code == 200
    assert not User.objects.exists()
    assert "This field is required." in response.content.decode()


@pytest.mark.parametrize(
    ("password", "message"),
    [
        ("Ab3-xy", "This password is too short. It must contain at least 8 characters."),
        ("password123", "This password is too common."),
        ("4839201756", "This password is entirely numeric."),
        ("patbuffwtamu", "The password is too similar to the"),
    ],
    ids=["too-short", "too-common", "all-numeric", "too-similar"],
)
def test_signup_applies_the_four_password_validators(client, password, message):
    data = {**GOOD, "password1": password, "password2": password}
    response = client.post(SIGNUP, data)
    assert not User.objects.exists()
    assert message in response.content.decode()


def test_signup_password_mismatch(client):
    response = client.post(SIGNUP, {**GOOD, "password2": "Something-Else-77"})
    assert not User.objects.exists()
    assert "The two password fields didn’t match." in response.content.decode()


def test_errors_are_linked_to_their_field(client):
    response = client.post(SIGNUP, {**GOOD, "email": ""})
    html = response.content.decode()
    assert 'id="id_email_error"' in html
    assert 'aria-invalid="true"' in html
    assert 'aria-describedby="id_email_error"' in html


def test_signup_stores_email_lowercased(client):
    client.post(SIGNUP, {**GOOD, "email": "  Pat@WTAMU.edu "})
    assert User.objects.get().email == "pat@wtamu.edu"


def test_case_variant_email_cannot_create_second_account(client):
    client.post(SIGNUP, {**GOOD, "email": "Pat@WTAMU.edu"})
    client.logout()
    response = client.post(SIGNUP, {**GOOD, "email": "pat@wtamu.edu", "first_name": "Other"})
    assert User.objects.count() == 1
    assert "An account with this email already exists." in response.content.decode()


def test_logged_in_user_is_sent_home_from_signup(client):
    client.force_login(UserFactory())
    response = client.get(SIGNUP)
    assert response.status_code == 302
    assert response.url == reverse("catalog:index")
