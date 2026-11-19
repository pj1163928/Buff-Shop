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
## 2026-11-18 — Buff Shop: Phase 4/18, Safe stock helper, Receive Stock and Stock Adjustment

### Prompts

1. The `/implement` skill, given `buff-shop.md phase 4`.
2. Four adjustments to the brief before building (pasted):
   1. Make stock changes atomic, including history: validate, run the
      conditional update, read the resulting stock, create exactly one
      history row, and roll everything back if the history insert fails.
      Never let stock change without a history entry.
   2. Strengthen the conditional UPDATE: enforce `stock + :change >= 0` in
      SQL, not with a Python-side check, and verify exactly one row changed.
   3. Clarify validation: Receive is positive only with an optional reason;
      Adjustment is positive or negative with a required reason; zero is
      rejected; an adjustment beyond available stock is rejected. Enforce the
      10,000-unit limit server-side.
   4. Add ordinary tests for concurrency (two simultaneous deductions can't
      go negative), rollback (a failed history insert rolls back the stock
      update; a failed update writes no history), and repeated form
      submissions not duplicating a change. Verify real behaviour rather
      than assume IMMEDIATE works.
   Plus: keep `StockMovement` immutable; the admin read-only, and no
   ordinary code path may edit or delete history. Corrections are new
   adjustments.
3. "Everything looks good move to next" (approved TDD test 1).
4. "This looks good move to next" (approved TDD test 2).

### Summary

- **Outcome:** a new `stock` app with the one stock helper,
  `change_stock()`, and an append-only `StockMovement` history. A staff
  stock page at `/dashboard/products/<pk>/stock/` has Receive Stock, Stock
  Adjustment and the product's history, newest first. `seed_demo` brings new
  demo products to their stock through recorded receives and adjustments.
  232 tests pass (160 before), at 100% line and branch coverage. `ruff check`
  and `ruff format --check` are clean. Not committed when this entry was
  written.
- **Changes:**
  - `stock/` (new): `models.py` has `StockMovement`, `MovementKind`,
    `ImmutableHistoryError`, and a queryset that refuses `update()`,
    `bulk_update()` and `delete()`. The DB refuses a 0 change and a reused
    submission token. `services.py` has `change_stock()`, `InsufficientStock`,
    `DuplicateSubmission` and `MAX_STOCK_CHANGE`. `admin.py` is view-only.
    There is one migration, `0001_initial`.
  - `stock/tests/`: `test_change_stock.py` (the TDD rules, validation,
    rollback, tokens, immutability), `test_concurrency.py` (real threads)
    and `test_admin.py`.
  - `dashboard/forms.py` (new): `ReceiveStockForm` and
    `StockAdjustmentForm`, each with a one-time hidden token.
  - `dashboard/views.py`, `urls.py`, `tests/routes.py`: `ProductStockView`
    (`dashboard:product_stock`, GET/POST), registered with the access walk.
  - `templates/dashboard/product_stock.html` (new), plus a "Manage stock"
    link per row in `product_list.html`. Three Font Awesome icons (truck,
    sliders, clock-rotate-left).
  - `dashboard/tests/test_stock_page.py` (new): forms, validation, the
    refusal message, double posts, history order and pagination.
  - `demo/seed.py`, the `seed_demo` command and its tests: `DemoProduct.history`;
    new products start at 0 and reach their stock through the helper, and
    existing products get no history.
  - `conftest.py`: the test database is now a SQLite file with
    `synchronous=OFF` (see Sideways).
  - `config/settings/base.py`: `stock` installed.
  - `static/css/site.css`: rebuilt.
  - Docs: `architecture.md`, `business-rules.md`, `testing.md`,
    `workflow.md`, and the `CLAUDE.md` current state. The plan's Phase 4
    criteria are ticked.
- **TDD:** two behaviours, each seen RED on an assertion and then GREEN:
  (1) a change that would go negative is refused, and stock and history are
  unchanged; (2) a successful change writes exactly one history row with
  change, resulting stock, kind, user and time. The plan's third behaviour
  (the DB CHECK constraint) was already built and tested in Phase 2
  (`catalog/tests/test_models.py`), so it couldn't go RED and was left as an
  existing test.
