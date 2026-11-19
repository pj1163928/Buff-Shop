# Workflow

Read when starting a session, choosing a skill, committing, or logging a session.

## Project pipeline
1. `/grill-me` (done; decisions are in [HANDOFF.md](../HANDOFF.md))
2. `/to-prd` (done; [prd/buff-shop.md](../prd/buff-shop.md))
3. `/prd-to-plan` (done; [plans/buff-shop.md](../plans/buff-shop.md))
4. `/implement` per phase, using `/tdd` for the rules listed in [testing.md](testing.md)
5. `/handoff` at the end of a session, which refreshes `HANDOFF.md`

Other skills:
- `/research` for current library facts, before building with:
  - `django-axes` (email user, account-only locking)
  - SQLite `transaction_mode`
  - the Tailwind standalone CLI
  - a JS QR scanner
- `/prototype` to try a UI or state model.
- `/progressive-disclosure` to rebuild `CLAUDE.md` and these docs.

## Order of work
- Build the risky rules early, in thin end-to-end slices: stock deduction, transitions, pickup verification, access control.
- Add `seed_demo` early so every slice can be demonstrated.
- The AI assistant is a deferred stretch goal. Ask the user which model to use before starting it. Its constraints are in the [PRD › Out of Scope](../prd/buff-shop.md#out-of-scope).

## Demo data
- `uv run python manage.py seed_demo` (code in `demo/seed.py`). Refuses unless `ALLOW_DEMO_SEED` is True (dev settings only).
- So far it creates 5 accounts and 16 products (15 active, some low or out of stock, plus 1 inactive), each with a placeholder photo from `demo/images/`. A product it creates starts at 0 and reaches its demo stock through receive and adjust history recorded by the staff account (`DemoProduct.history`, which must add up to `stock`). Products that already existed get no history, so to see it on an older database, delete `db.sqlite3`, `migrate`, then seed. Later phases add orders in every status.
- Photos: a product with no image (or a missing file) gets its demo photo; an existing image is never replaced. Every demo product must name an `image` and `alt_text`, and every photo must be credited in `demo/images/CREDITS.md` (a test checks both). Use only CC0, public-domain or CC BY images, at most 800 px wide.
- **Development-only logins** (public, printed by the command):

  | Role | Email | Password |
  |---|---|---|
  | superuser | `owner@buffshop.test` | `Owner-Demo-Pass-26` |
  | staff | `staff@buffshop.test` | `Staff-Demo-Pass-26` |
  | customers | `alex@`, `sam@`, `jordan@buffshop.test` | `Customer-Demo-Pass-26` |
- Re-running is safe. It never duplicates, never overwrites product stock, never reactivates a product, and never changes an existing superuser (its password is shown only if it is still the demo one). Only the staff and customer demo accounts are reset to the values above.

## Git
- Git repository on branch `main` (initialised in Phase 1).
- Commit only when the user asks.

## PROMPTS.md (AI usage log)
- Add an entry **only when the user asks**. Never add one unprompted.
- The newest entry goes at the top, below the format block. Never edit or delete old entries.
- Follow the format shown in the file: Prompts (every prompt, in order) and Summary (Outcome, Deviations, Sideways).
