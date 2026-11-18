# PRD: Buff Shop Ordering Web App

CIDM 4360 Final Project. Source of truth for requirements and agreed design decisions. Supersedes the decision list in the handoff file.

## Problem Statement

The Buff Shop is a campus store that sells textbooks, merchandise and lab kits. It tracks stock in spreadsheets, and there is no online way for customers to order.

From the customer's side: a student can't check whether an item is in stock, can't reserve it, and can't see where an order stands. They have to walk in and hope.

From the shop's side: staff keep stock counts by hand. Two sales of the last unit can't be prevented, and nothing warns staff when stock runs low or a new order arrives. There's also no reliable way to confirm that the person collecting an order is the person who placed it, and no view of revenue or best-sellers.

## Solution

A Django web app with two faces:

- **A customer storefront.** Customers sign up and log in with their email. They browse and search the catalog, which shows live stock status. They build a cart and place an order to pay in person at pickup, in two steps from cart to confirmation. Checkout verifies and deducts stock atomically, and blocks the order if any item is short, naming every short item. Each order gets an order number and a random pickup code, shown as both text and a QR code. Customers can track status in their order history: Placed, Preparing, Ready for Pick Up, Picked Up, or Cancelled.
- **A staff dashboard.** Staff add and edit products, receive and adjust stock with a full history log, and move orders through their statuses. They hand orders over by scanning or typing the pickup code, and enable or disable customer accounts. They also see analytics and get light, dismissible alerts for new orders and low stock. A superuser can correct mistakes with a logged status override and keeps Django's built-in admin as an emergency data tool.

The app runs on localhost for the class demo. Production settings are written and pass Django's deployment check. It is accessible to WCAG 2.2 AA and works from 360 px to 1920 px wide.

## User Stories

### Customer: account

1. As a new customer, I want to sign up with my first name, last name, email and password, so that I can place orders.
2. As a customer, I want to log in with my email address, so that I don't have to remember a separate username.
3. As a customer, I want clear rules when my password is too weak (under 8 characters, too common, all numbers, or too similar to my details), so that I can pick an acceptable one.
4. As a customer, I want to tick "Remember me" to stay logged in for two weeks, so that I don't have to log in every visit on my own device.
5. As a customer on a shared computer, I want my session to end when I close the browser if I didn't tick "Remember me", so that the next person can't use my account.
6. As a customer, I want a generic error when my login fails, whether or not the email exists, so that nobody can use the login form to find out who has an account.
7. As a customer, I want my account locked for 15 minutes after 5 failed login attempts, with a message telling me when to try again, so that nobody can guess my password.
8. As a customer, I want the lockout to apply to my account rather than my IP address, so that other students on the same campus network aren't locked out because of me.
9. As a customer, I want to reset a forgotten password by email, so that I can get back into my account.
10. As a customer, I want to edit my first and last name, so that my details stay correct.
11. As a customer, I want to change my password, so that I can keep my account secure.
12. As a customer whose account has been disabled, I want to be unable to log in and to have my active sessions ended, so that the disable takes effect immediately.

### Customer: catalog and search

13. As a customer, I want to see each product's name, category, price, image and stock status, so that I can decide what to buy.
14. As a customer, I want stock status shown as "In Stock", "Low Stock — act soon" or "Out of Stock" in words and not only by colour, so that I can read it however I view the page.
15. As a customer, I want to search by words in a product's title or description, ignoring case and matching partial words, so that I can find items without typing exact names.
16. As a customer, I want to filter the catalog by category (Textbook, Merchandise, Lab Kit), so that I can narrow down what I see.
17. As a customer, I want search results to update as I type, so that I can find things quickly.
18. As a customer without JavaScript, I want the search form to still work when I submit it, so that the catalog is usable in any browser.
19. As a customer, I want out-of-stock items to still appear in results, labelled "Out of Stock", so that I know the shop carries them.
20. As a customer, I want results sorted by name and paginated 12 per page, so that the list is predictable and easy to scan.
21. As a customer, I want a placeholder image when a product has no photo, so that the layout stays consistent.
22. As a customer, I want discontinued products to disappear from the catalog, search and my cart, so that I can't order something the shop no longer sells.

### Customer: cart and checkout

