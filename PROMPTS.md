# PROMPTS.md — AI Usage Log

This file is the record of AI use on this codebase. At the end of every
agent session, direct the agent to write the session log with this prompt:

> Append a session log to PROMPTS.md at the repo root, under today's date,
> newest entry at the top. Record every prompt I gave you this session, in
> order, including any corrections. End the entry with a short summary:
> the outcome, any places where I deviated from a recommended answer or
> asked follow-up questions, and anything that went sideways.

Two rules:

- Entries are added only by that prompt, never unprompted.
- New entries go at the top. Never rewrite or delete an old entry — the
  log is part of your work, and an honest log of a session that went
  sideways is worth more than a tidy one.

Each entry has this shape:

    ## YYYY-MM-DD — <one-line summary>

    ### Prompts
    1. ...

    ### Summary
    - **Outcome:** what was built and what was kept
    - **Deviations:** recommendations overridden, follow-up questions asked
    - **Sideways:** failures, wrong turns, and how they were caught
## 2026-11-18 — README with overview, screenshots, setup and testing steps

### Prompts

1. "Go ahead and create and push a new README file keep it simple small and
   easy to understand. include a section about how to test the application
   and all the preperation steps needed, as well as a basic overview tih
   pictures of what the site is and its use case"
2. "Go ahead and add the PROMPTS.md for this entry as well"

### Summary

- **Outcome:** added a short `README.md` and pushed it to GitHub in commit
  `d6864f2`. It has four sections:
  - what the site is for, with three screenshots and a note that only
    Phase 1 (accounts) is built so far
  - one-time preparation: install git and uv, clone, `uv sync`, `migrate`,
    and an optional `createsuperuser`
  - running the site, including the first-run Tailwind download and the
    Windows WinError 4551 workaround
  - testing: `uv run pytest`, `uv run ruff check .`, and five quick browser
    checks
- **Changes:**
  - `README.md` — new, written for anyone opening the repo for the first
    time (instructor, classmates, new developers).
  - `docs/images/home.png`, `docs/images/login.png`,
    `docs/images/signup-phone.png` — screenshots of the running app, taken
    with headless Firefox at 1280 px and 360 px wide.
- **Deviations:** none. A PROMPTS.md entry wasn't written with the README,
  because the project rule is to add entries only when asked. It was added
  afterwards at the user's request.
- **Sideways:** the first screenshot attempt saved nothing. Firefox didn't
  write the relative output paths into the project, and `pkill -f` matched
  its own shell. Using absolute paths and stopping the server by its process
  ID fixed both.

## 2026-11-18 — Buff Shop: Phase 1/18, Project skeleton and email sign-up/login

### Prompts

1. `/clear`, then the `/implement` skill, given `buff-shop.md phase 1`.
2. Approval of the brief, with pasted additions and a styling request:
   - "2. Add explicit email uniqueness requirements": normalise emails in the
     custom User manager, enforce uniqueness at the database level, make the
     admin and other account-creation paths use the same normalisation, and
     test that registering `Pat@WTAMU.edu` and `pat@wtamu.edu` can't create
     two accounts.
   - "3. Clarify SQLite transaction configuration": require
     `transaction_mode = IMMEDIATE`, `timeout = 20`, short transaction
     boundaries, no network requests or email inside database transactions,
     and no `ATOMIC_REQUESTS`.
   - "Also I would like you to style this using similar theming to WTAMUs
     official colors and icons: https://www.wtamu.edu/"
3. Commit question answered: "Go ahead an create a repository called Buff
   Shop and commit and push the changes". Extra files to include:
   `prd/buff-shop.md` and `.claude/` (not `HANDOFF.md`).

### Summary

