"""Production settings. Every secret comes from an environment variable.

Required: DJANGO_SECRET_KEY, DJANGO_ALLOWED_HOSTS (comma-separated).
Optional: DJANGO_CSRF_TRUSTED_ORIGINS, DJANGO_SQLITE_PATH, DJANGO_EMAIL_HOST,
DJANGO_EMAIL_PORT, DJANGO_EMAIL_HOST_USER, DJANGO_EMAIL_HOST_PASSWORD,
DJANGO_DEFAULT_FROM_EMAIL.
"""

import os

from .base import *  # noqa: F403
from .base import DATABASES


def _env_list(name: str) -> list[str]:
    """Split a comma-separated environment variable into a list, skipping blanks."""
    return [item.strip() for item in os.environ.get(name, "").split(",") if item.strip()]


DEBUG = False

# Raises KeyError at startup if missing: production must never run on a default key.
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
ALLOWED_HOSTS = _env_list("DJANGO_ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = _env_list("DJANGO_CSRF_TRUSTED_ORIGINS")

if os.environ.get("DJANGO_SQLITE_PATH"):
    DATABASES["default"]["NAME"] = os.environ["DJANGO_SQLITE_PATH"]

# HTTPS everywhere.
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 365
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Django 6.1 configures email through MAILERS (EMAIL_BACKEND is deprecated).
MAILERS = {
    "default": {
        "BACKEND": "django.core.mail.backends.smtp.EmailBackend",
        "OPTIONS": {
            "host": os.environ.get("DJANGO_EMAIL_HOST", "localhost"),
            "port": int(os.environ.get("DJANGO_EMAIL_PORT", "587")),
            "username": os.environ.get("DJANGO_EMAIL_HOST_USER", ""),
            "password": os.environ.get("DJANGO_EMAIL_HOST_PASSWORD", ""),
            "use_tls": True,
        },
    }
}
DEFAULT_FROM_EMAIL = os.environ.get("DJANGO_DEFAULT_FROM_EMAIL", "Buff Shop <noreply@localhost>")