- **Decisions:**
  - The helper raises `InsufficientStock` rather than returning `False`,
    so a caller can't ignore a refusal by mistake.
  - The `order` link on `StockMovement` waits for Phase 6.
  - One URL serves both forms, told apart by a hidden `action` field and
    form prefixes.
  - There is a 10,000-unit cap, enforced in the helper as well as the forms.
  - History shows 25 per page.
  - The helper stamps `created_at` itself.
  - `StockMovement` uses PROTECT for its product and user, so neither can
    be deleted while it has history.
  - The seed only writes history for products it creates, so an older
    `db.sqlite3` needs a fresh start to show it.
- **Deviations:** the user's four adjustments, plus immutability, were all
  adopted. Their SQL condition `stock + change >= 0` is implemented as the
  equivalent `stock >= -change`. The one-time submission token was added to
  make "repeated submissions can't duplicate" hold for double clicks, not
  only page refreshes. Because history became immutable, the planned
  backdating of seed history was dropped.
- **Sideways:**
  - The concurrency tests first failed with "database table is locked".
    Django's default in-memory shared-cache test database fails a waiting
    writer at once instead of honouring the busy timeout, so it doesn't
    behave like `db.sqlite3`. The fix was a file-based test database. That
    raised the suite from 79 s to 198 s; `synchronous=OFF` brought it to
    146 s.
  - A concurrency test was wrong: starting at 5, the deductions could
    legitimately dip below 0 depending on order. It now starts at 6 and
    checks that the history forms one unbroken chain.
  - To prove the concurrency tests aren't vacuous, a naive
    read-check-write helper was swapped in temporarily. All three tests
    failed, and the real helper was restored and checked byte-for-byte.
  - Two page tests were wrong at first. The double-post test expected one
    message where a real double click shows two. The history-order test
    patched `timezone.now`, but the model default had already captured the
    real function; the helper now sets `created_at` explicitly.
  - TDD test 2 first failed with `DoesNotExist` rather than an assertion,
    so an explicit count assertion was added before the `.get()`.
  - A bash heredoc failed on quoting while appending tests; the file was
    edited with the editor tool instead.

## 2026-11-18 — Polish: demo product photos, README sign-ins

### Prompts

1. "I am essentiallypolishing up some of what is already here can we get some
   images for my products these can really be anything as long as they are
   decent images that are CC0 or CC By or some free use derivative to act as
   a placeholder. Next can we update the README to include the new demo
   sign-ins append this session to PROMPTS.md as well"

### Summary

- **Outcome:** all 16 demo products have an openly licensed placeholder
  photo (13 distinct images; the four hoodie sizes share one), attached by
  `seed_demo`. The README lists the demo sign-ins and shows the current
  state of the app. 160 tests pass with 100% line coverage; `ruff check`
  and `ruff format --check` are clean. Not committed.
- **Changes:**
  - `demo/images/`: new. 13 JPEGs at 800 × 600 (about 880 KB in total) and
    `CREDITS.md`, with title, author, license and source link for each, and
    the changes made (cropped and resized). Six are CC0 and seven are
    CC BY 2.0.
  - `demo/seed.py`: every `DemoProduct` now requires an `image` and
    `alt_text` describing the photo. A product with no image, or whose file
    is missing from `media/`, gets its photo under a random name; an
    existing image is never replaced. The report counts photos attached.
  - `demo/management/commands/seed_demo.py`: prints "Product photos: N
    attached".
  - `conftest.py`: new. Every test stores media in a temporary folder.
  - `demo/tests/test_seed_demo.py`: photos are attached with alt text and
    random names, a rerun attaches nothing new, an existing image is kept, a
    missing file is replaced, and every photo is a valid JPEG at most 800 px
    wide that is credited in `CREDITS.md`.
  - `README.md`: a demo sign-ins table (role, email, password, what each
    can do) with a dev-only warning, the status updated to Phases 1–3,
    `seed_demo` as a setup step, browser checks for the catalog,
    dashboard and access refusals, and an image credits link.
  - `docs/images/home.jpg` replaces the outdated Phase 1 `home.png`, and
    `docs/images/dashboard-products.png` is new.
  - Docs: `docs/{architecture,frontend,testing,workflow}.md` describe the
    demo photos, their rules and the test media folder.
