"""htmx is pinned, checked and served from this site, never from a CDN."""

import hashlib
import re

import pytest
from django.conf import settings
from django.urls import reverse

from accounts.tests.factories import UserFactory

HTMX_DIR = settings.BASE_DIR / "static" / "vendor" / "htmx"
HTMX_FILE = HTMX_DIR / "htmx-2.0.11.min.js"
# SHA-256 of dist/htmx.min.js from the npm tarball htmx.org-2.0.11.tgz, whose
# SHA-512 matched the registry's published "integrity" value when downloaded.
HTMX_SHA256 = "d6fdc75f204e6bdefa99b69bf1e6d4ac69b8a364f77929f45c13476b4000f717"


def test_vendored_htmx_is_the_pinned_release():
    content = HTMX_FILE.read_bytes()
    assert hashlib.sha256(content).hexdigest() == HTMX_SHA256
    assert b'version:"2.0.11"' in content


def test_htmx_licence_is_kept_beside_it():
    assert "Zero-Clause BSD" in (HTMX_DIR / "LICENSE").read_text(encoding="utf-8")


@pytest.mark.django_db
def test_every_page_loads_local_htmx_and_sends_the_csrf_token(client):
    client.force_login(UserFactory())
    html = client.get(reverse("catalog:index")).content.decode()

    scripts = re.findall(r'<script[^>]*src="([^"]+)"', html)
    assert scripts == ["/static/vendor/htmx/htmx-2.0.11.min.js"]  # local, nothing external
    assert 'integrity="sha384-' in html
    token = re.search(r"""hx-headers='\{"X-CSRFToken": "([^"]+)"\}'""", html)
    assert token and token.group(1)