23. As a customer, I must be logged in to use the cart or place an order, so that every order belongs to a known account (no guest checkout).
24. As a customer, I want my cart saved to my account, so that it's still there when I come back on another device.
25. As a customer, I want to change quantities in my cart and see totals update without a full page reload, so that I can adjust my order quickly.
26. As a customer, I want to be stopped from setting a quantity above the current stock, so that I don't build an order that can't be filled.
27. As a customer, I want a "Place Order (Pay at Pickup)" button on the cart page that takes me straight to a confirmation, so that ordering takes no more than a few steps.
28. As a customer, I want checkout to tell me every item that is short if stock ran out while I was shopping, so that I can fix them all at once.
29. As a customer, I want my cart left unchanged when my order fails, so that I don't have to rebuild it.
30. As a customer, I want a double-click on "Place Order" to create only one order, so that I'm not charged for duplicates at pickup.
31. As a customer, I want the confirmation page to show my order number, pickup code and QR code, so that I know the order went through and how to collect it.
32. As a customer, I want my order to keep the price I saw when I ordered, even if the shop changes the price later, so that the amount due at pickup is what I agreed to.
33. As a first-time customer, I want to find a product and complete an order in under 3 minutes, so that ordering is quicker than walking in.

### Customer: orders and pickup

34. As a customer, I want an order history showing each order's date, items, total and status, so that I can track my orders.
35. As a customer, I want to open an order and see its pickup code and a QR code that my phone screen can show to staff, so that collecting is quick.
36. As a customer, I want to get an email when my order is Ready for Pick Up, so that I know when to go to the shop.
37. As a customer, I want that email to contain the order number but never the pickup code, so that someone reading my email can't collect my order.
38. As a customer, I want to cancel my own order while it is still Placed, without having to give a reason, so that I can change my mind before staff start preparing it.
39. As a customer, I want to see who cancelled an order and why ("Cancelled by customer" or "Cancelled by store: <reason>"), so that I understand what happened.
40. As a customer, I want "not found" if I try to open someone else's order, so that other people's orders stay private.

### Staff: access

41. As a staff member, I want one custom dashboard for all my shop work, so that I don't need Django's technical admin screens.
42. As the shop owner, I want every dashboard page and action to check the user's role on the server and refuse anyone who isn't staff, so that customers can't reach admin functions by guessing URLs.
43. As the shop owner, I want Django's built-in admin restricted to the superuser, so that ordinary staff can't make unsafe raw data edits.

### Staff: products and stock

44. As a staff member, I want to add a product with title, category, description, price, optional image, alt text, initial stock and low-stock threshold, so that it appears in the catalog.
45. As a staff member, I want uploaded images checked to be real JPEG, PNG or WebP files no larger than 5 MB, and stored as one resized, compressed copy, so that the site stays fast and safe.
46. As a staff member, I want alt text to default to the product title, so that every image is accessible without extra effort.
47. As a staff member, I want to update a product's price directly on its edit form, so that price changes are quick.
48. As a staff member, I want stock to be read-only on the edit form, so that stock only changes through recorded actions.
49. As a staff member, I want to "Receive Stock" by entering a positive amount, so that deliveries are recorded.
50. As a staff member, I want to make a "Stock Adjustment" up or down with a required reason, so that I can correct counts after breakage, loss or a miscount.
51. As a staff member, I want to see each product's stock history (checkouts, cancellations, receipts and adjustments, with who, when and why), so that I can explain any count.
52. As a staff member, I want to mark a product inactive and not delete it, so that past orders keep their history and the product can be brought back.
53. As a staff member, I want inactive products clearly labelled "Inactive" in my product list, so that I don't confuse them with live ones.
54. As a staff member, I want to set a low-stock threshold for each product, so that fast sellers can warn earlier than slow ones.
55. As a staff member, I want a "Low Stock" badge on products in my product list that I can't silence, so that I always know what needs reordering.

### Staff: orders

56. As a staff member, I want to see and filter orders by status, so that I can work through them.
57. As a staff member, I want an "Orders (N)" count in the dashboard menu, so that I always know how many new orders are waiting.
58. As a staff member, I want one button that moves an order to its next status (Placed → Preparing → Ready for Pick Up), so that updating orders is quick and hard to get wrong.
59. As a staff member, I want to undo one step (Ready → Preparing, Preparing → Placed), so that I can fix an accidental click.
60. As a staff member, I want the only way to mark an order Picked Up to be a matching pickup code, so that orders are handed only to the right person.
61. As a staff member, I want to cancel any order before it is picked up, with a required reason that the customer sees, so that customers know why their order was cancelled.
62. As a staff member, I want cancelling an order to put its stock back, so that the items can be sold again.
63. As a staff member, I want each order's history to show every status change with who and when, so that I can see what happened to it.

