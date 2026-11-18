"""Development and demo settings (localhost only). The default for manage.py."""

from .base import *  # noqa: F403
from .base import BASE_DIR, INSTALLED_APPS

DEBUG = True

# Development-only key. Production reads DJANGO_SECRET_KEY from the environment.
SECRET_KEY = "django-insecure-dev-only-buff-shop-key-do-not-use-in-production"

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]"]

# Emails (password reset, "Ready for Pick Up") print to the terminal.
# Django 6.1 configures email through MAILERS (EMAIL_BACKEND is deprecated).
MAILERS = {"default": {"BACKEND": "django.core.mail.backends.console.EmailBackend"}}
DEFAULT_FROM_EMAIL = "Buff Shop <noreply@buffshop.localhost>"

# Tailwind standalone CLI, driven by django-tailwind-cli (a dev-only dependency).
# Build: uv run python manage.py tailwind build
# The built static/css/site.css is committed, so production needs no build step.
INSTALLED_APPS = [*INSTALLED_APPS, "django_tailwind_cli"]
TAILWIND_CLI_VERSION = "4.3.5"
TAILWIND_CLI_SRC_CSS = BASE_DIR / "tailwind" / "source.css"
TAILWIND_CLI_DIST_CSS = "css/site.css"
