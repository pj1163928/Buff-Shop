# Business rules

Read when touching stock, checkout, order status, cancellation, pickup codes, account disabling, notifications or analytics. These are the rules most likely to break. Full detail: [PRD](../prd/buff-shop.md).

## Stock (NFR-A2)
- `select_for_update()` is a no-op on SQLite. Don't rely on it.
- **`stock.services.change_stock()`** does every stock change. Inside one `transaction.atomic()` (which takes SQLite's write lock at once, IMMEDIATE mode) it:
  1. refuses a reused `submission_token` (`DuplicateSubmission`);
  2. runs one conditional UPDATE, `filter(pk=…, stock__gte=-change).update(stock=F("stock") + change)`, i.e. `WHERE stock + change >= 0`, and checks exactly one row changed, else raises `InsufficientStock` (with `.available`);
  3. reads the resulting stock back and writes **exactly one** `StockMovement`. If that insert fails, the UPDATE rolls back with it. Stock never changes without history.
- Rules it enforces (`ValueError`, nothing changed): a whole number, never 0, at most `MAX_STOCK_CHANGE` (10,000) either way; receive and cancel add, checkout removes, adjust goes either way; an adjust needs a reason (trimmed, at most 200 characters). Receive notes are optional.
- It's safe inside an outer transaction: a refusal raises before anything is written, so checkout can catch `InsufficientStock` per line and carry on collecting short items.
- A DB `CheckConstraint` enforces `stock >= 0` as the second, independent safeguard.
- Callers: checkout, cancel/restore, Receive Stock (+N), Stock Adjustment (±N, reason required). The stock forms carry a one-time token, so a double click applies a change once.
- Stock history is append-only (see [architecture.md](architecture.md#stock)). `seed_demo` creates demo stock through the helper too.
- Stock is read-only on the product edit form.

## Checkout (FR-C2)
- The cart lives in the DB per user. No stock is reserved until checkout.
- Try every line and collect **all** short items. If any line is short, roll back and name every short item.
- The cart is untouched on failure and emptied on success.
- Block double submits in the browser and on the server.
- Order lines snapshot the product name and unit price.

## Order status
- Flow: Placed → Preparing → Ready for Pick Up → Picked Up, plus Cancelled.
- **All** allowed moves live in one transition table, with the actor for each:
  - staff forward one step
  - staff undo one step (Ready → Preparing, Preparing → Placed)
  - Ready → Picked Up **only** through pickup verification
  - customer cancels only from Placed
  - staff cancel any time before Picked Up, with a reason the customer sees
- Superuser override: any status except out of Cancelled. Reason required. Into Cancelled restores stock.
- Every change logs who, when, old status, new status and reason.
- Every cancel restores stock. Cancelled orders are excluded from revenue and best-sellers.

## Pickup code (FR-A2)
- Random, 6 characters, with no 0/O or 1/I. Displayed as `K7F-29Q`. Not derived from the order number.
- The QR code encodes the same code.
- Accept typed codes in any case, with or without the hyphen.
- Valid only while the order is Ready. Otherwise the message is "not found", "already used" or "cancelled".
- A match shows the customer name and items, then **Confirm Handover**.
- **Never** put the code in email, logs or the AI assistant.

## Accounts
- Lockout: `django-axes`, by email only (not IP). 5 failures cause a 15-minute lock.
- Login errors are generic, so they don't reveal whether an email exists.
- Disable ≠ lockout. Disabling ends active sessions.
- Staff can disable or enable **customers only**, with a reason, and it is logged. Never self, other staff or the superuser.
- The disable screen offers "cancel open orders too?".

## Stock status and notifications
- Status: 0 → Out of Stock; ≤ threshold → "Low Stock — act soon"; above → In Stock. Always use `catalog.models.stock_status()` / `product.stock_status`; never re-implement the comparison.
- Customer-facing product queries start from `Product.objects.active()`.
- Staff badges (dashboard product list, `templates/dashboard/_product_badges.html`) use three separate categories: **Out of Stock** (0), **Low Stock** (1 to threshold), **In Stock** (above), plus **Inactive**. Branch on `stock_status.value`.
- **Out of Stock counts toward the low-stock total** (stock ≤ threshold) for the alert pop-up and the analytics low-stock list, but stays its own status category in every display.
- Staff pop-up (htmx poll every 30 s) counts orders in Placed and active products at or below their threshold.
  - After dismissal it returns immediately on new activity, otherwise after 15 minutes.
  - Per-staff "snoozed until" (1 hour or end of day) is stored in the DB.
- The "Low Stock" badge and the "Orders (N)" menu count always show, whatever the snooze.

## Analytics
- Collected revenue = Picked Up orders. Pending revenue = Placed, Preparing and Ready orders.
- Top 5 best-sellers by quantity across non-cancelled orders.
- Filter: This week / This month / All time.

## Email
- Password reset, plus a "Ready for Pick Up" email that has the order number and never the code.
- A failed send is logged and never blocks the status change.
- Send after the commit (`transaction.on_commit()`), never inside a transaction: IMMEDIATE transactions hold SQLite's write lock.
