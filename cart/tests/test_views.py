"""The cart pages through the test client: access, persistence, htmx and no-JavaScript."""

import re

import pytest
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from accounts.tests.factories import DEFAULT_PASSWORD, UserFactory
from cart.models import Cart, CartLine
from cart.tests.factories import CartFactory, CartLineFactory
from catalog.tests.factories import ProductFactory

pytestmark = pytest.mark.django_db

CART_URL = reverse("cart:detail")
HTMX = {"HTTP_HX_REQUEST": "true"}


def line_url(product) -> str:
    return reverse("cart:line", args=[product.pk])


def add_url(product) -> str:
    return reverse("cart:add", args=[product.pk])


def quantity_of(user, product) -> int | None:
    line = CartLine.objects.filter(cart__user=user, product=product).first()
    return line.quantity if line else None


def messages_on(response) -> list[str]:
    return [str(m) for m in response.context["messages"]]


# --- Login required; no guest cart -----------------------------------------------------


@pytest.mark.parametrize(
    ("method", "url_for"),
    [("get", lambda p: CART_URL), ("post", add_url), ("post", line_url)],
)
def test_cart_pages_send_anonymous_visitors_to_log_in(client, method, url_for):
    product = ProductFactory()
    url = url_for(product)

    response = client.get(url) if method == "get" else client.post(url, {"quantity": 1})

    assert response.status_code == 302
    assert response["Location"] == f"{reverse('accounts:login')}?next={url}"
    assert not Cart.objects.exists()
    assert not CartLine.objects.exists()


@pytest.mark.parametrize("url_for", [add_url, line_url])
def test_cart_actions_are_post_only(client, url_for):
    client.force_login(UserFactory())
    assert client.get(url_for(ProductFactory())).status_code == 405


def test_viewing_the_cart_creates_no_cart(client):
    client.force_login(UserFactory())
    response = client.get(CART_URL)
    assert response.status_code == 200
    assert "Your cart is empty." in response.content.decode()
    assert not Cart.objects.exists()


# --- Saved to the account, across sessions and devices ---------------------------------


def test_cart_is_still_there_in_a_new_session_on_another_device():
    user = UserFactory()
    product = ProductFactory(title="Lab Safety Goggles", stock=10)
    laptop = Client()
    laptop.login(email=user.email, password=DEFAULT_PASSWORD)
    laptop.post(add_url(product), {"quantity": 1})
    laptop.post(reverse("accounts:logout"))

    phone = Client()
    phone.login(email=user.email, password=DEFAULT_PASSWORD)
    response = phone.get(CART_URL)

    assert "Lab Safety Goggles" in response.content.decode()
    assert [line.product for line in response.context["cart"].lines] == [product]


# --- Add to cart from the catalog ------------------------------------------------------


def test_add_to_cart_returns_to_the_catalog_page_with_a_message(client):
    user = UserFactory()
    product = ProductFactory(title="Maroon Water Bottle", stock=10)
    client.force_login(user)

    response = client.post(add_url(product), {"quantity": 1, "next": "/?page=1"})

    assert response.status_code == 302
    assert response["Location"] == "/?page=1"
    assert quantity_of(user, product) == 1
    followed = client.get(response["Location"])
    assert "Added Maroon Water Bottle to your cart. You have 1." in messages_on(followed)


@pytest.mark.parametrize("unsafe", ["https://evil.example/", "//evil.example/", ""])
def test_add_to_cart_never_redirects_off_site(client, unsafe):
    client.force_login(UserFactory())
    response = client.post(add_url(ProductFactory()), {"quantity": 1, "next": unsafe})
    assert response["Location"] == reverse("catalog:index")