- **TDD:** none. This was seed data, images and documentation. The seed
  behaviour got ordinary tests.
- **Decisions:**
  - Photos are stored in the repo and attached by `seed_demo`, not uploaded
    by hand, so a fresh clone gets them. They are resized before
    committing, following the PRD's 800 px rule.
  - Photos were found through Openverse with the license filter set to
    CC0, public-domain mark and CC BY, and inspected on contact sheets.
    Rejected: photos with faces, other brands' logos (most hoodie results),
    and one with a knife beside the water bottle.
  - The hoodie photo is a CC0 shot of a red hoodie seen from behind,
    cropped. No product-style hoodie photo without branding was found on
    Openverse or Wikimedia Commons.
  - The safety goggles show the maker's small "uvex" mark, kept as normal
    for a product photo.
  - The README's home screenshot was replaced because it still showed the
    Phase 1 page; it is a JPEG because a PNG of the photos was 600 KB.
- **Deviations:** none. No follow-up questions were asked.
- **Sideways:**
  - The first `CREDITS.md` was written by a shell heredoc that ran the
    Markdown backticks as commands, blanking the file names. Caught by
    reading the output and regenerated with a quoted heredoc.
  - The first goggles crop cut the glasses out of the frame. Caught on the
    contact sheet and recropped.
  - One new test had an assertion that could never fail. It was rewritten
    to compare the stored image name before and after the rerun.
  - `static/css/site.css` showed as modified from an earlier
    `tailwind runserver` (an unminified watcher build). `tailwind build`
    restored it to the committed version.

## 2026-11-18 — Buff Shop: Phase 3/18, Dashboard shell and access control

### Prompts

1. The `/implement` skill, given `buff-shop.md phase 3`.
2. Approved the brief with adjustments: (1) the access test must cover more
   than GET and POST: detect other supported methods and make sure every
   method is protected, never assuming GET protection covers POST; (2)
   `/admin/` must refuse staff and customers on the server, keep normal
   admin for the superuser, and not break the Category and Product
   registrations; (3) keep the badge wording Out of Stock / Low Stock /
   In Stock, with Out of Stock counting toward the low-stock alert total
   while staying a separate status; (4) every new dashboard URL must have a
   URL name, a registered fixture for its parameters, an expected HTTP
   method and a staff authorisation test.
3. Approved RED 1, asking that OPTIONS and TRACE be handled carefully: if
   they can't reliably produce the login redirect, test that they are
   refused rather than weakening the requirement.
4. Approved RED 2, asking that the customer be created with
   `is_staff=False` and `is_superuser=False` explicitly.
5. Approved RED 3 and the recommendation to broaden tests 1 and 2: routes
   with no parameters are tested directly even if unregistered, routes with
   parameters must be registered, an unbuildable route is never silently
   skipped, and discovery must follow nested URL files recursively.

### Summary

- **Outcome:** staff get a `/dashboard/` home and a product list of every
  product with "In Stock" / "Low Stock" / "Out of Stock" and "Inactive"
  badges (icon plus words). One staff check guards the dashboard, `/admin/`
  is superuser-only, and a persistent access test walks every dashboard
  route with all eight HTTP methods. 155 tests pass with 100% line coverage;
  `ruff check` and `ruff format --check` are clean.
- **Changes:**
  - `dashboard/`: new app. `access.py` (`StaffRequiredMixin`,
    `SuperuserRequiredMixin`), `views.py` (home and product list, 25 per
    page, all products), `urls.py`.
  - `dashboard/tests/`: `walk.py` (route discovery, walk planning and the
    request checks), `routes.py` (the registry each new route must join),
    `test_access.py` (the persistent access test), `test_walk.py` and
    `walk_fixture_urls.py` (tests of the walk itself), `test_pages.py`.
  - `config/admin.py`, `config/apps.py`: new. A superuser-only admin site
    and login form, installed as the default `admin.site`;
    `config/settings/base.py` uses it in place of `django.contrib.admin` and
    adds the `dashboard` app. `config/urls.py` includes `/dashboard/`.
  - `config/tests/test_admin_site.py`: new. Anonymous, customer and staff
    refusal (pages, a data change, the admin login form) and full superuser
    access.
  - `accounts/tests/factories.py`: `UserFactory` sets `is_staff` and
    `is_superuser` to False explicitly.
  - Templates: `templates/dashboard/{base,home,product_list,_product_badges}.html`,
    `templates/403.html` ("Access denied"), a staff-only "Dashboard" link
    in `templates/base.html`, and icons `gauge`, `boxes-stacked`, `ban`.
  - `tailwind/source.css`: a `dash-link` utility. `static/css/site.css`
    rebuilt (it was an unminified watcher build before the phase).
  - Docs: `docs/{architecture,business-rules,frontend,testing}.md` and
    `CLAUDE.md`. The Phase 3 acceptance criteria are ticked in the plan.
