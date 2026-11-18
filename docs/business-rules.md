# Business rules

Read when touching stock, checkout, order status, cancellation, pickup codes, account disabling, notifications or analytics. These are the rules most likely to break. Full detail: [PRD](../prd/buff-shop.md).

## Stock (NFR-A2)
- `select_for_update()` is a no-op on SQLite. Don't rely on it.
- One helper does every stock change. It runs a conditional single-statement update, e.g. `filter(pk=..., stock__gte=qty).update(stock=F("stock") - qty)`, inside `transaction.atomic()`, and checks the number of rows changed.
- A DB `CheckConstraint` enforces `stock >= 0`.
- Callers: checkout, cancel/restore, Receive Stock (+N), Stock Adjustment (±N, reason required). Each one writes a stock history row.
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
- Status: 0 → Out of Stock; ≤ threshold → "Low Stock — act soon"; above → In Stock.
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