def test_adding_more_than_stock_is_capped_and_explained(client):
    user = UserFactory()
    product = ProductFactory(title="Buffs Lanyard", stock=2)
    CartLineFactory(cart=CartFactory(user=user), product=product, quantity=2)
    client.force_login(user)

    response = client.post(add_url(product), {"quantity": 1}, follow=True)

    assert quantity_of(user, product) == 2
    assert (
        "Only 2 are in stock, and your cart already has 2 Buffs Lanyard, the most you can order."
        in messages_on(response)
    )


def test_adding_an_out_of_stock_product_says_so(client):
    user = UserFactory()
    product = ProductFactory(title="Physics Circuits Kit", stock=0)
    client.force_login(user)

    response = client.post(add_url(product), {"quantity": 1}, follow=True)

    assert quantity_of(user, product) is None
    assert "Physics Circuits Kit is out of stock, so it isn't in your cart." in messages_on(
        response
    )


@pytest.mark.parametrize(
    ("quantity", "error"),
    [
        ("0", "Enter a quantity of at least 1."),
        ("-2", "Enter a quantity of at least 1."),
        ("two", "Enter a whole number for the quantity."),
        ("1.5", "Enter a whole number for the quantity."),
        ("", "Enter a quantity of at least 1."),
        ("2147483648", "Enter a quantity of at most 2,147,483,647."),
    ],
)
def test_add_to_cart_refuses_bad_quantities(client, quantity, error):
    user = UserFactory()
    client.force_login(user)

    response = client.post(add_url(ProductFactory()), {"quantity": quantity}, follow=True)

    assert error in messages_on(response)
    assert not CartLine.objects.exists()


def test_inactive_or_missing_products_cannot_be_added(client):
    client.force_login(UserFactory())
    inactive = ProductFactory(is_active=False)

    assert client.post(add_url(inactive), {"quantity": 1}).status_code == 404
    assert client.post(reverse("cart:add", args=[999999]), {"quantity": 1}).status_code == 404
    assert not CartLine.objects.exists()


def test_catalog_offers_add_to_cart_only_for_in_stock_products(client):
    in_stock = ProductFactory(title="In Stock Mug", stock=5)
    sold_out = ProductFactory(title="Sold Out Mug", stock=0)
    client.force_login(UserFactory())

    html = client.get(reverse("catalog:index")).content.decode()

    assert f'action="{add_url(in_stock)}"' in html
    assert f'action="{add_url(sold_out)}"' not in html
    assert 'Add to cart<span class="sr-only">: In Stock Mug</span>' in html


def test_catalog_asks_visitors_to_log_in_instead_of_adding(client):
    product = ProductFactory(title="Mug")
    html = client.get(reverse("catalog:index")).content.decode()
    assert add_url(product) not in html
    assert f"{reverse('accounts:login')}?next=/" in html
    assert "Log in to order" in html


# --- Changing quantities without JavaScript --------------------------------------------


def test_quantity_change_without_javascript_redirects_back_with_a_message(client):
    line = CartLineFactory(product=ProductFactory(title="Hoodie", stock=10), quantity=1)
    client.force_login(line.cart.user)

    response = client.post(line_url(line.product), {"quantity": 4})

    assert response.status_code == 302
    assert response["Location"] == CART_URL
    followed = client.get(CART_URL)
    assert "Hoodie: quantity is now 4." in messages_on(followed)
    assert quantity_of(line.cart.user, line.product) == 4


def test_cart_page_forms_are_plain_posts_that_htmx_upgrades(client):
    line = CartLineFactory()
    client.force_login(line.cart.user)

    html = client.get(CART_URL).content.decode()

    url = line_url(line.product)
    # Each form works on its own: method, action and a CSRF token.
    assert html.count(f'action="{url}"') == 2  # quantity form and Remove form
    assert html.count(f'hx-post="{url}"') == 2
    assert html.count('name="csrfmiddlewaretoken"') >= 2
    assert f'<label for="quantity-{line.product.pk}"' in html
    assert 'name="quantity" value="0"' in html  # Remove


