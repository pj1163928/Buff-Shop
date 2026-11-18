import pytest
from django.conf import settings
from django.urls import reverse

from accounts.tests.factories import DEFAULT_PASSWORD, UserFactory

pytestmark = pytest.mark.django_db

LOGIN = reverse("accounts:login")
LOGOUT = reverse("accounts:logout")
GENERIC_ERROR = "The email or password is incorrect. Please try again."


def _login(client, email, password=DEFAULT_PASSWORD, remember=False):
    data = {"username": email, "password": password}
    if remember:
        data["remember_me"] = "on"
    return client.post(LOGIN, data)


def test_login_page_has_email_password_and_remember_me(client):
    html = client.get(LOGIN).content.decode()
    assert 'type="email"' in html and 'for="id_username"' in html
    assert 'for="id_password"' in html
    assert "Remember me for two weeks" in html


def test_login_with_email_succeeds(client):
    user = UserFactory(email="pat@wtamu.edu")
    response = _login(client, "pat@wtamu.edu")
    assert response.status_code == 302
    assert response.url == reverse("catalog:index")
    assert int(client.session["_auth_user_id"]) == user.pk


def test_login_email_is_case_insensitive(client):
    UserFactory(email="pat@wtamu.edu")
    response = _login(client, "  PAT@Wtamu.EDU ")
    assert response.status_code == 302
    assert "_auth_user_id" in client.session


def test_failed_login_error_is_identical_for_unknown_email_and_wrong_password(client):
    UserFactory(email="pat@wtamu.edu")
    wrong_password = _login(client, "pat@wtamu.edu", "not-the-password")
    unknown_email = _login(client, "nobody@wtamu.edu", "not-the-password")
    for response in (wrong_password, unknown_email):
        assert response.status_code == 200
        assert GENERIC_ERROR in response.content.decode()
    assert wrong_password.context["form"].errors == unknown_email.context["form"].errors
    assert "_auth_user_id" not in client.session


def test_inactive_user_gets_the_same_generic_error(client):
    UserFactory(email="gone@wtamu.edu", is_active=False)
    response = _login(client, "gone@wtamu.edu")
    assert GENERIC_ERROR in response.content.decode()
    assert "_auth_user_id" not in client.session


def test_without_remember_me_session_ends_at_browser_close(client):
    UserFactory(email="pat@wtamu.edu")
    response = _login(client, "pat@wtamu.edu")
    assert client.session.get_expire_at_browser_close()
    cookie = response.cookies[settings.SESSION_COOKIE_NAME]
    assert cookie["max-age"] == "" and cookie["expires"] == ""


def test_with_remember_me_session_lasts_two_weeks(client):
    UserFactory(email="pat@wtamu.edu")
    response = _login(client, "pat@wtamu.edu", remember=True)
    two_weeks = 14 * 24 * 60 * 60
    assert not client.session.get_expire_at_browser_close()
    assert client.session.get_expiry_age() == two_weeks
    assert int(response.cookies[settings.SESSION_COOKIE_NAME]["max-age"]) == two_weeks


def test_logged_in_user_is_sent_home_from_login(client):
    client.force_login(UserFactory())
    response = client.get(LOGIN)
    assert response.status_code == 302


def test_login_honours_safe_next(client):
    UserFactory(email="pat@wtamu.edu")
    response = client.post(
        LOGIN + "?next=/admin/", {"username": "pat@wtamu.edu", "password": DEFAULT_PASSWORD}
    )
    assert response.url == "/admin/"


def test_logout_requires_post_and_logs_out(client):
    client.force_login(UserFactory())
    assert client.get(LOGOUT).status_code == 405
    response = client.post(LOGOUT, follow=True)
    assert "_auth_user_id" not in client.session
    assert "You have been logged out." in response.content.decode()
