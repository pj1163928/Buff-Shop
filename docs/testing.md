# Testing

Read when writing or running tests, or finishing a plan phase. Full list: [PRD › Testing Decisions](../prd/buff-shop.md#testing-decisions).

## Tools and targets
- pytest-django, factory_boy (factories for users, categories, products, carts and orders), pytest-cov, ruff.
- **85% line coverage.**
- Test behaviour through public interfaces: the Django test client for views, service functions for business rules.
- Layout: `<app>/tests/test_*.py`. Factories are in `<app>/tests/factories.py` (`accounts.tests.factories`: `UserFactory`, `StaffFactory`, `SuperuserFactory`, `DEFAULT_PASSWORD`; `catalog.tests.factories`: `CategoryFactory` (get-or-create by name, reuses the seeded categories), `ProductFactory`).
- Factories set `is_staff=False` and `is_superuser=False` explicitly on `UserFactory`, so a "customer" can never gain a role from a default.
- **Persistent dashboard access test** (`dashboard/tests/`):
  - `walk.py` discovers every route in the `dashboard` namespace or under `/dashboard/`, following nested `include()`s to any depth, and requests each one with **all eight HTTP methods**.
  - `test_access.py`: anonymous → login redirect back to the exact URL; customer → 403; plain staff → 403 on `superuser_only` routes; staff/superuser let in on their registered methods.
  - Routes needing no arguments are requested by path even if unregistered. A route that can't be built is a failure, never skipped.
  - `test_every_dashboard_route_is_walkable` fails unless every route is named, class-based, uses `StaffRequiredMixin`, and is registered in `routes.py` with sample kwargs that build it, its exact methods, and the right `superuser_only`. Stale entries fail too.
  - **Adding a dashboard route = add one `RouteSpec` to `dashboard/tests/routes.py`.** Never weaken or bypass this test.
  - `test_walk.py` tests the walk itself against `walk_fixture_urls.py` (nested files, an unguarded route, a stray route, a superuser-only route).
- `config/tests/test_admin_site.py`: `/admin/` refuses anonymous, customers and plain staff (pages, data changes and the admin login form) and works for the superuser.
- `demo/tests/test_seed_demo.py` covers idempotency, protected data and the refusal under production settings (in a subprocess).
- `config/tests/test_settings.py` checks the SQLite options and runs `check --deploy` under prod settings in a subprocess.
- The root `conftest.py` points `MEDIA_ROOT` at a temporary folder for every test, so tests that seed or upload never write to `media/`.
- **The test database is a SQLite file**, not Django's in-memory default (root `conftest.py`, `django_db_modify_db_settings`). In-memory shared-cache SQLite fails a waiting writer at once with "database table is locked", so it can't test concurrency. `PRAGMA synchronous=OFF` keeps it fast without changing locking.
- **Stock** (`stock/tests/`): `test_change_stock.py` (the TDD rules, validation, rollback when the history insert fails, tokens, append-only history); `test_concurrency.py` (real threads with their own connections, `django_db(transaction=True)`, released together by a barrier; checked to fail against a naive read-then-write helper); `test_admin.py` (view-only). The dashboard page is in `dashboard/tests/test_stock_page.py`.
- The negative-stock CHECK constraint is tested on its own in `catalog/tests/test_models.py`.
- The test runner swaps in an in-memory mailer, so read `config.settings.dev` directly to check the dev mail config. Use `mailoutbox`/`mail.outbox` for sent mail.

## Build with TDD (`/tdd`)
Each phase's TDD picks, and the tests to write first, are in the "TDD" subsection of that phase in [plans/buff-shop.md](../plans/buff-shop.md). The PRD's must-haves:
- the stock-change helper
- the status-transition table
- pickup code verification
- the dashboard access-control test

## Required critical-rule tests
- **Stock and checkout:**
  - all short items are named, with nothing deducted
  - the cart is untouched on failure
  - stock never goes negative
  - a double submit creates one order
  - cancel restores stock
  - every change writes a history row
- **Concurrency:** two simultaneous checkouts for the last unit; exactly one succeeds.
- **Pickup:** right code, wrong code, used code, cancelled order, not-yet-Ready order, and case/hyphen normalisation.
- **Transitions:** every allowed and disallowed move; Picked Up reachable only by verification; the override is superuser-only, can't leave Cancelled, needs a reason, and is logged.
- **Access:**
  - a test walks **every** `/dashboard/` URL as both an anonymous user and a customer, and both are refused
  - `/admin/` refuses plain staff
  - another user's order gives a 404
  - staff can't disable staff or the superuser
- **Lockout:**
  - 5 failures cause a 15-minute lock
  - the error is generic
  - a disabled user can't log in and their sessions end

## Manual demo checklist (no Playwright)
- the 360 px layout
- QR display and laptop webcam scanning
- a keyboard-only order walkthrough
- screen-reader announcement of htmx updates
- both emails in the console