def test_remove_takes_the_line_out(client):
    line = CartLineFactory(product=ProductFactory(title="Hoodie"))
    client.force_login(line.cart.user)

    response = client.post(line_url(line.product), {"quantity": 0}, follow=True)

    assert "Removed Hoodie from your cart." in messages_on(response)
    assert quantity_of(line.cart.user, line.product) is None
    assert "Your cart is empty." in response.content.decode()


@pytest.mark.parametrize(
    ("quantity", "error"),
    [
        ("-1", "Enter a quantity of 0 or more. Use 0 or Remove to take an item out."),
        ("abc", "Enter a whole number for the quantity."),
        ("", "Enter a quantity, or 0 to remove the item."),
    ],
)
def test_bad_quantities_are_refused_and_the_line_kept(client, quantity, error):
    line = CartLineFactory(quantity=2)
    client.force_login(line.cart.user)

    response = client.post(line_url(line.product), {"quantity": quantity}, follow=True)

    assert error in messages_on(response)
    assert quantity_of(line.cart.user, line.product) == 2


def test_changing_a_product_not_in_your_cart_is_not_found(client):
    someone_elses = CartLineFactory(quantity=1)
    client.force_login(UserFactory())

    response = client.post(line_url(someone_elses.product), {"quantity": 3})

    assert response.status_code == 404
    assert quantity_of(someone_elses.cart.user, someone_elses.product) == 1


def test_an_inactive_line_cannot_be_changed_and_is_kept(client):
    line = CartLineFactory(product=ProductFactory(is_active=False), quantity=2)
    client.force_login(line.cart.user)

    assert client.post(line_url(line.product), {"quantity": 1}).status_code == 404
    assert quantity_of(line.cart.user, line.product) == 2


def test_cart_page_warns_when_stock_fell_below_a_line(client):
    line = CartLineFactory(product=ProductFactory(stock=5), quantity=2)
    line.product.stock = 1
    line.product.save()
    client.force_login(line.cart.user)

    html = client.get(CART_URL).content.decode()

    assert "Only 1 in stock now. Lower the quantity before you order." in html
    assert quantity_of(line.cart.user, line.product) == 2  # viewing changes nothing


# --- Changing quantities with htmx -----------------------------------------------------


def test_htmx_update_returns_the_cart_with_totals_in_the_live_region(client):
    cart = CartFactory()
    hoodie = ProductFactory(title="Hoodie", price="44.99", stock=10)
    bottle = ProductFactory(title="Bottle", price="14.50", stock=10)
    CartLineFactory(cart=cart, product=hoodie, quantity=1)
    CartLineFactory(cart=cart, product=bottle, quantity=1)
    client.force_login(cart.user)

    response = client.post(line_url(hoodie), {"quantity": 2}, **HTMX)

    html = response.content.decode()
    assert response.status_code == 200
    assert "<html" not in html  # a partial, not a page
    status = re.search(r'<div id="cart-status" hx-swap-oob="innerHTML">(.*?)</div>', html, re.S)
    assert status, "the live region is updated out of band"
    assert "Hoodie: quantity is now 2. Cart total: $104.48 for 3 items." in status.group(1)
    assert '<span id="cart-count" hx-swap-oob="innerHTML">3</span>' in html
    assert "$89.98" in html  # hoodie line total
    assert '<dd id="cart-total">$104.48</dd>' in html


def test_cart_page_has_a_persistent_live_region_outside_the_swapped_area(client):
    line = CartLineFactory()
    client.force_login(line.cart.user)

    html = client.get(CART_URL).content.decode()

    status_at = html.index('<div id="cart-status" role="status"')
    contents_at = html.index('<div id="cart-contents"')
    assert status_at < contents_at
    assert 'hx-target="#cart-contents"' in html


def test_htmx_capped_update_says_so_in_the_live_region(client):
    line = CartLineFactory(product=ProductFactory(title="Hoodie", stock=3), quantity=1)
    client.force_login(line.cart.user)

    html = client.post(line_url(line.product), {"quantity": 10}, **HTMX).content.decode()

    assert "Only 3 are in stock, so Hoodie was set to 3, the most you can order." in html
    assert '<span class="sr-only">Warning:</span>' in html
    assert quantity_of(line.cart.user, line.product) == 3


