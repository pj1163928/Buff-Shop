# Plan: Buff Shop Ordering Web App

> Source PRD: [prd/buff-shop.md](../prd/buff-shop.md). User story numbers below refer to that file.

## Architectural decisions

Durable decisions that apply across all phases.

### Database and transactions

- **The target database is SQLite**, as the brief requires, in development, the demo and the written production settings. There is no PostgreSQL path.
- SQLite ignores `select_for_update()`, so nothing relies on it.
- Django's SQLite `transaction_mode = "IMMEDIATE"` and a busy timeout make a write transaction take the write lock when it starts, so concurrent writers wait in line. This is a SQLite-only option. Confirm the Django version requirement during Phase 1 research.
- Stock has two independent safeguards, and each must hold on its own:
  1. the single conditional UPDATE in the stock helper, which only applies when the result stays at zero or above and checks the rows changed
  2. a database `CHECK (stock >= 0)` constraint
- Status changes also use a conditional UPDATE on the current status (for example "set Picked Up where status is Ready"). Two people acting on the same order at once can't both succeed.

### URLs

All URLs are named and app-namespaced. Products are addressed by numeric ID. Orders are addressed by order number.

| Area | Paths |
|---|---|
| Catalog (`catalog:`) | `/` (list, search and filter) |
| Accounts (`accounts:`) | `/accounts/signup/`, `/accounts/login/`, `/accounts/logout/`, `/accounts/profile/`, `/accounts/password/change/`, `/accounts/password/reset/…` (Django's flow) |
| Cart (`cart:`) | `/cart/`, `/cart/add/<product_id>/`, `/cart/lines/<product_id>/` (htmx quantity update) |
| Orders (`orders:`) | `/orders/` (history), `/orders/place/` (POST), `/orders/<order_number>/`, `/orders/<order_number>/cancel/`, `/orders/<order_number>/qr/` |
| Dashboard (`dashboard:`) | everything under `/dashboard/`: `products/`, `products/new/`, `products/<id>/edit/`, `products/<id>/stock/`, `orders/`, `orders/<order_number>/` and its actions, `pickup/`, `customers/`, `customers/<id>/…`, `staff/`, `alerts/…`, `analytics/` |
| Django admin | `/admin/`, superuser only |

### Models and owning apps

| App | Models | Notes |
|---|---|---|
| accounts | **User** (custom, email is the unique login field, first and last name required, no username), **AccountStatusChange** (user, disabled/enabled, reason, by, at) | The User model exists before the first migration |
| catalog | **Category** (name; seeded with Textbook, Merchandise, Lab Kit), **Product** (title, category FK, description, price, optional image, alt text, stock, low-stock threshold default 5, is_active) | Shared active-products helper lives here |
| stock | **StockMovement** (product, change, resulting stock, kind: checkout/cancel/receive/adjust, order FK nullable, user, time, reason) | The one safe stock helper lives here |
| cart | **Cart** (one per user), **CartLine** (cart, product, quantity; unique per cart and product) | No stock reserved |
| orders | **Order** (order number, user, status, pickup code, placed at, cancellation reason/source, checkout submission token), **OrderLine** (order, product, snapshot name, snapshot unit price, quantity), **OrderStatusChange** (order, old status, new status, by, at, reason, is_override), **OrderNumberSequence** (year, last number) | Transition table lives here |
| dashboard | **AlertState** (one per staff user: snoozed until, dismissed at, counts at dismissal) | Every staff view; the one staff-only access check |

### Uniqueness and identifiers

- **Order number** `BUF-<year>-<5-digit sequence>` has a database unique constraint. The per-year sequence is advanced inside the checkout transaction.
- **Pickup code**: 6 characters from an alphabet without look-alikes (no 0/O, 1/I), generated with Python's `secrets` module. It is not derived from the order number. It has a database unique constraint. On the very unlikely collision, generation retries with a new code.
- **Checkout submission token** has a database unique constraint, so a repeated submit can't create a second order.

### Auth and access

- `is_staff` means shop staff and reaches `/dashboard/`. `is_superuser` alone reaches overrides, staff management and `/admin/`.
- Every dashboard view and action goes through one staff-only check. Anonymous users are redirected to log in, and logged-in customers get 403. Superuser-only dashboard routes also refuse plain staff with 403.
- Customer order lookups are always scoped to the current user. Another user's order gives a 404.
- Lockout uses `django-axes`, keyed on email only.

### Statuses

- Placed, Preparing, Ready for Pick Up, Picked Up and Cancelled.
- One transition table lists every allowed move and its actor.
- **Picked Up is reached only through pickup verification.** It is final in the normal flow: no staff undo, no staff or customer cancel, and no stock restore. The only exception is the logged superuser override.

---

## Rules for every phase (definition of done)

These apply to every phase. A phase isn't finished until all of them hold.

- [ ] **`seed_demo` is updated** whenever the phase adds functionality, so the new feature can be demonstrated straight after running it. It stays idempotent and still refuses to run under production settings.
- [ ] **Every new `/dashboard/` route is covered by the access-control test**, which walks every dashboard URL automatically (Phase 3). If a new route can't be walked automatically, for example because it needs URL arguments the test doesn't know, the test fails until the route is registered with it. Superuser-only routes are also checked against plain staff.
- [ ] Critical rules touched by the phase have dedicated tests (see [docs/testing.md](../docs/testing.md)), whatever the overall coverage.
- [ ] `pytest` passes, and `ruff check .` and `ruff format --check .` are clean.
- [ ] New pages meet the accessibility basics: labelled fields, visible focus, status in text and not by colour alone, htmx regions as live regions, and a usable layout at 360 px.

---

## Phase 1: Project skeleton and email sign-up/login

**User stories**: 1, 2, 3, 4, 5

### What to build

Set up the project and deliver the first working path. A visitor can sign up with first name, last name, email and password, then log in and out with their email. "Remember me" keeps them logged in for two weeks; otherwise the session ends when the browser closes. This phase also lays the foundations every later phase needs:

- git
- dev and production settings
- the custom User model before the first migration
- SQLite IMMEDIATE transactions with a busy timeout
- the Tailwind standalone build and an accessible base layout
- pytest, coverage and ruff
- the console email backend

### Acceptance criteria

- [x] The project is a git repository, and the custom User model is in the first migration.
- [x] Sign-up requires all four fields and applies Django's four default password validators with readable messages.
- [x] Login uses email. A failed login shows one generic error whether or not the email exists.
- [x] Without "Remember me" the session expires at browser close; with it, the session lasts two weeks.
- [x] Dev settings use SQLite with `transaction_mode="IMMEDIATE"` and a busy timeout.
- [x] Production settings read secrets from environment variables, and `manage.py check --deploy` passes under them.
- [x] The Tailwind stylesheet is built by the standalone CLI and committed. The build command is recorded in `CLAUDE.md`.
- [x] The base layout has a skip link, visible focus styles, and works at 360 px.

### TDD

**Recommendation:** no TDD. This phase is setup and configuration. Sign-up, login and session expiry use Django's built-in auth, whose behaviour is already settled, so normal view tests cover them.

---

## Phase 2: Read-only catalog and first `seed_demo`

**User stories**: 13, 14, 19, 20, 21, 22 (catalog), 86, 87 and 88 (first version)

### What to build

Customers see the catalog at `/`. It lists active products sorted by name, 12 per page, with name, category, price, image (or a placeholder) and stock status in words. Categories are seeded by a data migration and editable in `/admin/`. The shared active-products helper is introduced here. The first `seed_demo` creates the superuser, a staff account, a few customers and about 15 products, including some low-stock and out-of-stock ones.

### Acceptance criteria

- [ ] Stock status reads "Out of Stock" at 0, "Low Stock — act soon" at or below the product's own threshold, and "In Stock" above it. It is shown in text, not only colour.
- [ ] Out-of-stock products appear. Inactive products never appear, and the catalog query goes through the active-products helper.
- [ ] Products without an image show a placeholder with sensible alt text.
- [ ] Pagination is 12 per page, sorted by name.
- [ ] A database constraint keeps `stock >= 0`.
- [ ] `seed_demo` can be run twice without duplicating data, refuses to run under production settings, and prints the demo logins.

### TDD

**Recommendation:** TDD for the two behaviours below. Everything else in this phase gets normal tests.

1. **Stock status at the threshold boundaries.** One rule drives the customer label, the staff badge, the alert count and the analytics list, and an off-by-one error here would be wrong everywhere.
   - `test_stock_status_boundaries`: with threshold 5, stock 0 is "Out of Stock", stock 1 and 5 are "Low Stock — act soon", and stock 6 is "In Stock". With threshold 0, stock 0 is "Out of Stock" and stock 1 is "In Stock".
2. **The active-products helper hides inactive products.** Every customer-facing query depends on it, so it must be right before anything is built on it.
   - `test_active_products_excludes_inactive`: an active product, an inactive product and an active out-of-stock product exist. The helper returns the two active ones, including the out-of-stock one.

---

## Phase 3: Dashboard shell and access control (TDD)

**User stories**: 41, 42, 43, 53, 55

### What to build

Staff get a `/dashboard/` home and a product list showing every product. Inactive products are labelled "Inactive", and products at or below their threshold get a "Low Stock" badge that can't be silenced. One staff-only check guards the whole dashboard, and `/admin/` is limited to the superuser.

The access-control test is built first, with TDD, and is **persistent**. It discovers every route in the `dashboard` namespace from Django's URL resolver, so routes added in later phases are checked automatically. It fails if it finds a route it can't build a URL for. Each route is requested as an anonymous user (redirected to login) and as a customer (403), for both GET and POST. Superuser-only routes are also requested as plain staff (403).

### Acceptance criteria

- [ ] The access test discovers dashboard routes automatically, with no hand-maintained list of routes.
- [ ] The access test fails when a new dashboard route can't be walked, so a route can't go untested.
- [ ] Anonymous users are redirected to login, and customers get 403, on every dashboard route and method.
- [ ] `/admin/` refuses plain staff and admits the superuser.
- [ ] The staff product list shows "Inactive" and "Low Stock" badges in text.
- [ ] `seed_demo` includes inactive and low-stock products to show the badges.

### TDD

**Recommendation:** TDD for the three behaviours below. Everything else in this phase gets normal tests.

1. **Anonymous users are refused on every dashboard route.** This is the main guard on staff functions, and the PRD requires it to be built test-first.
   - `test_dashboard_routes_redirect_anonymous_to_login`: for every route discovered in the `dashboard` namespace, GET and POST from an anonymous user redirect to the login page.
2. **Customers are refused on every dashboard route.** Being logged in must not be enough.
   - `test_dashboard_routes_forbid_customers`: for every discovered route, GET and POST from a logged-in customer return 403.
3. **No dashboard route escapes the walk.** This is what keeps the test persistent as later phases add pages.
   - `test_every_dashboard_route_is_walkable`: every discovered route that needs URL arguments has sample arguments registered. The test lists any route that doesn't and fails.

---

## Phase 4: Safe stock helper, Receive Stock and Stock Adjustment (TDD)

**User stories**: 49, 50, 51

### What to build

The one stock helper is built with TDD on SQLite. It runs inside an IMMEDIATE transaction, applies a single conditional UPDATE that only succeeds if stock stays at zero or above, checks the rows changed, and writes a StockMovement row. Staff use it from a product's stock page:

- **Receive Stock** takes a positive amount.
- **Stock Adjustment** takes a positive or negative amount and needs a reason.

The same page shows the product's full stock history.

### Acceptance criteria

- [ ] The helper refuses any change that would take stock below zero and reports the failure. Stock is unchanged.
- [ ] The CHECK constraint independently rejects a negative stock written without the helper. This is tested on its own.
- [ ] Every successful change writes exactly one history row with change, resulting stock, kind, user, time and reason.
- [ ] Receive Stock rejects zero and negative amounts. Stock Adjustment rejects a missing reason.
- [ ] The stock history page lists movements newest first, with who, when, kind and reason.
- [ ] `seed_demo` creates some receive and adjust history.

### TDD

**Recommendation:** TDD for the three behaviours below. Everything else in this phase gets normal tests.

1. **The helper refuses any change that would make stock negative.** This is the core stock-integrity rule.
   - `test_stock_change_refused_when_result_would_be_negative`: with stock 2, a change of −3 is reported as failed. Stock stays 2, and no history row is written.
2. **Every successful change writes exactly one history row.** Without it, staff can't explain a count.
   - `test_stock_change_records_history`: with stock 2, a staff member receives +5. Stock is 7, and exactly one history row records change +5, resulting stock 7, kind "receive", the user and the time.
3. **The database rejects negative stock on its own.** This is the second, independent safeguard.
   - `test_database_rejects_negative_stock`: setting a product's stock to −1 directly, bypassing the helper, raises an integrity error.

---

## Phase 5: Cart

**User stories**: 22 (cart), 23, 24, 25, 26

### What to build

Logged-in customers add products to a database cart from the catalog. On the cart page they change quantities through htmx and see line and cart totals update without a reload. The server caps each quantity at current stock. Inactive products are dropped from the cart view. Anonymous users are sent to login.

### Acceptance criteria

- [ ] The cart persists per user across sessions and devices.
- [ ] Quantity updates return updated totals in a live region. A quantity above stock is capped, and the customer is told.
- [ ] Inactive products don't show in the cart or count toward the total.
- [ ] Cart pages require login, and there is no guest cart.
- [ ] Quantity changes work without JavaScript through a normal form submit.
- [ ] `seed_demo` gives one demo customer a filled cart.

### TDD

**Recommendation:** TDD for the two behaviours below. Everything else in this phase gets normal tests.

1. **The server caps cart quantity at current stock.** It stops customers building an order that can't be filled, whatever the browser sends.
   - `test_cart_quantity_capped_at_stock`: with stock 3, posting quantity 10 saves quantity 3, and the response tells the customer it was capped.
2. **Inactive products are dropped from the cart.** A discontinued product must not be orderable or counted.
   - `test_cart_total_ignores_inactive_products`: a cart holds one active and one inactive product. Only the active one is shown, and the total counts only that one.

---

## Phase 6: Checkout

**User stories**: 27, 28, 29, 30, 31, 32

### What to build

"Place Order (Pay at Pickup)" on the cart page creates the order in one database transaction. It tries every line through the stock helper and collects every short item. If any item is short, everything rolls back, the cart is left as it was, and the customer sees every short item by name. On success:

- order lines snapshot the product name and unit price
- the order gets a unique order number and a securely generated unique pickup code
- the cart is emptied
- the customer lands on a confirmation page with the order number, the pickup code (`K7F-29Q`) and its QR code

Double submits are blocked in the browser (the button is disabled) and on the server (a unique submission token).

### Acceptance criteria

- [ ] Order number and pickup code each have a database unique constraint.
- [ ] Pickup codes come from the `secrets` module and the no-look-alike alphabet. A forced collision in a test causes a retry, not an error.
- [ ] When any item is short, nothing is deducted, the cart is unchanged, and every short item is named.
- [ ] A successful checkout deducts stock, writes one checkout stock movement per line, and empties the cart.
- [ ] Changing a product's price after ordering doesn't change the order total.
- [ ] Submitting the same checkout twice creates one order. The second submit lands on the existing confirmation.
- [ ] **Concurrency test:** two simultaneous checkouts for the last unit, on SQLite with real separate connections or threads; exactly one succeeds.
- [ ] `seed_demo` creates a few Placed orders.

### TDD

**Recommendation:** TDD for the three behaviours below. Everything else in this phase gets normal tests.

1. **A checkout with any short item changes nothing and names every short item.** This is the all-or-nothing rule at the heart of FR-C2.
   - `test_checkout_with_short_items_changes_nothing`: a cart holds A (enough stock), B (short) and C (short). No order is created. A, B and C stock is unchanged, with no stock movements. The cart is unchanged. The response names both B and C.
2. **A repeated submission creates one order.** Duplicate orders would mean duplicate stock deductions.
   - `test_repeated_submission_creates_one_order`: posting the same checkout submission twice creates one order and one set of deductions. The second post lands on the same confirmation page.
3. **Pickup codes are unique, use the safe alphabet, and retry on collision.** Pickup verification depends on one code matching exactly one order.
   - `test_pickup_code_retries_on_collision`: the code source is made to return an existing order's code first. The new order gets a different code, 6 characters long, with no 0, O, 1 or I.

Normal tests (not TDD) still cover the required concurrency test, price snapshots and the order-number format.

---

## Phase 7: Order history and customer cancel

**User stories**: 34, 35, 38, 39 (customer), 40

### What to build

Customers see their order history with date, items, total and status. Each order page shows the pickup code and a QR code sized to scan from a phone, plus the order's status history. The transition table and the OrderStatusChange log are introduced here with TDD. The first moves are Placed → Cancelled by the customer, which restores stock through the helper and shows "Cancelled by customer".

### Acceptance criteria

- [ ] The transition table is the single source of allowed moves and actors. A table-driven test covers every allowed and disallowed pair for every actor.
- [ ] A customer can cancel only while the order is Placed. Stock is restored, with a cancel stock movement.
- [ ] Every status change writes one OrderStatusChange row with who, when, old status, new status and reason.
- [ ] Requesting another user's order, its QR or its cancel action returns 404.
- [ ] `seed_demo` includes a customer-cancelled order.

### TDD

**Recommendation:** TDD for the three behaviours below. Everything else in this phase gets normal tests.

1. **The transition table allows exactly the agreed moves for each actor.** Every later status feature relies on it, and the PRD requires it test-first.
   - `test_transition_table`: parametrised over every (from status, to status, actor) combination. Allowed moves succeed and all others are refused. No actor reaches Picked Up through an ordinary transition.
2. **Every status change writes one history row.** This is the audit trail for orders.
   - `test_status_change_writes_history`: a customer cancels a Placed order. Exactly one history row records the customer, the time, Placed → Cancelled, and the reason "Cancelled by customer".
3. **Customer cancel restores stock.** Otherwise cancelled items could never be sold again.
   - `test_customer_cancel_restores_stock`: an order holds 2 units of a product. After cancelling, stock rises by 2, and there is exactly one "cancel" stock movement linked to the order.

---

## Phase 8: Staff order management

**User stories**: 39 (store), 56, 57, 58, 59, 61, 62

### What to build

Staff see all orders at `/dashboard/orders/`, filterable by status. The dashboard menu shows "Orders (N)" for orders in Placed. An order's dashboard page shows the customer, lines, total and current status, with these actions:

- one button that moves the order to its next status (Placed → Preparing → Ready for Pick Up)
- an undo button that steps back one status
- cancel, for any order before Picked Up. Staff cancel needs a reason and restores stock, and the customer sees "Cancelled by store: <reason>".

Every action goes through the transition table, so each change still writes its OrderStatusChange row (from Phase 7). This phase is only about state changes. Displaying the history and sending email come in Phase 9.

### Acceptance criteria

- [ ] The status filter and the "Orders (N)" count are correct for each status.
- [ ] Advance and undo follow the transition table. No button offers Picked Up, and moves the table doesn't allow are refused on the server.
- [ ] Staff cancel needs a reason, is refused once the order is Picked Up, and restores stock with a cancel movement.
- [ ] The customer's order page shows "Cancelled by store: <reason>".
- [ ] Each action writes exactly one OrderStatusChange row.
- [ ] New dashboard routes pass the persistent access test.
- [ ] `seed_demo` has orders in Placed, Preparing, Ready and store-cancelled.

### TDD

**Recommendation:** TDD for the two behaviours below. Everything else in this phase gets normal tests.

1. **Staff cancel needs a reason.** The customer sees it, and an unexplained cancellation is the failure the PRD guards against.
   - `test_staff_cancel_requires_reason`: a cancel with an empty reason is refused, and status and stock are unchanged. With a reason, the order is Cancelled, stock is restored, and the customer's order page shows "Cancelled by store: <reason>".
2. **A stale status change is refused.** Two staff clicking "next" on the same order must not skip a status.
   - `test_stale_status_change_is_refused`: two advance requests are both made while the order is Placed. The order ends in Preparing (not Ready), there is one history row, and the second request gets a "this order has changed" message.

---

## Phase 9: Staff order history and Ready email

**User stories**: 36, 37, 63, 89

### What to build

The staff order page shows the order's complete status history: every change, with who, when, old status, new status and reason, newest first.

When an order enters Ready for Pick Up, the customer gets an email with the order number and never the pickup code. It prints to the console in development and the demo. Sending happens after the status change is saved. A failed send is caught and logged, and never blocks or undoes the change. A Ready → Preparing → Ready bounce doesn't need special handling; the email is simply sent again.

### Acceptance criteria

- [ ] The staff order page lists every status change, including cancellations, with actor, time and reason.
- [ ] Entering Ready sends one email, visible in the console, containing the order number.
- [ ] A test asserts that the email does not contain the pickup code in any form (with or without the hyphen).
- [ ] A simulated email failure leaves the order in Ready, writes a log entry without the pickup code, and shows staff no error page.
- [ ] Moves to any other status send no email.
- [ ] `seed_demo` orders have realistic multi-step histories.

### TDD

**Recommendation:** TDD for the two behaviours below. Everything else in this phase gets normal tests.

1. **The Ready email never contains the pickup code.** Leaking the code would let anyone who reads the email collect the order.
   - `test_ready_email_never_contains_pickup_code`: moving an order to Ready sends one email containing the order number. Its subject and body contain the pickup code neither with nor without the hyphen.
2. **An email failure doesn't block the status change.** Order state must not depend on a mail server.
   - `test_email_failure_does_not_block_ready`: with the mail backend made to fail, the order still ends in Ready with its history row. An error is logged, and the log doesn't contain the pickup code.

---

## Phase 10: Pickup verification by typed code (TDD)

**User stories**: 60, 65, 66, 67, 68

### What to build

Staff open `/dashboard/pickup/` and type a code. Case and hyphen are ignored. A code matching a Ready order shows the customer's name and items, with a "Confirm Handover" button. Confirming moves the order to Picked Up through a conditional status update and logs who did it. **Handover is irreversible in the normal flow**: a Picked Up order can't be confirmed again, undone, or cancelled by staff or the customer, and its stock is never restored. The only exception is the logged superuser override (Phase 17).

### Acceptance criteria

- [ ] The correct code on a Ready order shows the preview, and confirming moves it to Picked Up with a history row.
- [ ] A wrong code shows "not found". A Picked Up order's code shows "already used". A Cancelled order's code shows "cancelled". A Placed or Preparing order's code is rejected as not ready.
- [ ] Codes are normalised: `k7f29q`, `K7F-29Q` and ` k7f-29q ` all match.
- [ ] **Repeated confirmation:** posting Confirm Handover twice, or from two sessions at once, leaves one Picked Up change, with no second history row and no error page.
- [ ] Staff cancel, customer cancel and staff undo on a Picked Up order are all refused, and stock is unchanged.
- [ ] The results area is a live region.
- [ ] `seed_demo` includes a Ready order with a known code for the demo, plus a Picked Up order.

### TDD

**Recommendation:** TDD for the three behaviours below. Everything else in this phase gets normal tests.

1. **A typed code is normalised and matches a Ready order.** This is the happy path of FR-A2, and the PRD requires it test-first.
   - `test_typed_code_matches_ready_order`: for a Ready order with code `K7F-29Q`, the inputs `K7F-29Q`, `k7f29q` and ` k7f-29q ` all show that order's customer name and items.
2. **Each non-matching case is rejected with the right message.** Staff must know why a code failed.
   - `test_code_rejection_messages`, parametrised: an unknown code shows "not found", a Picked Up order's code shows "already used", a Cancelled order's code shows "cancelled", and a Placed or Preparing order's code shows "not ready yet". No order changes status.
3. **Handover can't be confirmed twice.** Handover is irreversible and must be recorded once.
   - `test_confirm_handover_twice_records_one_pickup`: Confirm Handover is posted twice for the same order. It ends Picked Up with exactly one Ready → Picked Up history row, naming the staff member, and the second post shows "already used".

---

## Phase 11: Authentication security and account management

**User stories**: 6, 7, 8, 9, 10, 11

### What to build

Complete the account layer started in Phase 1:

- **Lockout.** `django-axes` locks an account for 15 minutes after 5 failed logins. It is keyed on the submitted email, not the IP address. The locked-out message says to try again in 15 minutes, and errors never reveal whether an email exists.
- **Profile.** Customers edit their first and last name at `/accounts/profile/`.
- **Password change.** It applies the four default validators. The current session stays logged in, and the user's other sessions are ended.
- **Password reset.** Django's built-in flow by email, printed to the console. A completed reset ends all of the user's existing sessions and clears any lockout on that email.

Session invalidation is built on Django's session-hash check, so changing the password is what ends the other sessions.

### Acceptance criteria

- [ ] 5 failures lock that email for 15 minutes. A different email from the same IP is unaffected.
- [ ] The lockout clears after 15 minutes, tested with a controllable clock.
- [ ] The error for an unknown email is identical to the error for a wrong password. A reset request for an unknown email shows the same message as for a known one.
- [ ] Name changes save, and both names stay required.
- [ ] After a password change, the session that made the change stays logged in, and a second session for the same user is logged out.
- [ ] The reset email appears in the console and its link works only once. After the reset, old sessions are logged out and the email is no longer locked.
- [ ] Axes is configured for the email login field. Research findings are recorded before building.
- [ ] `seed_demo` documents a customer to use for the lockout and reset demos.

### TDD

**Recommendation:** TDD for the two behaviours below. Everything else in this phase gets normal tests.

1. **Five failures lock that email, and only that email.** This protects accounts without locking out a whole campus network.
   - `test_five_failures_lock_that_email_only`: after 5 wrong passwords for customer A, a 6th attempt with the right password is refused with the "try again in 15 minutes" message. Customer B, from the same IP address, still logs in.
2. **The lockout ends after 15 minutes.** A lockout that never clears is as bad as no lockout.
   - `test_lockout_expires_after_15_minutes`: after locking customer A, the clock moves forward 15 minutes, and the right password then logs them in.

Normal tests cover the generic error, profile edits, password change sessions and the reset flow, which use Django's built-in views.

---

## Phase 12: Live search and category filter

**User stories**: 15, 16, 17, 18

### What to build

The catalog gets a search box and a category filter. Search is a case-insensitive partial match on title or description, combined with the optional category. Results update as you type through a debounced htmx request that returns a partial. Without JavaScript, the same view handles a normal form submit. Results keep the name sort and 12-per-page pagination, and include out-of-stock items.

### Acceptance criteria

- [ ] "hood" matches "Buff Hoodie – Medium". Description matches work. Case is ignored.
- [ ] The category filter combines with search, and pagination keeps both.
- [ ] Results come through the active-products helper, so inactive products never show.
- [ ] The results region is a live region. The plain submit works with JavaScript off.

### TDD

**Recommendation:** no TDD. Search is a plain filter on top of the already-tested active-products helper and affects only what is displayed, not stored data. Normal view tests cover partial match, category filter, pagination and the no-JavaScript submit.

---

## Phase 13: Staff product add and edit

**User stories**: 44, 45, 46, 47, 48, 52, 54

### What to build

Staff add and edit products: title, category, description, price, optional image, alt text (defaults to the title), low-stock threshold and active flag. Initial stock on create goes through the stock helper as a receive. Stock is read-only on the edit form. Uploaded images must really be JPEG, PNG or WebP (checked by Pillow) and no more than 5 MB. One copy is stored, resized to at most about 800 px wide and compressed, under a random filename. There is no delete, only marking inactive.

### Acceptance criteria

- [ ] A renamed non-image file, and a file over 5 MB, are rejected with clear messages.
- [ ] The stored image is at most about 800 px wide, has a random name, and the original isn't kept.
- [ ] Alt text defaults to the title when left blank.
- [ ] The edit form can't change stock. Initial stock creates a receive movement.
- [ ] Marking a product inactive removes it from the catalog, search and carts. Past orders are unaffected.
- [ ] New dashboard routes pass the persistent access test.

### TDD

**Recommendation:** TDD for the two behaviours below. Everything else in this phase gets normal tests.

1. **Uploads must be real JPEG, PNG or WebP files no larger than 5 MB.** This is the main safety check on user-supplied files.
   - `test_image_upload_validation`, parametrised: a text file renamed to `.jpg`, a GIF, and a 6 MB image are each rejected with a clear message. A small valid PNG is accepted.
2. **The edit form can't change stock.** Stock must change only through recorded actions.
   - `test_edit_form_cannot_change_stock`: posting the edit form with `stock=999` saves the other fields, but stock is unchanged and no stock movement is written.

---

## Phase 14: Disable and enable customers

**User stories**: 12, 69, 70, 71, 72

### What to build

Staff disable or re-enable customer accounts from `/dashboard/customers/`, with a required reason. The rules are explicit:

- **Sessions:** disabling immediately deletes every session belonging to that user, so they're logged out everywhere. A disabled user can't log in. The login error stays generic.
- **Open orders:** disabling **does not** cancel open orders automatically. The disable screen lists the customer's open orders with an unticked "cancel these too?" checkbox, so staff decide. If ticked, each order goes through the normal staff-cancel path with the disable reason, restoring stock and logging history.
- **Audit:** every disable and enable writes an AccountStatusChange row with who, when, the action and the reason. It is shown on the customer's dashboard page.
- **Limits:** staff can't disable themselves, other staff, or the superuser.

### Acceptance criteria

- [ ] After disabling, the customer's existing session is gone on their next request, and they can't log in.
- [ ] With the checkbox unticked, open orders stay as they were. With it ticked, they are cancelled with the reason, and stock is restored.
- [ ] Disable and enable each write an audit row with actor, time, action and reason. A missing reason is refused.
- [ ] Attempts to disable self, staff or the superuser are refused on the server, not just hidden in the page.
- [ ] New dashboard routes pass the persistent access test.
- [ ] `seed_demo` includes one disabled customer with an audit row.

### TDD

**Recommendation:** TDD for the three behaviours below. Everything else in this phase gets normal tests.

1. **Staff can't disable themselves, other staff or the superuser.** Staff must not be able to lock each other out.
   - `test_staff_cannot_disable_protected_accounts`, parametrised over self, another staff member and the superuser: the request is refused, the account stays active, and no audit row is written.
2. **Disabling ends the customer's sessions and blocks login.** The disable must take effect at once.
   - `test_disabling_ends_sessions_and_blocks_login`: a customer is logged in, then staff disable them. The customer's next request is treated as logged out, and logging in again fails with the generic error.
3. **Open orders are cancelled only when staff tick the box.** Staff decide what happens to open orders.
   - `test_open_orders_cancelled_only_when_ticked`: disabling with the box unticked leaves the customer's open orders unchanged. With it ticked, each open order is Cancelled with the disable reason, and its stock is restored.

---

## Phase 15: Staff operations: camera scanner and alert pop-up

**User stories**: 64, 73, 74, 75

### What to build

Two staff-facing operational features, demonstrated together.

**Camera QR scanner.** The pickup page gets a camera scanner, using a maintained JavaScript QR library loaded only on that page. A successful scan fills in the code and runs the same server-side verification as typing. The scanner handles each camera outcome:

- the browser asks for camera permission only when staff press "Start camera"
- if permission is denied, there is no camera, or the page isn't on `localhost`/HTTPS, a plain message says why and points to the typed field
- the typed field is always visible and always works, so it's the fallback

Camera scanning works on the laptop at `localhost`.

**Alert pop-up.** A dismissible pop-up in the dashboard polls through htmx every 30 seconds and shows, for example, "3 new orders · 2 low stock". After dismissal, it reappears at once if either count rises, otherwise after 15 minutes if the condition still holds. Staff can snooze it for 1 hour or until the end of the day. The snooze time is stored per staff member in the database. The "Low Stock" badges and the "Orders (N)" count always show.

### Acceptance criteria

- [ ] The scanner library is researched and pinned to an exact version, and loads only on the pickup page.
- [ ] A scan triggers the same server-side verification as a typed code. Scanning can't bypass the Ready check.
- [ ] Each camera outcome shows a clear text message and leaves the typed field working: permission denied, no camera, or insecure context.
- [ ] The scanner can be started and stopped with the keyboard, and the camera is released when stopped or when leaving the page.
- [ ] Alert counts match orders in Placed and active products at or below their threshold.
- [ ] Dismissed: the pop-up is hidden until a count rises, or until 15 minutes pass with the condition still true. Tested with a controllable clock.
- [ ] Snooze for 1 hour or end of day hides it, even if counts rise. Badges and the menu count are unaffected.
- [ ] The pop-up is a polite live region and can be dismissed by keyboard.
- [ ] New dashboard routes pass the persistent access test.
- [ ] Manual check: QR scan from a phone screen to the laptop webcam, and the denied-permission path.

### TDD

**Recommendation:** TDD for the three alert pop-up behaviours below. The camera scanner runs in the browser and is checked manually, and everything else in this phase gets normal tests.

1. **A dismissed alert returns immediately when a count rises.** New work must not be hidden by an old dismissal.
   - `test_dismissed_alert_returns_when_count_rises`: with 3 new orders, staff dismiss the alert. The next poll is hidden. A 4th order arrives, and the next poll shows the alert.
2. **A dismissed alert returns after 15 minutes if the condition still holds.** This is the reminder that stops alerts being forgotten.
   - `test_dismissed_alert_returns_after_15_minutes`: staff dismiss the alert with counts unchanged. At 14 minutes it is hidden. At 15 minutes, with the condition still true, it shows again.
3. **A snooze hides the alert even when counts rise, until it ends.** Snooze is the one deliberate way to silence it.
   - `test_snooze_hides_alert_until_it_ends`: staff snooze for 1 hour, and a new order arrives. The alert stays hidden. After 1 hour it shows again. The "Orders (N)" count is correct throughout.

---

## Phase 16: Analytics

**User stories**: 76, 77, 78, 79, 80, 81

### What to build

`/dashboard/analytics/` shows:

- Collected revenue (Picked Up orders) and Pending revenue (Placed, Preparing and Ready orders), summed from order-line snapshots
- the total order count with a breakdown by status
- the top 5 best-sellers by quantity across non-cancelled orders
- the low-stock list

A This week / This month / All time filter applies to revenue, counts and best-sellers, based on the placed date.

### Acceptance criteria

- [ ] Cancelled orders are excluded from revenue and best-sellers, but appear in the status breakdown.
- [ ] Revenue uses snapshot prices, not current prices.
- [ ] The period filter changes the figures correctly at the week and month boundaries.
- [ ] Figures are shown as text and tables. No information is given by colour alone.
- [ ] `seed_demo` spreads orders across dates so each period shows different figures.

### TDD

**Recommendation:** TDD for the two behaviours below. Everything else in this phase gets normal tests.

1. **Revenue splits into Collected and Pending from snapshot prices, excluding cancelled orders.** These are the figures the owner relies on.
   - `test_revenue_split_collected_and_pending`: orders exist in every status. After placing them, a product's price is changed. Collected equals the snapshot total of Picked Up orders. Pending equals the snapshot total of Placed, Preparing and Ready orders. Cancelled orders count in neither.
2. **Best-sellers ignore cancelled orders.** Otherwise cancelled orders would mislead restocking.
   - `test_best_sellers_exclude_cancelled`: product A sold 5 units in a cancelled order and 1 in a Placed order. Product B sold 3 in Placed orders. B ranks above A, and A's count is 1.

---

## Phase 17: Superuser override and staff management

**User stories**: 82, 83, 84, 85

### What to build

The superuser can override an order to any status except out of Cancelled, with a required reason. The override is logged as an override in the order history, with old status, new status and reason. Overriding into Cancelled restores stock. This is the only route out of Picked Up. The superuser can also add staff accounts and remove staff rights through a superuser-only dashboard page.

### Acceptance criteria

- [ ] The override is refused for plain staff and customers. A missing reason is refused. Cancelled → anything is refused.
- [ ] Every override writes a history row marked as an override.
- [ ] Overriding into Cancelled restores stock exactly once, including from Picked Up.
- [ ] Staff management routes refuse plain staff, and the persistent access test checks them.

### TDD

**Recommendation:** TDD for the three behaviours below. Everything else in this phase gets normal tests.

1. **Only the superuser can override, and a reason is required.** The override is the most powerful action in the app.
   - `test_override_requires_superuser_and_reason`: plain staff get 403. The superuser without a reason is refused. With a reason, the status changes, and one history row is marked as an override with old status, new status and reason.
2. **Nothing leaves Cancelled.** Reviving a cancelled order would double-count stock that was already restored.
   - `test_override_cannot_leave_cancelled`: overriding a Cancelled order to any other status is refused, and nothing changes.
3. **Overriding into Cancelled restores stock exactly once.** This is the one route out of Picked Up, and it must keep stock correct.
   - `test_override_into_cancelled_restores_stock_once`: overriding a Picked Up order of 2 units into Cancelled raises stock by 2, with one cancel movement. A second override attempt is refused, and stock doesn't rise again.

---

## Phase 18: Finish and polish

**User stories**: 33, 87, 88 (final)

### What to build

Make the app demo-ready:

- `seed_demo` creates orders in every status, with documented passwords.
- Accessibility and responsive pass at 360 px and 1920 px.
- `check --deploy` passes under production settings.
- Coverage is confirmed.
- The manual demo checklist is run.

### Acceptance criteria

- [ ] `seed_demo` produces data for every screen and every status, runs twice cleanly, and refuses production settings.
- [ ] **Coverage is at least 85% overall line coverage. This is a floor, not a substitute.** The dedicated critical-rule tests must exist and pass whatever the coverage number:
  - stock changes and adjustments
  - checkout and the concurrency test
  - order transitions and the override
  - permissions and the access walk
  - pickup verification
  - lockout and disabling
- [ ] `manage.py check --deploy` passes under production settings.
- [ ] Manual checklist done and noted:
  - the 360 px layout
  - QR display and webcam scan
  - a keyboard-only order walkthrough
  - screen-reader announcement of htmx updates
  - both emails in the console
- [ ] A first-time user can find a product and place an order in under 3 minutes (timed walkthrough).

### TDD

**Recommendation:** no TDD. This phase adds no new behaviour: it is seed data, polish, coverage and manual checks.