### Staff: pickup verification

64. As a staff member, I want to scan a customer's QR code with the laptop camera, so that handover is fast.
65. As a staff member, I want to type the pickup code if the camera doesn't work, so that I can always complete a handover.
66. As a staff member, I want a code to be accepted only if it belongs to an order that is Ready for Pick Up, so that orders can't be collected early or twice.
67. As a staff member, I want a clear message when a code is wrong, already used, or belongs to a cancelled order, so that I know why it was rejected.
68. As a staff member, I want a matching code to show the customer's name and items before I click "Confirm Handover", so that I can check the order before giving it out.

### Staff: customer accounts

69. As a staff member, I want to disable or re-enable customer accounts with a required reason, so that I can deal with abuse.
70. As a staff member, I want to be unable to disable myself, other staff or the superuser, so that staff can't lock each other out.
71. As a staff member, I want the disable screen to list the customer's open orders with a "cancel these too?" checkbox, so that I decide what happens to them.
72. As the shop owner, I want who disabled or enabled an account, and when, to be logged, so that account actions can be audited.

### Staff: notifications

73. As a staff member, I want a light pop-up such as "3 new orders · 2 low stock" that refreshes every 30 seconds, so that I notice new work without reloading.
74. As a staff member, I want to dismiss the pop-up and have it come back right away only if something new happens, or after 15 minutes if the condition still holds, so that it reminds me without nagging.
75. As a staff member, I want to snooze the pop-up for 1 hour or until the end of the day, so that I can focus during busy periods.

### Staff: analytics

76. As the shop owner, I want to see Collected revenue (Picked Up orders) and Pending revenue (Placed, Preparing and Ready orders) separately, so that I know what's been paid and what's expected.
77. As the shop owner, I want the total order count with a breakdown by status, so that I can see the workload.
78. As the shop owner, I want the top 5 best-selling products across all non-cancelled orders, so that I know what to stock more of.
79. As the shop owner, I want a list of low-stock products, so that I know what to reorder.
80. As the shop owner, I want to switch analytics between This week, This month and All time, so that I can compare periods.
81. As the shop owner, I want cancelled orders left out of revenue and best-sellers, so that the figures are accurate.

### Superuser

82. As the superuser, I want to override an order to any status except out of Cancelled, with a required reason, so that I can fix mistakes the normal flow can't.
83. As the superuser, I want every override logged with who, when, old status, new status and reason, and shown in the order's history, so that corrections are auditable.
84. As the superuser, I want an override into Cancelled to put stock back, so that stock stays correct.
85. As the superuser, I want to manage staff accounts, so that I control who can run the shop.
86. As the superuser, I want to edit the category list in Django's built-in admin, so that new categories can be added without a code change.

### Demo and development

87. As the developer, I want a demo-data command that creates a superuser, a staff account, several customers, about 15 products (some low and some out of stock), and orders in every status, so that the app can be demonstrated straight away.
88. As the developer, I want the demo-data command to be safe to run twice and to refuse to run under production settings, so that it can't damage real data.
89. As the developer, I want emails printed to the console during development and the demo, so that I can show password reset and ready-for-pickup emails without a mail server.

## Implementation Decisions

### Stack and project setup

- Django, SQLite, htmx and Pillow, as mandated by the brief. The `qrcode` library (with Pillow) generates QR images. `django-axes` handles lockout.
- The tooling is pytest with pytest-django, factory_boy, pytest-cov, and ruff for lint and format.
- Styling uses Tailwind CSS, built with the standalone CLI binary, so the project needs no Node.js. The built stylesheet is committed so the app runs without a build step.
- The project is not yet a git repository. Initialise git before the first code is written.
- htmx requests send Django's CSRF token.

### Apps (suggested split)

- **Accounts:** the custom user model, sign-up, login and logout, profile, password change and reset, lockout integration, and account disable/enable with its audit log.
- **Catalog:** categories, products, the shared "active products" query helper, search, and image processing.
- **Stock:** the single safe stock-change helper and the stock history log.
- **Cart:** the per-user database cart.
- **Orders:** orders, order lines, order numbers, the status transition table, cancellation, the override, pickup codes, QR rendering, and the ready-for-pickup email.
- **Dashboard:** every staff-facing view (products, stock, orders, pickup verification, customers, notifications, analytics), behind one staff-only access check.