def test_htmx_bad_quantity_reports_the_error_and_keeps_the_line(client):
    line = CartLineFactory(quantity=2)
    client.force_login(line.cart.user)

    response = client.post(line_url(line.product), {"quantity": "-3"}, **HTMX)

    html = response.content.decode()
    assert response.status_code == 200  # htmx swaps only successful responses
    assert '<span class="sr-only">Error:</span>' in html
    assert "Enter a quantity of 0 or more." in html
    assert quantity_of(line.cart.user, line.product) == 2


def test_htmx_removing_the_last_line_shows_an_empty_cart(client):
    line = CartLineFactory(product=ProductFactory(title="Hoodie"))
    client.force_login(line.cart.user)

    html = client.post(line_url(line.product), {"quantity": 0}, **HTMX).content.decode()

    assert "Removed Hoodie from your cart. Cart total: $0.00 for 0 items." in html
    assert "Your cart is empty." in html
    assert '<span id="cart-count" hx-swap-oob="innerHTML">0</span>' in html


# --- CSRF ---------------------------------------------------------------------------------


def test_cart_changes_need_the_csrf_token():
    line = CartLineFactory(quantity=1)
    client = Client(enforce_csrf_checks=True)
    client.force_login(line.cart.user)

    refused = client.post(line_url(line.product), {"quantity": 3}, **HTMX)
    assert refused.status_code == 403
    assert client.post(add_url(line.product), {"quantity": 1}).status_code == 403
    assert quantity_of(line.cart.user, line.product) == 1

    client.get(CART_URL)  # sets the CSRF cookie, as a browser visit would
    token = client.cookies["csrftoken"].value
    accepted = client.post(line_url(line.product), {"quantity": 3}, HTTP_X_CSRFTOKEN=token, **HTMX)
    assert accepted.status_code == 200
    assert quantity_of(line.cart.user, line.product) == 3


# --- Header "Cart (N)" -----------------------------------------------------------------


def test_header_count_is_total_active_units_not_lines(client):
    cart = CartFactory()
    CartLineFactory(cart=cart, quantity=2)
    CartLineFactory(cart=cart, quantity=3)
    CartLineFactory(cart=cart, product=ProductFactory(is_active=False), quantity=4)
    client.force_login(cart.user)

    html = client.get(reverse("catalog:index")).content.decode()

    assert 'Cart (<span id="cart-count">5</span>' in html


def test_header_shows_cart_zero_without_active_items(client):
    CartLineFactory(
        cart=CartFactory(user=(user := UserFactory())), product=ProductFactory(is_active=False)
    )
    client.force_login(user)
    html = client.get(reverse("catalog:index")).content.decode()
    assert 'Cart (<span id="cart-count">0</span>' in html


def test_visitors_get_no_cart_link_and_no_cart_query(client):
    with CaptureQueriesContext(connection) as queries:
        html = client.get(reverse("catalog:index")).content.decode()
    assert 'id="cart-count"' not in html
    assert not [q for q in queries if "cart_cartline" in q["sql"]]


def test_header_count_costs_one_query_and_none_extra_on_the_cart_page(client):
    line = CartLineFactory(quantity=2)
    client.force_login(line.cart.user)

    with CaptureQueriesContext(connection) as catalog_queries:
        client.get(reverse("catalog:index"))
    with CaptureQueriesContext(connection) as cart_queries:
        client.get(CART_URL)

    def cart_line_queries(captured):
        return [q for q in captured if "cart_cartline" in q["sql"]]

    assert len(cart_line_queries(catalog_queries)) == 1  # the header count
    assert len(cart_line_queries(cart_queries)) == 1  # the contents, reused for the header
