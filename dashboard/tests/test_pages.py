"""The dashboard pages staff see: home, the product list and its badges."""

import re

import pytest
from django.urls import reverse

from accounts.tests.factories import StaffFactory, UserFactory
from catalog.tests.factories import ProductFactory
from demo.seed import seed_demo

pytestmark = pytest.mark.django_db

PRODUCTS = reverse("dashboard:product_list")


@pytest.fixture
def staff_client(client):
    client.force_login(StaffFactory(is_superuser=False))
    return client


def row_for(html: str, product) -> str:
    """The product list's table row for ``product``."""
    match = re.search(rf'<tr id="product-{product.pk}">(.*?)</tr>', html, re.S)
    assert match, f"no row for {product.title}"
    return match.group(1)


def badges_in(row: str) -> list[str]:
    """The badge words in a row, in order."""
    return re.findall(
        r'<li class="inline-flex[^"]*">\s*<svg[^>]*>.*?</svg><span>([^<]+)</span>', row
    )


# --- Home -----------------------------------------------------------------------


def test_staff_see_the_dashboard_home_with_a_link_to_products(staff_client):
    response = staff_client.get(reverse("dashboard:home"))
    html = response.content.decode()
    assert response.status_code == 200
    assert "Staff dashboard" in html
    assert f'href="{PRODUCTS}"' in html
    assert 'aria-current="page"' in html


def test_dashboard_link_in_header_is_for_staff_only(client):
    dashboard = f'href="{reverse("dashboard:home")}"'
    assert dashboard not in client.get("/").content.decode()
    client.force_login(UserFactory())
    assert dashboard not in client.get("/").content.decode()
    client.force_login(StaffFactory())
    assert dashboard in client.get("/").content.decode()


def test_customers_see_a_plain_access_denied_page(client):
    client.force_login(UserFactory())
    response = client.get(reverse("dashboard:home"))
    assert response.status_code == 403
    assert "Access denied" in response.content.decode()


# --- Product list -----------------------------------------------------------------


def test_product_list_shows_every_product_including_inactive(staff_client):
    live = ProductFactory(title="Maroon Water Bottle")
    hidden = ProductFactory(title="Buff Hoodie – XS", is_active=False)
    html = staff_client.get(PRODUCTS).content.decode()
    assert "Inactive" not in badges_in(row_for(html, live))
    assert "Inactive" in badges_in(row_for(html, hidden))


@pytest.mark.parametrize(
    ("stock", "threshold", "badge"),
    [
        (0, 5, "Out of Stock"),
        (1, 5, "Low Stock"),
        (5, 5, "Low Stock"),
        (6, 5, "In Stock"),
        (2, 1, "In Stock"),  # each product's own threshold
        (0, 0, "Out of Stock"),
    ],
)
def test_stock_badge_follows_the_products_own_threshold(staff_client, stock, threshold, badge):
    product = ProductFactory(stock=stock, low_stock_threshold=threshold)
    row = row_for(staff_client.get(PRODUCTS).content.decode(), product)
    assert badges_in(row) == [badge]


def test_an_inactive_low_stock_product_shows_both_badges(staff_client):
    product = ProductFactory(stock=2, is_active=False)
    row = row_for(staff_client.get(PRODUCTS).content.decode(), product)
    assert badges_in(row) == ["Low Stock", "Inactive"]


def test_badges_are_words_with_a_hidden_icon_not_colour_alone(staff_client):
    product = ProductFactory(stock=1, is_active=False)
    row = row_for(staff_client.get(PRODUCTS).content.decode(), product)
    icons = re.findall(r"<li class=\"inline-flex[^\"]*\">\s*(<svg[^>]*>)", row)
    assert len(icons) == 2
    assert all('aria-hidden="true"' in icon for icon in icons)
    assert "act soon" not in row  # the staff wording is "Low Stock"


def test_row_shows_category_price_stock_and_threshold(staff_client):
    product = ProductFactory(title="Chemistry Lab Kit", stock=9, low_stock_threshold=5)
    row = row_for(staff_client.get(PRODUCTS).content.decode(), product)
    assert "Chemistry Lab Kit" in row
    assert product.category.name in row
    assert f"${product.price}" in row
    cells = re.findall(r"<td[^>]*>([^<]*)</td>", row)
    assert cells == ["9", "5", f"${product.price}", product.category.name]


def test_product_list_is_sorted_by_name_25_per_page(staff_client):
    for n in reversed(range(26)):
        ProductFactory(title=f"Item {n:02d}", is_active=n % 2 == 0)
    first = staff_client.get(PRODUCTS)
    assert [p.title for p in first.context["products"]] == [f"Item {n:02d}" for n in range(25)]
    assert "Page 1 of 2" in first.content.decode()
    second = staff_client.get(PRODUCTS, {"page": 2})
    assert [p.title for p in second.context["products"]] == ["Item 25"]


def test_empty_product_list_says_so(staff_client):
    assert "There are no products yet." in staff_client.get(PRODUCTS).content.decode()


def test_seeded_demo_data_shows_every_badge(staff_client):
    seed_demo()
    html = staff_client.get(PRODUCTS).content.decode()
    shown = set(re.findall(r"<span>(In Stock|Low Stock|Out of Stock|Inactive)</span>", html))
    assert shown == {"In Stock", "Low Stock", "Out of Stock", "Inactive"}