### Accounts and roles

- A custom user model is created before the first migration. Email is the unique login field, and first and last name are required.
- Password rules are Django's four default validators, and hashing uses Django's default (PBKDF2, salted).
- `is_staff` means shop staff ("Admin" in the brief). `is_superuser` alone grants status overrides, staff account management, and access to Django's built-in admin. Plain staff are blocked from the built-in admin.
- Lockout uses `django-axes`, keyed on the submitted email only (not IP): 5 failures lock the account for 15 minutes. The login error is the same whether or not the email exists. The lockout message says to try again in 15 minutes.
- Disabling an account is separate from lockout. A disabled user can't log in, and their existing sessions are deleted when they are disabled.
- Staff may disable or enable customers only, never themselves, other staff, or the superuser. A reason is required, and who and when are recorded. The disable screen lists the customer's open orders with an optional "cancel these too" checkbox. Cancelling them goes through the normal staff-cancel path, with the disable reason.
- Customers can edit their name and change their password. They can't delete their own account.
- Session length: two weeks with "Remember me"; otherwise the session ends when the browser closes.

### Access control

- Every dashboard view, and every action it posts to, enforces staff role on the server. Anonymous users are redirected to log in. Logged-in non-staff users get an "access denied" response.
- Every customer order view looks the order up scoped to the current user. Another user's order returns "not found", not "access denied", so its existence isn't revealed.

### Catalog

- **Category** is a table seeded by a data migration with Textbook, Merchandise and Lab Kit. It is editable only in Django's built-in admin, with no dashboard pages.
- **Product** has a title, category, description, price, optional image, required alt text (defaulting to the title), stock, a low-stock threshold (default 5), and an active flag.
- There are no variants. Sizes are separate products, e.g. "Buff Hoodie – Medium".
- Products are soft-deleted only: there is no hard delete from the dashboard. Inactive products are excluded from every customer-facing query (catalog, search, cart, and the future assistant) through one shared active-products helper. They appear as "Inactive" in the dashboard.
- Stock status comes from stock and that product's threshold:
  - **Out of Stock** at 0.
  - **Low Stock — act soon** at or below the threshold.
  - **In Stock** above it.

  The same threshold drives the staff low-stock badge, the pop-up count, and the analytics low-stock list.
- Search is a case-insensitive partial match on title or description, combined with an optional category filter. It is sorted by name, with 12 per page. Out-of-stock items are included. Live results come from a debounced htmx request that returns a partial. The same view handles a plain form submit without JavaScript.
- Image uploads are validated by Pillow as real JPEG, PNG or WebP, and anything over 5 MB is rejected. One copy is stored, resized to at most about 800 px wide and compressed, under a random filename, and the original is discarded. Products without an image show a placeholder.
- Prices are edited on the product form. There is no price history.

### Cart and checkout

- The cart is stored in the database, one per user, with lines of product and quantity. No stock is reserved before checkout. Inactive products are dropped from the cart view.
- Quantity changes post through htmx and return updated line and cart totals. The server caps quantity at current stock.
- Checkout has two steps: the cart page, whose "Place Order (Pay at Pickup)" button leads to the confirmation page with the order number, pickup code and QR code.
- The order and all stock deductions happen in one database transaction. Each line is attempted, and every short line is collected. If any line is short, the whole transaction rolls back, the cart is left untouched, and the customer sees every short item by name. On success the cart is emptied.
- Each order line saves a snapshot of the product name and unit price at purchase time. The order total comes from these snapshots.
- Double submits are blocked twice over. In the browser, the button is disabled after the first click. On the server, a per-submission guard means a repeated submit can't create a second order.

### Stock integrity

- SQLite ignores `select_for_update()`, so the design doesn't rely on it.
- All stock changes go through one helper that runs a single conditional UPDATE. The UPDATE subtracts or adds the quantity only if the result stays at zero or above, then checks the number of rows changed to know whether it succeeded. Checkout, cancel/restore, Receive Stock, and Stock Adjustment all use it.
- The database has a check constraint that stock is never negative, as a second line of defence.
- SQLite is configured for IMMEDIATE transactions with a busy timeout, so concurrent writers wait in line instead of failing straight away.
- Every stock change writes a history row with the product, the change amount, the resulting stock, the kind (checkout, cancel, receive, or adjust), the related order if any, the user, the time, and the reason where one is required.
- Stock is read-only on the product edit form. Receive Stock takes a positive amount. Stock Adjustment takes a positive or negative amount and requires a reason.