- **Outcome:** Phase 1 built. Visitors sign up (first name, last name,
  email, password, with Django's four password validators), are logged in
  straight away, and log in and out by email. "Remember me" keeps the
  session for two weeks; otherwise it ends at browser close. 49 tests pass
  with 100% line and branch coverage. `ruff check` and `ruff format --check`
  are clean. `check --deploy` passes under production settings.
- **Changes:**
  - `.gitignore`, `pyproject.toml`, `uv.lock` — git initialised on `main`;
    uv project with Django 6.1.3 and dev tools (django-tailwind-cli 4.8.2,
    pytest, pytest-django, pytest-cov, factory-boy, ruff); pytest, coverage
    and ruff config.
  - `manage.py`, `config/wsgi.py`, `config/asgi.py` — manage.py defaults to
    dev settings; wsgi/asgi default to prod.
  - `config/settings/base.py` — shared settings: SQLite with
    `transaction_mode="IMMEDIATE"`, `timeout=20`, `ATOMIC_REQUESTS=False`
    and comments on the transaction rules; custom user; the four password
    validators; login URLs; two-week session age.
  - `config/settings/dev.py` — debug, dev key, console email via
    `MAILERS`, Tailwind CLI settings (pinned to Tailwind 4.3.5).
  - `config/settings/prod.py` — secrets and hosts from environment
    variables, SSL redirect, secure cookies, HSTS, SMTP via `MAILERS`.
  - `config/urls.py` — admin, `accounts/`, and the catalog home.
  - `accounts/models.py`, `accounts/migrations/0001_initial.py` — the
    email-login `User` (no username, names required), `UserManager`, and
    `normalize_email()`, used by the manager, `clean()` and `save()`; plus a
    `Lower("email")` unique constraint in the first migration.
  - `accounts/forms.py`, `accounts/views.py`, `accounts/urls.py` — sign-up,
    email login with "Remember me" and a generic failure message, POST-only
    logout.
  - `accounts/admin.py` — Django admin for the email user, so admin-created
    users are normalised too.
  - `catalog/views.py`, `catalog/urls.py` — placeholder home at `/`
    (`catalog:index`) until Phase 2.
  - `templates/base.html`, `templates/includes/*.html`,
    `templates/accounts/*.html`, `templates/catalog/index.html`,
    `templates/icons/*.svg` — accessible base layout (skip link, landmarks,
    visible focus, 360 px), labelled form fields with linked errors and help
    text, status messages with icon and text, Font Awesome Free solid icons
    inlined.
  - `tailwind/source.css`, `static/css/site.css` — WTAMU-style theme and the
    committed built stylesheet.
  - `accounts/tests/*`, `catalog/tests/test_layout.py`,
    `config/tests/test_settings.py` — model, sign-up, login/session, admin,
    layout and settings tests (including a `check --deploy` subprocess
    test).
  - `CLAUDE.md`, `docs/architecture.md`, `docs/frontend.md`,
    `docs/testing.md`, `docs/workflow.md`, `docs/business-rules.md` —
    commands (including the Tailwind build), layout, URLs, account and
    transaction rules, research findings, theme and test layout.
  - `plans/buff-shop.md` — Phase 1 acceptance criteria ticked.
- **TDD:** skipped, as the plan recommends: the phase is setup and
  configuration on Django's built-in auth. Every acceptance criterion has
  ordinary tests.
- **Decisions:**
  - Django 6.1.3 (current). Checked in the installed source: SQLite
    `transaction_mode` exists (Django 5.1+), and django-axes 9.0.0 supports
    Django 6.1.
  - Tailwind via django-tailwind-cli, which downloads the standalone binary
    (no Node.js). The source CSS is in `tailwind/` because the package warns
    when it sits inside `static/`.
  - Emails are stored trimmed and lowercased everywhere. Sign-up logs the
    customer in with a browser-close session. Logout is POST-only.
  - Theme: maroon `#450012` and related shades, charcoal `#332c2c`, Oswald
    and Nunito Sans, all read from wtamu.edu's own stylesheets. No gold
    (none in their CSS). No WTAMU logo. Font Awesome Free 6.7.2 solid icons
    match the site's icon style, with CC BY 4.0 attribution in the footer.
    Every colour pair was checked: all pass AA, most pass AAA.
  - Light theme only, like wtamu.edu.
  - The Phase 1 home page is a placeholder `catalog:index`, so the URL
    name stays stable when Phase 2 builds the catalog.
  - `seed_demo` doesn't exist until Phase 2, so this phase adds no seed
    data.
- **Deviations:** the user added stricter email-uniqueness requirements
  (manager normalisation, database constraint, admin path, case-variant
  test) and explicit SQLite transaction rules. All were built, and the rules
  were added to the docs. The user also asked for WTAMU-style theming, which
  wasn't in the plan. Instead of "Commit only", the user asked for a new
  GitHub repository called "Buff Shop" and a push. GitHub names can't
  contain spaces, so it was created as `Buff-Shop`, private by default.
- **Sideways:**
  - The web-fetch agent couldn't read wtamu.edu's colours, because it gets
    pages as text without CSS. Downloading the site's stylesheets with curl
    and counting colour values worked instead.
  - Django 6.1 deprecates `EMAIL_BACKEND` in favour of `MAILERS`. A
    deprecation warning in the first test run caught it. The dev mail test
    also failed because the test runner swaps in an in-memory mailer; it now
    reads the dev settings module directly.
  - A scripted edit to `prod.py` used an end marker that also appeared
    earlier in the docstring. The replacement went in between every
    character and the file grew to 837 KB. The SyntaxError from the
    `check --deploy` test caught it, and the file was rewritten.
  - The first Tailwind build failed with "Cannot apply unknown utility
    class `btn`": Tailwind v4 can't `@apply` a class from
    `@layer components`. The shared classes now use `@utility`. The
    standalone binary is about 109 MB, so the first download took several
    minutes.

## 2026-11-18 — Phased implementation plan (/prd-to-plan)

### Prompts
1. `/clear`, then `/prd-to-plan @prd/buff-shop.md`
2. Pasted review of the proposed 19-phase breakdown, titled "Recommended
   changes":
   1. Phase 3: make the dashboard access-control test persistent, so it
      picks up routes added in later phases, and require an access test
      for every new dashboard endpoint.
   2. Phase 4: clarify the transaction strategy and the target database,
      since IMMEDIATE transactions are database-specific. Keep the
      conditional stock update and the constraint as independent
      safeguards.
   3. Phase 6: enforce database-level uniqueness for order numbers and
      pickup codes, generate pickup codes securely, and handle collisions.
   4. Phase 9: define handover as irreversible. No repeat confirmation and
      no stock restore through ordinary cancellation. Test repeated
      confirmation and invalid transitions.
   5. Phase 14: clarify what happens to sessions and open orders when a
      customer is disabled, and make sure the action and reason are
      audited.
   6. Phase 19: make 85% coverage an explicit minimum that doesn't replace
      dedicated tests for the critical rules.

   Followed by: "I'd explicitly add a requirement that each phase updates
   seed_demo whenever it introduces new functionality. Append all
   conversations to PROMPTS.md according to source formatting"

### Summary
- **Outcome:**
  - Wrote `plans/buff-shop.md` with 19 tracer-bullet phases covering all
    89 user stories.
  - The plan header records the durable decisions: database and
    transactions, named URLs (products by ID, orders by order number),
    models per app, uniqueness rules, access control, and statuses.
  - A "Rules for every phase" checklist was added. It requires every phase
    to update `seed_demo`, to have its new `/dashboard/` routes covered by
    the persistent access test, to give critical rules dedicated tests,
    and to pass the lint and accessibility basics.
  - All six review recommendations were folded in:
    - Phase 3: the access test discovers dashboard routes from the URL
      resolver and fails on routes it can't walk.
    - Database: SQLite is named as the target, with IMMEDIATE noted as
      SQLite-only, and the two stock safeguards are tested separately.
    - Phase 6: unique constraints, `secrets`-based codes, and a retry on
      collision.
    - Phase 9: handover is irreversible, with repeat-confirm and
      cancel-after-pickup tests.
    - Phase 14: sessions are deleted, open orders are left to staff via an
      unticked checkbox, and every action is audited.
    - Phase 19: 85% is a floor, not a substitute for the critical tests.
  - Updated the "next step" pointers in `CLAUDE.md` and
    `docs/workflow.md`.
- **Deviations:**
  - The user didn't answer Claude's three breakdown questions (19 fine
    phases vs. about 10 coarser ones, the two candidate merges, the order
    of search and product editing). Instead they sent review changes. The
    proposed 19-phase breakdown and order were kept as presented.
  - The user added the per-phase `seed_demo` requirement, which goes
    beyond the PRD's "add seed_demo early".
- **Sideways:**
  - Two review points asked about things the PRD had already decided:
    - the target database (SQLite, mandated by the brief)
    - disable behaviour (sessions deleted; staff choose about open orders
      via a checkbox)

    The plan states these explicitly rather than changing them.
  - "Handover is irreversible" conflicts slightly with the PRD's superuser
    override, which can move an order out of Picked Up, and into Cancelled
    with a stock restore. The plan keeps the override as the single,
    logged exception, because the review only ruled out *ordinary*
    cancellation.

## 2026-11-18 — CLAUDE.md with progressive disclosure, plus a skill for it

Continues the same session as the `/to-prd` entry below. That entry was
logged mid-session, so these later prompts are added here as a new entry
instead of editing it.

### Prompts
1. "Alright what I would like for you to do is to create a CLAUDE.md file
   with prorgressive disclosure with docs files placed in a docs folder.
   Information contained within this should remin succing and necessary and
   should not be overly long. Actually please create a skill in .claude
   called progressive-disclosure that accomplishes this task automatically
   as well for future projects."
2. "Go ahead and append these messages to PROMPTS.md as well"

### Summary
- **Outcome:**
  - Created the `progressive-disclosure` project skill (48 lines). It
    surveys the repo and sorts each fact into one of three places:
    `CLAUDE.md`, a topic doc in `docs/`, or a link to an existing spec.
    It then writes the files and checks the links and line counts.
  - Ran the skill's process on this project. That produced `CLAUDE.md`
    (33 lines) and five docs: `architecture.md`, `business-rules.md`,
    `frontend.md`, `testing.md` and `workflow.md`, each between 35 and 60
    lines. The docs link back to the PRD for full detail.
  - All links were verified to resolve.
- **Deviations:** No recommendations were overridden. Claude offered to
  copy the skill to `~/.claude/skills/` so it works in future projects;
  the user hasn't answered yet.
- **Sideways:**
  - The skill lives in this project's `.claude/` folder as asked, so it
    won't be available in other projects until it is copied to the
    personal skills folder.
  - The commands in `CLAUDE.md` are marked "planned" because no code
    exists yet. The Tailwind build command is left to be confirmed during
    setup.
  - No PROMPTS.md entry was added after the first prompt, because the log
    rules say entries are added only when the user asks. This entry was
    written after the user asked.

## 2026-11-18 — PRD written from HANDOFF.md (/to-prd)

### Prompts
1. `/clear`, then `/to-prd @HANDOFF.md - append this sessions messages
   including this one to PROMPTS.md according to source formatting.`

### Summary
- **Outcome:** Wrote `prd/buff-shop.md` from the decisions in
  `HANDOFF.md`, following the to-prd template: problem, solution,
  89 user stories, implementation decisions, testing decisions, out of
  scope, and further notes. No new scope was added. Updated the "State of
  the work" section of `HANDOFF.md` to name the PRD as the source of truth
  and `/prd-to-plan` as the next step; the decision list in `HANDOFF.md`
  was left in place. No code was written, and the folder is still not a
  git repository.
- **Deviations:** None. The skill says not to interview the user, so no
  questions were asked.
- **Sideways:**
  - The two interpretations flagged last session (the override reason in
    Q10 and the staff-only silencing in Q13) are still unconfirmed. They
    are listed under "Interpretations to confirm" in the PRD's Further Notes
    rather than asked about.
  - The PRD template has no "Testing Decisions" heading, but the handoff
    contained detailed testing decisions, so a section for them was added.

## 2026-11-18 — Design interview (/grill-me) for the Buff Shop app, then handoff

### Prompts
1. `/clear`, then `/grill-me` with the full client brief: the Buff Shop owner's
   quote (catalog with stock status, login-only ordering, pay at pickup,
   order history with five statuses, pickup passcode/QR, optional on-topic AI
   assistant, admin dashboard for products/prices/restock/orders/pickup
   verification/user enable-disable, analytics with revenue, order count,
   top 5, low stock under 5, and reminder messages), requirements FR-C1–C3,
   FR-A1–A2, NFR-C1–C3, NFR-A1–A2 with user stories, and the stack: Django,
   pytest, ruff, SQLite, htmx, Pillow, accessible and mobile-friendly.
2. Q1 (login identifier): "A" — email + password, custom user model.
3. Q2 (roles): "C" — `is_staff` = Admin, `is_superuser` held for later.
4. Q3 (admin surface): "C" — custom `/dashboard/`, `/admin/` superuser only.
5. Q4 (categories): "C" — Category table, edited only in `/admin/`.
6. Q5 (sizes/variants): "A" — no variants, one product = one stock count.
7. Q6 (discontinued products): "B" — soft delete with an Active switch.
8. Q7 (low-stock rule): "B" — per-product threshold, default 5.
9. Q8 (cart): "A" — database cart, no stock held until checkout.
10. Q9 (cancellation): "B - also make it to where staff can add a
    cancelation reason as well"
11. Q10 (status changes): "B - but allow an override if a mistake occurs and
    explain the reasoning"
12. Q11 (override scope, follow-up to Q10): "B" — superuser only, any status
    except out of Cancelled.
13. Q12 (pickup verification): "A" — QR code plus typed passcode fallback.
14. Q13 (staff reminders): "B - but lighter the message can be dimissied but a
    banner will be placed over the item on a staff viewpoint, for a user it
    will show low stock act soon. It will periodically re-appear and an option
    to allow users to silence banner notifications."
15. Q14 (silencing, follow-up to Q13): "B" — per-staff snooze (1 hour / end of
    day).
16. Q15 (revenue definition): "C" — Collected vs Pending revenue shown
    separately.
17. Q16 (login lockout): "A" — `django-axes`, lock by account only.
18. Q17 (disabling a customer with open orders): "C" — staff choose, with a
    "cancel these too?" checkbox.
19. Q18 (AI assistant): "C" — not built now; stretch goal.
20. Q19 (checkout steps): "A" — two steps, Cart → Confirmation.
21. Q20 (search fields): "B" — title + description, plus category filter.
22. Q21 (images): "B" — optional, placeholder, one Pillow-resized copy.
23. Q22 (email): "C" — password reset + "Ready for Pick Up" email.
24. Q23 (hosting/HTTPS): "A" — localhost only for the class demo.
25. Q24 (styling): "C" — Tailwind CSS.
26. Q25 (Tailwind build, follow-up to Q24): "A" — standalone CLI, no Node.js.
27. Q26 (safe stock deduction): "B" — conditional single-statement update +
    `stock >= 0` constraint.
28. Q27 (testing): "B" — critical-rule tests, 85% coverage, automatic
    dashboard access test.
29. Q28 (restocking): "C" — Receive Stock + Stock Adjustment + stock history
    log.
30. Q29 (order numbers): "B" — `BUF-<year>-<sequence>`.
31. Q30 (sign-up fields): "B" — first name, last name, email, password.
32. Q31 (demo data): "C" — `seed_demo` management command.
33. `/handoff` — write HANDOFF.md for a fresh agent.
34. "please append this chat log to PROMPTS.md according to source formatting"

### Summary
- **Outcome:** Design interview completed: 31 questions covering accounts,
  roles, catalog, cart/checkout, stock integrity, the order lifecycle, pickup
  verification, notifications, analytics, email, hosting, styling, testing,
  and demo data. All decisions, plus the condensed client requirements, are
  recorded in `HANDOFF.md`. No code, PRD, or plan was written; the folder is
  still not a git repository. Next step: `/to-prd`, then `/prd-to-plan`.
- **Deviations:**
  - Recommendations overridden:
    - Q7: chose per-product low-stock thresholds over a single shop-wide 5.
    - Q23: chose localhost-only over PythonAnywhere hosting. As a result,
      HTTPS is shown only by production settings and `check --deploy`, phone
      QR scanning over the LAN won't work, and emails print to the console.
    - Q24: chose Tailwind over Pico CSS. That added the Q25 build question
      and a manual accessibility checklist.
  - Recommendations extended by the user:
    - Q9: staff must give a cancellation reason.
    - Q10: added a status override for mistakes. This led to follow-up Q11.
    - Q13: redesigned reminders as a dismissible, re-appearing pop-up, a
      "Low Stock" badge on staff items, a "Low Stock — act soon" badge for
      customers, and a silence option. This led to follow-up Q14.
  - Smaller defaults that Claude stated alongside questions were accepted
    without comment and recorded as decisions. Examples: price snapshot on
    order lines, cancel restores stock, the analytics time filter, the
    password and lockout defaults.
- **Sideways:**
  - Two answers were ambiguous. In Q10, "explain the reasoning" was read as
    "the person overriding must type a reason". In Q13, "users" silencing
    banners was read as staff, and customers were given nothing to silence.
    Claude stated both interpretations and asked for correction; the user
    didn't correct them, but neither was explicitly confirmed. Worth
    re-checking when writing the PRD.
  - The `claude-api` reference was loaded for Q18 to get model names and
    prices right, then the assistant was deferred, so that lookup turned out
    not to be needed yet.
