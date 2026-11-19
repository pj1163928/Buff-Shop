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
- **`/admin/` is superuser-only** through `config/admin.py`'s `SuperuserAdminSite` (`has_permission` needs an active superuser; its login form refuses non-superusers too). `config/apps.py`'s `SuperuserAdminConfig` replaces `django.contrib.admin` in `INSTALLED_APPS` and makes it the default `admin.site`, so `@admin.register` works as usual.
- Categories are edited only in `/admin/`.

## Data rules
- Create the custom user model **before the first migration**.
- Products are soft-deleted (`is_active`); no hard delete from the dashboard.
- Each product has its own `low_stock_threshold` (default 5).
- Order number format: `BUF-<year>-<5-digit seq>`.

## Layout
- `config/settings/{base,dev,prod}.py`, `config/urls.py` (includes each app's namespaced URLs).
- Apps: `accounts/`, `catalog/`, `stock/`, `cart/`, `dashboard/`, `demo/` (more are added by later phases). Tests live in `<app>/tests/`.
- `demo/` has no models: it holds `seed_demo` (`demo/seed.py` has the data and rules, the command only prints) and the demo product photos in `demo/images/`.
- Project templates in `templates/` (`base.html`, `includes/`, `icons/`, one folder per app). Tailwind source in `tailwind/source.css`.

## URLs so far
| Name | Path |
|---|---|
| `catalog:index` | `/`: the catalog (`ProductListView`), 12 per page, `?page=N` |
| `accounts:signup` / `accounts:login` / `accounts:logout` (POST only) | `/accounts/signup/`, `/accounts/login/`, `/accounts/logout/` |
| `cart:detail` | `/cart/`: the logged-in user's cart (`CartView`), active lines only, with line and cart totals |
| `cart:add` (POST only) | `/cart/add/<product_id>/`: add `quantity` (≥ 1) of an active product, then back to the safe `next` URL (default the catalog) |
| `cart:line` (POST only) | `/cart/lines/<product_id>/`: set a line's `quantity` (0 removes it). htmx gets `cart/_update.html`; without JS it redirects to `/cart/` with a message. 404 if the user has no line for that active product |
| `dashboard:home` | `/dashboard/`: staff home (`DashboardHomeView`) |
| `dashboard:product_list` | `/dashboard/products/`: every product incl. inactive, 25 per page, `?page=N`, with a "Manage stock" link per row |
| `dashboard:product_stock` | `/dashboard/products/<pk>/stock/`: Receive Stock and Stock Adjustment forms (GET/POST) and the product's stock history, newest first, 25 per page |
| admin | `/admin/`, superuser only |

## Catalog
- `catalog.Category` (unique name; Textbook, Merchandise and Lab Kit added by data migration `0002`). Edited only in `/admin/`.
- `catalog.Product`: title, category (PROTECT), description, price, optional image, alt text (blank defaults to the title in `save()`), stock, `low_stock_threshold` (default 5), `is_active`. A `CheckConstraint` (`catalog_product_stock_gte_0`) keeps `stock >= 0`.
- **`Product.objects.active()`** is the shared active-products helper. Every customer-facing product query starts from it.
- **`catalog.models.stock_status(stock, threshold)`** returns a `StockStatus` choice: `.value` is the stable id (`in_stock`, `low_stock`, `out_of_stock`) and `.label` is the customer wording. `product.stock_status` uses the product's own threshold.
- Images (`catalog/images.py`): `validate_product_image` (Pillow-detected JPEG/PNG/WebP, max 5 MB) and `product_image_path` (random `products/<uuid>.<ext>`, extension from the detected format). Resizing comes in Phase 13.
- Admin: Category and Product are registered; product stock is read-only there.

## Stock
- `stock.StockMovement`: product (PROTECT), change, resulting stock, kind (`MovementKind`: checkout / cancel / receive / adjust), user (PROTECT), `created_at`, reason, `submission_token` (unique, nullable). DB constraints: change ≠ 0, unique token. Phase 6 adds a nullable `order` link.
- **History is append-only.** `save()` on an existing row, `delete()`, and queryset `update()` / `bulk_update()` / `delete()` raise `ImmutableHistoryError`. Correct a count with a new adjustment. `/admin/` shows it view-only.
- **`stock.services.change_stock(product, change, *, kind, user, reason="", submission_token=None)`** is the one stock helper. See [business-rules.md](business-rules.md#stock-nfr-a2).
- Forms: `dashboard/forms.py` (`ReceiveStockForm`, `StockAdjustmentForm`, both carrying a one-time hidden token; prefixes `receive-` / `adjust-` and a hidden `action` field tell them apart on the one page).

## Cart
- `cart.Cart` (one per user, `OneToOneField`; `Cart.objects.for_user(user)` gets or creates it) and `cart.CartLine` (cart, product (CASCADE: a cart isn't history), quantity). DB constraints: one line per cart and product (`cart_cartline_unique_product`), quantity ≥ 1 (`cart_cartline_quantity_gte_1`).
- **The cart never changes stock** and reserves nothing. Stock moves only at checkout, through `change_stock()`.
- **`Cart.add(product, quantity=1)`** and **`Cart.set_quantity(product, quantity)`** return a `CartUpdate` (`quantity`, `capped`, `removed`, `available`). Rules are in [business-rules.md](business-rules.md#cart).
- **`CartLine.objects.for_user(user).contents()`** (a `CartContents` with `lines`, `total`, `item_count`) and **`.item_count()`** (active units, one aggregate query) both apply `CartLine.objects.active()`, which filters through `Product.objects.active()`. Use them for anything a customer sees.
- Header "Cart (N)": `cart.context_processors.cart_item_count` gives a lazy `cart_item_count` (one query, only if rendered, none for visitors). Views that already loaded the cart pass their own `cart_item_count`, which wins (`cart.views.cart_context`).
- Admin: Cart with inline lines (superuser only).

## Dashboard
- **The one staff check** is `dashboard/access.py`: `StaffRequiredMixin` (active `is_staff`) and `SuperuserRequiredMixin` (also `is_superuser`), built on `UserPassesTestMixin`. Anonymous → redirect to login with `?next=`; logged-in without the role → 403 (`templates/403.html`, "Access denied").
- **Every dashboard view is class-based and puts the mixin first** in its bases, so the check runs in `dispatch()` before any handler, for every HTTP method, and before any object lookup (a customer gets 403, not 404).
- **Every new dashboard route must be registered** in `dashboard/tests/routes.py` (name, methods, sample kwargs, `superuser_only`), or the access test fails. See [testing.md](testing.md).
- Staff product queries do **not** use `active()`: staff see every product.

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
