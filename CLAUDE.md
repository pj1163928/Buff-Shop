# Buff Shop

A Django web app for a campus shop. Customers browse the catalog and order to pay at pickup. Staff manage stock, orders, pickup handover and analytics. CIDM 4360 final project.

## Current state
- **Source of truth:** [prd/buff-shop.md](prd/buff-shop.md). **Plan:** [plans/buff-shop.md](plans/buff-shop.md) (18 phases, plus rules for every phase). Phases 1–5 are built (accounts; read-only catalog and first `seed_demo`; dashboard shell, the persistent access test and superuser-only `/admin/`; the safe stock helper with Receive Stock, Stock Adjustment and stock history; the per-user cart with htmx quantity updates).
- **Next step:** implement Phase 6 of the plan.

## Commands
Python and packages are managed with `uv` (Django 6.1, Python 3.12+).
- `uv sync` · `uv run python manage.py migrate`
- `uv run pytest` (coverage included) · `uv run ruff check .` · `uv run ruff format .`
- `uv run python manage.py tailwind runserver`: dev server plus Tailwind watcher (first run downloads the standalone binary)
- **Tailwind build:** `uv run python manage.py tailwind build`. It builds `tailwind/source.css` into `static/css/site.css`, which is committed. Rebuild after changing classes in templates.
- `uv run python manage.py seed_demo`: demo accounts and products (dev only; logins in [docs/workflow.md](docs/workflow.md))
- `manage.py` uses `config.settings.dev`. `wsgi.py`/`asgi.py` use `config.settings.prod`.

## Always-on rules
- Every customer-facing product query goes through the shared active-products helper.
- Every stock change goes through the one safe stock helper. Never rely on `select_for_update()`, because SQLite ignores it.
- Order status changes only through the allowed-transitions table. Picked Up is reachable only through pickup verification.
- Every `/dashboard/` view and action checks the staff role on the server (`StaffRequiredMixin` first in its bases), and every new dashboard route is registered in `dashboard/tests/routes.py`. A customer requesting another user's order gets a 404.
- Never expose the pickup code in email, logs or the assistant.
- Accessibility is WCAG 2.2 AA. Status is never shown by colour alone.
- Commit only when asked. Add PROMPTS.md entries only when asked.

## Working with the user
- The user is a beginner. Explain options plainly, recommend one, and give the reason.

## Docs: read when relevant
| Read when… | File |
|---|---|
| Creating apps, models, settings or URLs, or deciding where code goes | [docs/architecture.md](docs/architecture.md) |
| Touching stock, checkout, statuses, pickup codes, accounts, alerts or analytics | [docs/business-rules.md](docs/business-rules.md) |
| Writing templates, htmx, CSS, images or the QR scanner | [docs/frontend.md](docs/frontend.md) |
| Writing or running tests, or finishing a phase | [docs/testing.md](docs/testing.md) |
| Starting a session, picking a skill, committing or logging | [docs/workflow.md](docs/workflow.md) |