### Orders

- **Order number:** `BUF-<year>-<5-digit sequence>`, e.g. `BUF-2026-01042`.
- **Statuses:** Placed, Preparing, Ready for Pick Up, Picked Up, and Cancelled. One table of allowed transitions holds every rule, with the actor allowed for each:
  - Staff forward moves: Placed → Preparing → Ready for Pick Up.
  - Staff one-step undo: Ready → Preparing, and Preparing → Placed.
  - Ready → Picked Up happens only through pickup code verification.
  - Customer cancel: only from Placed.
  - Staff cancel: from any status before Picked Up.
  - Picked Up and Cancelled are final in the normal flow.
- **Superuser override:** moves an order to any status except out of Cancelled. It requires a reason. An override into Cancelled restores stock.
- Every status change, including overrides and cancellations, writes an order history row: who, when, old status, new status, and reason. The order page shows this history.
- **Cancellation:**
  - Customer cancels are labelled "Cancelled by customer", with no reason asked.
  - Staff cancels need a reason, and the customer sees "Cancelled by store: <reason>".
  - Every cancel restores stock through the safe helper.
  - Cancelled orders are excluded from revenue and best-sellers.

### Pickup codes and QR

- Each order gets a random 6-character pickup code from an alphabet without look-alike characters (no 0/O or 1/I). It is displayed in two groups of three, e.g. `K7F-29Q`. It is not derived from the order number and is unique among orders.
- The customer's order page shows a QR code encoding the same pickup code, with the code printed underneath. It is sized to scan from a phone screen.
- The staff verification page takes a typed code, accepting it with or without the hyphen and in any case. It also offers a camera scanner that uses a JavaScript QR scanning library loaded only on that page.
- A code is accepted only when it matches an order in Ready for Pick Up. Otherwise the page says the code was not found, already used, or cancelled. A match shows the customer's name and items. "Confirm Handover" then moves the order to Picked Up and logs who did it.

### Staff notifications

- A dismissible pop-up in the dashboard polls through htmx every 30 seconds. It shows the count of orders in Placed and the count of active products at or below their threshold, e.g. "3 new orders · 2 low stock".
- After dismissal, it reappears at once if either count rises. Otherwise it returns after 15 minutes if the condition still holds.
- A per-staff "snoozed until" time, stored in the database, hides the pop-up for 1 hour or until the end of the day.
- The "Low Stock" badge on the staff product list and the "Orders (N)" menu count always show, whatever the snooze or dismissal state.
- Customers get no notifications to silence. "Low Stock — act soon" is product information.

### Analytics

- **Revenue:** Collected (Picked Up orders) and Pending (Placed, Preparing and Ready orders), summed from order line snapshots.
- **Orders:** total count with a per-status breakdown.
- **Top 5 best-sellers:** by quantity across non-cancelled orders.
- **Low stock:** a list of active products at or below their threshold.
- A This week / This month / All time filter applies to revenue, order counts and best-sellers. It filters on the order's placed date.

### Email

- Django's built-in password reset flow.
- A "Ready for Pick Up" email is sent when an order enters Ready. It contains the order number, never the pickup code.
- A failed email send is caught and logged. It never blocks or rolls back the status change.
- Development and the demo use the console email backend.

### Accessibility and responsive design

- The target is WCAG 2.2 AA:
  - a visible label on every form field
  - text contrast of at least 4.5:1
  - full keyboard operation with a visible focus outline
  - status always given in text and never by colour alone
  - tap targets of at least 24 px
- htmx-updated regions (search results, cart totals, the notification pop-up, pickup verification results) are live regions, so screen readers announce changes.
- Layouts work from 360 px to 1920 px on current Chrome, Safari, Firefox and Edge.

### Settings and deployment

- The app runs on localhost for the demo.
- Separate production settings read secrets from environment variables and turn on SSL redirect, secure cookies and HSTS. `manage.py check --deploy` passes under these settings.
- Running on localhost has consequences:
  - Camera QR scanning works on the laptop browser at `localhost`, but not on a phone over the LAN, because that connection isn't HTTPS.
  - The typed code is always the fallback.

### Demo data

