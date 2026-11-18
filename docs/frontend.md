# Frontend

Read when writing templates, htmx interactions, CSS, images or the QR scanner.

## Styling
- Tailwind CSS v4, built with the standalone CLI binary (no Node.js) via django-tailwind-cli. Source: `tailwind/source.css` (kept outside `static/`). Output: `static/css/site.css`.
- **Commit the built `static/css/site.css`** so the app runs without a build step. Rebuild with `uv run python manage.py tailwind build`.
- **Theme: WTAMU web colours**, read from wtamu.edu's CSS: maroon `#450012` (primary), `maroon-950/800/700/600/50`, `charcoal` `#332c2c` (text, footer), `muted`, `mist`, `line`, `success`, `danger`, `warning` (Low Stock). Fonts: Oswald (`font-display`, headings and buttons, uppercase) and Nunito Sans (`font-sans`, body), from Google Fonts. No WTAMU logo is used.
- Shared classes in `source.css`: `.btn-primary`, `.btn-outline`, `.nav-link`, `.card`, `.help-text`, `.field-error`. Inputs are styled globally.
- Put `.on-maroon` on dark areas so the focus ring turns white there.
- **Icons:** Font Awesome Free 6.7.2 solid SVGs (CC BY 4.0, attributed in the footer), inlined from `templates/icons/`: `{% include "icons/user.svg" with class="h-5 w-5" %}`. They are `aria-hidden`, so always pair them with text. Add new ones from `https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@6.7.2/svgs/solid/<name>.svg` and add the same attributes.
- Forms: `{% include "includes/field.html" with field=form.x %}` gives a visible label, errors at `<id>_error` and help at `<id>_helptext`. Django adds `aria-describedby` and `aria-invalid`. `includes/form_errors.html` is the `role="alert"` summary.
- Stock status: `{% include "catalog/_stock_status.html" with status=product.stock_status %}` gives an icon plus the words; style branches on `status.value`, never on the label.
- Dashboard pages extend `templates/dashboard/base.html` (side menu of `.dash-link`s with `aria-current="page"`; add each new section there) and fill `{% block dashboard_content %}`. Staff see a "Dashboard" link in the header.
- Staff product badges: `{% include "dashboard/_product_badges.html" with product=product %}`.
- Wide staff tables sit in an `overflow-x-auto` region with `role="region"`, `tabindex="0"` and `aria-labelledby` the caption, with the key column (status) right after the name so it stays visible at 360 px.
- `templates/403.html` is the "Access denied" page.
- Messages render in `base.html` in a `role="status"` region, with an icon and a visually hidden "Success:"/"Error:" prefix.
- Layouts must work from 360 to 1920 px on current Chrome, Safari, Firefox and Edge.

## htmx
- Every htmx request sends the Django CSRF token.
- Partial updates:
  - live catalog search (debounced)
  - cart quantity and totals
  - the staff notification pop-up (30 s poll)
  - pickup verification results
- Every htmx feature still works as a plain form submit without JavaScript.
- Double submit: disable the button after the first click (the server guards too).

## Accessibility (WCAG 2.2 AA)
- A visible label on every field.
- Text contrast of at least 4.5:1.
- Full keyboard use with a visible focus outline.
- Status is always shown in text, never by colour alone.
- Tap targets of at least 24 px.
- htmx-updated regions are ARIA live regions, so screen readers announce changes.

## Images
- Optional, with a placeholder when missing: `static/img/product-placeholder.svg`, `alt="No photo available"`. Product images use `product.alt_text`.
- Pillow validates real JPEG, PNG or WebP files and rejects anything over 5 MB.
- Store one copy resized to at most about 800 px wide, compressed, under a random filename. Discard the original.
- Alt text is required and defaults to the product title.

## QR
- Generate it server-side with `qrcode` + Pillow, and print the code underneath. It must be readable on a phone screen.
- Staff camera scanning uses a JS library loaded **only on the verification page**. It works at `localhost` on the laptop, not on a phone over the LAN (no HTTPS). The typed code is always the fallback.
