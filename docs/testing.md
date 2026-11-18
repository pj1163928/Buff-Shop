# Testing

Read when writing or running tests, or finishing a plan phase. Full list: [PRD › Testing Decisions](../prd/buff-shop.md#testing-decisions).

## Tools and targets
- pytest-django, factory_boy (factories for users, categories, products, carts and orders), pytest-cov, ruff.
- **85% line coverage.**
- Test behaviour through public interfaces: the Django test client for views, service functions for business rules.
- Layout: `<app>/tests/test_*.py`. Factories are in `<app>/tests/factories.py` (`accounts.tests.factories`: `UserFactory`, `StaffFactory`, `SuperuserFactory`, `DEFAULT_PASSWORD`).
- `config/tests/test_settings.py` checks the SQLite options and runs `check --deploy` under prod settings in a subprocess.
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