- **TDD:**
  - `test_dashboard_routes_redirect_anonymous_to_login`: RED on an
    assertion (16 requests let through), then GREEN with the mixin.
  - `test_dashboard_routes_forbid_customers` and
    `test_every_dashboard_route_is_walkable` passed on first run, because
    the earlier GREEN or the correct registry already satisfied them. Each
    was shown failing on its assertion against a deliberate break (a check
    weakened to "logged in is enough"; two temporary bad routes), then
    restored.
- **Decisions:**
  - The staff check is a `UserPassesTestMixin` subclass placed first in
    each view's bases, so it runs in `dispatch()` for every method before
    any lookup.
  - Discovery covers the `dashboard` namespace and any route whose path
    starts with `dashboard/`.
  - The registry records methods, sample kwargs and `superuser_only`. The
    test finds routes on its own; the registry is a checklist it enforces,
    which is how the plan's "no hand-maintained list" criterion is met.
  - `/admin/` uses Django's documented custom-default-site pattern, and
    its login form also refuses non-superusers.
  - Staff product list: 25 per page, sorted by name, with columns Product,
    Status, Stock, Low-stock threshold, Price, Category in a scrollable
    region.
  - `seed_demo` needed no change: it already has inactive, low-stock and
    out-of-stock products, now checked by a dashboard test.
- **Deviations:**
  - The user's adjustments were all built: all eight methods walked;
    admin refusal tested for every role including form posts and login;
    the registry requirements; the explicit customer flags; broader
    tests 1 and 2 and the nested-include self-test.
  - OPTIONS and TRACE needed no special handling: they go through
    `dispatch()`, so they get the same login redirect and 403.
- **Sideways:**
  - The RED 3 demonstration showed that tests 1 and 2 skipped an
    unregistered, unguarded route, and only test 3 caught it. Raised with
    the user and fixed by broadening the walk; the same bad routes then
    failed all three tests.
  - The fake URL setup for the walk self-tests lacked the catalog URLs,
    which the new 403 page links to. One self-test errored until they were
    added.
  - Screenshots at 1280 px and 360 px showed the threshold note wrapping
    and the Status column scrolled off-screen on a phone. The threshold got
    its own column and Status moved next to the product name.

## 2026-11-18 — Buff Shop: Phase 2/18, Read-only catalog and first `seed_demo`

### Prompts

1. The `/implement` skill, given `buff-shop.md phase 2`.
2. Approved the brief with four adjustments: (1) safe `seed_demo` credentials:
   print passwords only in development, clearly documented dev-only
   credentials, never overwrite an existing superuser's password, refuse
   unless the seed environment is explicitly allowed, independent of
   `DEBUG`; (2) stronger idempotency: never reactivate an inactive product,
   never overwrite stock, never overwrite passwords except designated demo
   accounts; (3) image handling: validate formats, a maximum upload size, a
   safe generated filename, uploads kept apart from static assets (resizing
   can wait); (4) pagination edge-case tests: exactly 12 is one page, 13 is
   two, inactive products don't affect pagination, out-of-stock products
   stay visible, sorting is consistent between pages. Also: "for TDD phases
   this point going forward only stop at red and continue past to green when
   red has been checked over."
3. Approved the first RED test, recommending that `stock_status()` return a
   structured result with a stable identifier (`out_of_stock`, `low_stock`,
   `in_stock`) alongside the label.
