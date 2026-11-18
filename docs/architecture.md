# Architecture

Read when creating apps, models, settings or URLs, or deciding where code belongs. Full detail: [PRD › Implementation Decisions](../prd/buff-shop.md#implementation-decisions).

## Stack
- Django + SQLite, htmx, Pillow (installed from Phase 2), `qrcode`, `django-axes`.
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
- Apps: `accounts/`, `catalog/`, `demo/` (more are added by later phases). Tests live in `<app>/tests/`.
- `demo/` has no models: it holds `seed_demo` (`demo/seed.py` has the data and rules, the command only prints).
- Project templates in `templates/` (`base.html`, `includes/`, `icons/`, one folder per app). Tailwind source in `tailwind/source.css`.

## URLs so far
| Name | Path |
|---|---|
| `catalog:index` | `/`: the catalog (`ProductListView`), 12 per page, `?page=N` |
| `accounts:signup` / `accounts:login` / `accounts:logout` (POST only) | `/accounts/signup/`, `/accounts/login/`, `/accounts/logout/` |
| admin | `/admin/` |

## Catalog
- `catalog.Category` (unique name; Textbook, Merchandise and Lab Kit added by data migration `0002`). Edited only in `/admin/`.
- `catalog.Product`: title, category (PROTECT), description, price, optional image, alt text (blank defaults to the title in `save()`), stock, `low_stock_threshold` (default 5), `is_active`. A `CheckConstraint` (`catalog_product_stock_gte_0`) keeps `stock >= 0`.
- **`Product.objects.active()`** is the shared active-products helper. Every customer-facing product query starts from it.
- **`catalog.models.stock_status(stock, threshold)`** returns a `StockStatus` choice: `.value` is the stable id (`in_stock`, `low_stock`, `out_of_stock`) and `.label` is the customer wording. `product.stock_status` uses the product's own threshold.
- Images (`catalog/images.py`): `validate_product_image` (Pillow-detected JPEG/PNG/WebP, max 5 MB) and `product_image_path` (random `products/<uuid>.<ext>`, extension from the detected format). Resizing comes in Phase 13.
- Admin: Category and Product are registered; product stock is read-only there.

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
- Media: `MEDIA_ROOT = media/` (gitignored, uploads only, never mixed with committed `static/`). Dev serves it through `static()` in `config/urls.py`.
- `ALLOW_DEMO_SEED`: `False` in base, `True` only in dev. `seed_demo` refuses without it (independent of `DEBUG`).
- Demo runs on localhost only.

## Research findings (Phase 1, checked in installed source, Nov 2026)
- Django 6.1.3: SQLite `OPTIONS["transaction_mode"]` accepts DEFERRED/IMMEDIATE/EXCLUSIVE (added in Django 5.1).
- Django 6.1 deprecates `EMAIL_BACKEND` and the `EMAIL_*` settings in favour of `MAILERS = {"default": {"BACKEND": ..., "OPTIONS": {...}}}`.
- django-axes 9.0.0 lists Django 6.1 support (needed in Phase 11).
- django-tailwind-cli 4.8.2 downloads the Tailwind standalone binary (pinned with `TAILWIND_CLI_VERSION = "4.3.5"`) into `.django_tailwind_cli/` (gitignored). It is a dev-only dependency, installed in dev settings only.