- A `seed_demo` management command creates:
  - a superuser, a staff account, and a few customers, all with documented demo passwords
  - about 15 products across the three categories, including low-stock and out-of-stock ones
  - orders in every status
- It is idempotent and refuses to run under production settings.

## Testing Decisions

- **What makes a good test here:** test observable behaviour through public interfaces, using the Django test client for views and the service functions for business rules. Don't assert on internal implementation details. Each critical rule gets tests that would fail if the rule were broken.
- **Critical-rule tests (required):**
  - **Checkout and stock:**
    - deduction succeeds when stock is sufficient
    - every short item is named and nothing is deducted when any item is short
    - the cart is untouched on failure
    - stock never goes negative
    - a double submit creates one order
    - cancel restores stock
    - every stock change writes a history row
  - **Concurrency:** two simultaneous checkouts for the last unit; exactly one succeeds.
  - **Pickup code:**
    - the correct code on a Ready order succeeds
    - a wrong code, an already-used code, a cancelled order's code, and a code for an order not yet Ready are each rejected with the right message
    - typed codes are normalised (case, hyphen)
  - **Status transitions:**
    - every allowed transition succeeds for the allowed actor
    - every disallowed transition is refused
    - Picked Up is reachable only through verification
    - the override is superuser-only, can't leave Cancelled, requires a reason, and is logged
  - **Access control:**
    - an automatic test enumerates every `/dashboard/` URL and checks that anonymous users and regular customers are both refused
    - the built-in admin refuses plain staff
    - customers get "not found" for other users' orders
    - staff can't disable staff or the superuser
  - **Lockout:**
    - 5 failures lock the account for 15 minutes
    - the error message doesn't reveal whether the email exists
    - a disabled user can't log in and their sessions are ended
- **Coverage:** 85% line coverage target, measured with pytest-cov.
- **Test data:** factory_boy factories for users, categories, products, carts and orders.
- **Build these with TDD:**
  - the stock-change helper
  - the status-transition table
  - pickup code verification
  - the dashboard access-control test
- **Manual demo checklist (no Playwright):**
  - the 360 px layout
  - QR display and scanning on the laptop webcam
  - a keyboard-only walkthrough of the order flow
  - screen-reader announcement of htmx updates
  - the console output of both emails
- **Prior art:** none. This is a new codebase.

## Out of Scope

- The **AI shopping assistant** is deferred as a stretch goal, built last if at all. If built, the agreed constraints are:
  - logged-in customers only
  - read-only
  - order lookup returns only the user's own orders
  - it never reveals the pickup code
  - it stays on Buff Shop topics, with a test set of off-topic prompts it must decline

  The preferred approach is Claude with two tools, `search_products` and `get_my_order_status`. The model choice is left open, so ask the user when that phase starts.
- Online payment of any kind. Customers pay in person at pickup.
- Guest checkout.
- Product variants (sizes, colours) as a single product with multiple stock counts.
- Price history.
- Hard deletion of products from the dashboard.
- Dashboard pages for managing categories. Categories are managed in Django's built-in admin.
- Customer self-deletion of accounts.
- Stock reservation before checkout.
- Per-staff "seen" tracking of new orders.
- Customer notifications other than the "Ready for Pick Up" email and password reset.
- Public hosting. The demo is localhost only; production settings are written but not deployed.
- HTTPS on the LAN, and therefore phone-camera QR scanning from another device.
- Automated browser testing (Playwright or similar).

## Further Notes

- **Interpretations to confirm.** Two answers from the design interview were read in a specific way and never explicitly confirmed:
  1. "Allow an override if a mistake occurs and explain the reasoning" was read as "the superuser must type a reason, which is logged".
  2. "An option to allow users to silence banner notifications" was read as "staff can snooze the pop-up". Customers get nothing to silence, because their "act soon" badge is product information.

  Both are built as described above unless the user says otherwise.
- **Naming.** The brief's "Admin" role is implemented as Django staff. "Admin" in the client brief means the dashboard; Django's built-in admin is a separate, superuser-only tool.
- **Order of work.** The risky rules (atomic stock deduction, the transition table, pickup verification and access control) should be built and tested early, in thin end-to-end slices. The demo-data command should come early too, so every later slice can be shown working.
- **Research to do before building**, against current primary sources:
  - `django-axes` configuration for an email-based custom user model with account-only locking
  - Django's SQLite `transaction_mode` option and its version requirements
  - the Tailwind standalone CLI
  - a maintained JavaScript QR scanning library
