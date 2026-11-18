# Architecture

Read when creating apps, models, settings or URLs, or deciding where code belongs. Full detail: [PRD › Implementation Decisions](../prd/buff-shop.md#implementation-decisions).

## Stack
- Django + SQLite, htmx, Pillow, `qrcode`, `django-axes`.
- Tooling: pytest-django, factory_boy, pytest-cov, ruff.
- Tailwind via the standalone CLI binary (no Node.js). See [frontend.md](frontend.md).

## Apps (planned split)
| App | Owns |
|---|---|
| accounts | Custom user (email login), sign-up/login, profile, password reset, lockout, disable/enable + audit log |
| catalog | Category, Product, shared active-products helper, search, image processing |
| stock | The one safe stock-change helper, stock history log |
| cart | Per-user DB cart |
| orders | Order, OrderLine (name/price snapshot), order numbers, transition table, cancel, override, pickup code, QR, ready email |
| dashboard | Every staff view, behind one staff-only access check |

## Roles
- `is_staff` = shop staff ("Admin" in the brief) → `/dashboard/`.
- `is_superuser` only: status override, managing staff, Django `/admin/`. Plain staff are blocked from `/admin/`.
- Categories are edited only in `/admin/`.

## Data rules
- Create the custom user model **before the first migration**.
- Products are soft-deleted (`is_active`); no hard delete from the dashboard.
- Each product has its own `low_stock_threshold` (default 5).
- Order number format: `BUF-<year>-<5-digit seq>`.

## Layout
- `config/settings/{base,dev,prod}.py`, `config/urls.py` (includes each app's namespaced URLs).
- Apps: `accounts/`, `catalog/` (more are added by later phases). Tests live in `<app>/tests/`.
- Project templates in `templates/` (`base.html`, `includes/`, `icons/`, one folder per app). Tailwind source in `tailwind/source.css`.

## URLs so far
| Name | Path |
|---|---|
| `catalog:index` | `/` (placeholder home until Phase 2) |
| `accounts:signup` / `accounts:login` / `accounts:logout` (POST only) | `/accounts/signup/`, `/accounts/login/`, `/accounts/logout/` |
| admin | `/admin/` |

## Accounts
- `accounts.User` (`AbstractUser` with `username = None`). `USERNAME_FIELD = "email"`, first and last name required.
- **Emails are always stored lowercased and trimmed** by `accounts.models.normalize_email()`. It is used by the manager (`create_user`, `get_by_natural_key`, so login and `createsuperuser` too), `User.clean()` (sign-up and admin forms) and `User.save()` (every other path). The database also has a `Lower("email")` unique constraint.
- Sign-up logs the new customer in, with a browser-close session. Login sets `set_expiry(0)` without "Remember me" and `SESSION_COOKIE_AGE` (two weeks) with it.
- If you call `login()` yourself, pass `backend=` explicitly, because axes adds a second backend in Phase 11.

## Settings
- Base (all environments): SQLite with `OPTIONS = {"transaction_mode": "IMMEDIATE", "timeout": 20}` and `ATOMIC_REQUESTS = False`.
- **Transaction rules (IMMEDIATE takes the write lock at the start of every transaction):**
  - keep `transaction.atomic()` blocks short
  - never make network calls or send email inside one; use `transaction.on_commit()`
  - never turn on `ATOMIC_REQUESTS`
- Dev: console email via `MAILERS` (Django 6.1 deprecates `EMAIL_BACKEND`), insecure dev key, localhost hosts.
- Prod: secrets from env vars (`DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, …, listed in the `prod.py` docstring), SSL redirect, secure cookies, HSTS, SMTP via `MAILERS`. `manage.py check --deploy` passes, and a test enforces it.
- Demo runs on localhost only.

## Research findings (Phase 1, checked in installed source, Nov 2026)
- Django 6.1.3: SQLite `OPTIONS["transaction_mode"]` accepts DEFERRED/IMMEDIATE/EXCLUSIVE (added in Django 5.1).
- Django 6.1 deprecates `EMAIL_BACKEND` and the `EMAIL_*` settings in favour of `MAILERS = {"default": {"BACKEND": ..., "OPTIONS": {...}}}`.
- django-axes 9.0.0 lists Django 6.1 support (needed in Phase 11).
- django-tailwind-cli 4.8.2 downloads the Tailwind standalone binary (pinned with `TAILWIND_CLI_VERSION = "4.3.5"`) into `.django_tailwind_cli/` (gitignored). It is a dev-only dependency, installed in dev settings only.