4. Approved the second RED test, asking for a safeguard that the catalog
   view actually uses `Product.objects.active()` and doesn't filter on its
   own.

### Summary

- **Outcome:** the catalog at `/` lists active products sorted by name, 12
  per page, with image or placeholder, category, price and a stock badge (an
  icon plus the words). Categories are seeded by a data migration and
  editable in `/admin/`. `seed_demo` creates 5 demo accounts and 16 products
  (15 active, some low or out of stock, plus 1 inactive). 105 tests pass,
  with 100% line coverage. `ruff check` and `ruff format --check` are clean.
- **Changes:**
  - `catalog/models.py`: Category, Product (with a `stock >= 0` CHECK
    constraint), `StockStatus` and `stock_status()`, and the
    `Product.objects.active()` helper. The alt text defaults to the title.
  - `catalog/images.py`: new. A Pillow-based format check (JPEG/PNG/WebP), a
    5 MB limit, and random storage names whose extension comes from the
    detected format.
  - `catalog/migrations/0001_initial.py`, `0002_seed_categories.py`: new.
  - `catalog/views.py`, `catalog/urls.py`: `ProductListView` replaces the
    placeholder home page.
  - `catalog/admin.py`: new. Category and Product are registered, with
    product stock read-only.
  - `templates/catalog/index.html`, `templates/catalog/_stock_status.html`:
    the catalog grid, pagination and the stock badge.
  - `templates/icons/{triangle-exclamation,circle-xmark,chevron-left,chevron-right}.svg`
    and `static/img/product-placeholder.svg`: new.
  - `demo/`: a new app. `seed.py` holds the data and the rules for
    protecting existing data, and `management/commands/seed_demo.py` is the
    command.
  - `config/settings/base.py`, `dev.py`: `MEDIA_ROOT`/`MEDIA_URL`, the
    `demo` app, and `ALLOW_DEMO_SEED` (True only in dev).
    `config/urls.py` serves media in dev.
  - `pyproject.toml`, `uv.lock`: Pillow, needed by `ImageField`.
  - `tailwind/source.css`, `static/css/site.css`: `warning` colour tokens
    and a rebuild (the stylesheet was an unminified watcher build before the
    phase).
  - Tests: `catalog/tests/{factories,test_stock_status,test_active_products,test_models,test_images,test_catalog_view,test_admin}.py`
    and `demo/tests/test_seed_demo.py`.
  - Docs: `docs/{architecture,business-rules,frontend,testing,workflow}.md`
    and `CLAUDE.md`, updated with the new helpers, URLs, settings and demo
    logins. The Phase 2 acceptance criteria are ticked in the plan.
- **TDD:**
  - `test_stock_status_boundaries`: the 0, 1, 5 and 6 boundaries with
    threshold 5, and 0 and 1 with threshold 0.
  - `test_active_products_excludes_inactive`.

  Both were RED on an assertion against stubs, then GREEN.
- **Decisions:**
  - `seed_demo` lives in a new model-less `demo` app.
  - The production guard is an explicit `ALLOW_DEMO_SEED` setting, not
    `DEBUG`, and a subprocess test runs the command under the real prod
    settings.
  - Demo products are created only if missing.
  - The superuser's password is printed on later runs only while it still
    matches the demo one. This is checked read-only with `check_password`.
  - The placeholder alt text is "No photo available".
  - A page number past the end gives a 404.
  - Product stock is read-only in Django admin.
- **Deviations:**
  - The user's four adjustments (see prompt 2) were all built. Image format
    and size validation were pulled forward from Phase 13 and tested
    normally, not with TDD.
  - A separate test pins the stable `StockStatus` identifiers, as the user
    recommended. The approved TDD test was left unchanged.
  - A behavioural test swaps in a different `active()` and checks that the
    catalog shows exactly what it returns. If the view filtered products on
    its own, it would fail.
  - The user's new rule, stop only at RED in TDD, was saved as a standing
    preference.
- **Sideways:**
  - The first version of the "status is text plus icon" test split the HTML
    on `<p` and matched the icon's `<path`. It was replaced with a regex.
  - Headless Firefox couldn't take screenshots while the user's own Firefox
    was open. A separate throwaway profile was used instead.

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
