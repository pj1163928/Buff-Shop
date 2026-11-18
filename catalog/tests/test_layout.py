import pytest
from django.urls import reverse

from accounts.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def test_home_page_loads_for_visitors_with_signup_and_login_links(client):
    response = client.get(reverse("catalog:index"))
    html = response.content.decode()
    assert response.status_code == 200
    assert reverse("accounts:signup") in html
    assert reverse("accounts:login") in html


def test_base_layout_has_skip_link_main_landmark_and_viewport(client):
    html = client.get(reverse("catalog:index")).content.decode()
    assert '<a href="#main"' in html and "Skip to main content" in html
    assert '<main id="main"' in html
    assert 'name="viewport" content="width=device-width, initial-scale=1"' in html
    assert '<html lang="en">' in html
    assert "css/site.css" in html


def test_logged_in_header_shows_name_and_logout_button(client):
    client.force_login(UserFactory(first_name="Pat"))
    html = client.get(reverse("catalog:index")).content.decode()
    assert "Hi, Pat" in html
    assert f'action="{reverse("accounts:logout")}"' in html
    assert reverse("accounts:signup") not in html


def test_built_stylesheet_is_present_and_contains_theme():
    from django.conf import settings

    css = (settings.BASE_DIR / "static" / "css" / "site.css").read_text()
    assert "#450012" in css.lower() or "450012" in css.lower()
    assert ":focus-visible" in css
