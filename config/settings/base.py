"""Settings shared by every environment.

Environment-specific values live in ``dev.py`` and ``prod.py``, which import
everything from here.
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

INSTALLED_APPS = [
    # Django admin, superuser only (config/admin.py).
    "config.apps.SuperuserAdminConfig",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Project apps
    "accounts",
    "catalog",
    "stock",
    "dashboard",
    "demo",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# --- Database -----------------------------------------------------------------
# SQLite is the target database everywhere (dev, demo and production settings).
#
# transaction_mode="IMMEDIATE" (Django 5.1+) makes every transaction take
# SQLite's write lock as soon as it starts, so concurrent writers queue up
# instead of failing part-way through with "database is locked".
# timeout=20 is the busy timeout: a writer waits up to 20 seconds for the lock.
#
# Because every transaction holds the write lock for its whole length:
#   * keep transaction.atomic() blocks short;
#   * never make network calls or send email inside one (use
#     transaction.on_commit() to send after the commit);
#   * ATOMIC_REQUESTS stays False, so a whole request is never one transaction.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
        "ATOMIC_REQUESTS": False,
        "OPTIONS": {
            "transaction_mode": "IMMEDIATE",
            "timeout": 20,
        },
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Accounts -----------------------------------------------------------------
AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "catalog:index"
LOGOUT_REDIRECT_URL = "catalog:index"

# "Remember me" keeps the session for SESSION_COOKIE_AGE (two weeks). Without it,
# the login view makes the session end when the browser closes.
SESSION_COOKIE_AGE = 60 * 60 * 24 * 14
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

# --- Internationalisation -----------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "America/Chicago"
USE_I18N = True
USE_TZ = True

# --- Static files -------------------------------------------------------------
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# --- Uploaded files (product images) ------------------------------------------
# Kept apart from the committed static assets: media/ is gitignored and holds
# only files uploaded through the app. Dev serves it from config/urls.py.
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# --- Demo data ----------------------------------------------------------------
# seed_demo refuses to run unless this is True. Only dev.py turns it on, so the
# command can never touch a production database (independent of DEBUG).
ALLOW_DEMO_SEED = False
