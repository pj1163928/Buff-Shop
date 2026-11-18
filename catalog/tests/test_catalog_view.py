import random
import re
from decimal import Decimal
from unittest import mock

import pytest
from django.urls import reverse

from accounts.tests.factories import UserFactory
from catalog.models import Category, ProductQuerySet
from catalog.tests.factories import ProductFactory

pytestmark = pytest.mark.django_db

URL = reverse("catalog:index")


def titles_on(client, page=1):
    response = client.get(URL, {"page": page})
    assert response.status_code == 200
    return [p.title for p in response.context["products"]]


# --- What each product shows --------------------------------------------------


def test_product_card_shows_name_category_price_and_status_in_words(client):
    ProductFactory(
        title="Buff Hoodie – Medium",
        category=Category.objects.get(name="Merchandise"),
        price=Decimal("44.99"),
        stock=3,
    )
    html = client.get(URL).content.decode()
    assert "Buff Hoodie – Medium" in html
    assert "Merchandise" in html
    assert "$44.99" in html
    assert "Low Stock — act soon" in html


@pytest.mark.parametrize(
    ("stock", "label"), [(0, "Out of Stock"), (5, "Low Stock — act soon"), (6, "In Stock")]
)
def test_status_is_text_with_an_icon_not_colour_alone(client, stock, label):
    ProductFactory(stock=stock)
    html = client.get(URL).content.decode()
    badge = re.search(rf"<p class=[^>]*>(<svg[^>]*>).*?</svg><span>{label}</span></p>", html)
    assert badge, "status badge should be an icon followed by the status in words"
    assert 'aria-hidden="true"' in badge.group(1)  # icon is decoration; the words carry meaning


def test_out_of_stock_active_products_are_listed(client):
    ProductFactory(title="Physics Circuits Kit", stock=0)
    html = client.get(URL).content.decode()
    assert "Physics Circuits Kit" in html
    assert "Out of Stock" in html


def test_inactive_products_never_appear(client):
    ProductFactory(title="Visible Mug")
    ProductFactory(title="Discontinued Scarf", is_active=False)
    html = client.get(URL).content.decode()
    assert "Visible Mug" in html
    assert "Discontinued Scarf" not in html


def test_product_without_image_shows_placeholder_with_alt_text(client):
    ProductFactory(title="Buffs Lanyard")
    html = client.get(URL).content.decode()
    assert 'src="/static/img/product-placeholder.svg" alt="No photo available"' in html


def test_product_with_image_uses_its_alt_text(client):
    ProductFactory(image="products/abc.png", alt_text="Maroon hoodie, front view")
    html = client.get(URL).content.decode()
    assert 'src="/media/products/abc.png" alt="Maroon hoodie, front view"' in html


def test_empty_catalog_says_so(client):
    html = client.get(URL).content.decode()
    assert "No products are available right now." in html


def test_visitors_are_invited_to_log_in_but_customers_are_not(client):
    ProductFactory()
    assert "to order. Anyone can browse." in client.get(URL).content.decode()
    client.force_login(UserFactory())
    assert "to order. Anyone can browse." not in client.get(URL).content.decode()


# --- The catalog goes through the shared helper ------------------------------


def test_catalog_lists_exactly_what_the_active_products_helper_returns(client):
    """If the view filtered products itself, "Hidden By Helper" would appear."""
    ProductFactory(title="Chosen By Helper")
    ProductFactory(title="Hidden By Helper")

    def only_chosen(self):
        return self.filter(title="Chosen By Helper")

    with mock.patch.object(ProductQuerySet, "active", only_chosen):
        assert titles_on(client) == ["Chosen By Helper"]


# --- Pagination and sorting -------------------------------------------------------


def test_exactly_twelve_products_fit_on_one_page(client):
    ProductFactory.create_batch(12)
    response = client.get(URL)
    assert len(response.context["products"]) == 12
    assert response.context["is_paginated"] is False
    html = response.content.decode()
    assert "Page 1 of" not in html
    assert 'rel="next"' not in html


def test_thirteen_products_make_two_pages(client):
    ProductFactory.create_batch(13)
    response = client.get(URL)
    html = response.content.decode()
    assert len(response.context["products"]) == 12
    assert "Page 1 of 2" in html
    assert 'href="?page=2" rel="next"' in html
    assert 'rel="prev"' not in html
    assert "Showing 1–12 of 13 products" in html

    page_two = client.get(URL, {"page": 2})
    html = page_two.content.decode()
    assert len(page_two.context["products"]) == 1
    assert "Page 2 of 2" in html
    assert 'href="?page=1" rel="prev"' in html
    assert 'rel="next"' not in html


def test_inactive_products_do_not_affect_pagination(client):
    ProductFactory.create_batch(12)
    ProductFactory.create_batch(3, is_active=False)
    response = client.get(URL)
    assert len(response.context["products"]) == 12
    assert response.context["is_paginated"] is False
    assert "of 12 products" in response.content.decode()


def test_out_of_stock_products_count_and_show_across_pages(client):
    for n in range(13):
        ProductFactory(title=f"Item {n:02d}", stock=0 if n in (0, 12) else 10)
    assert "Item 00" in titles_on(client, 1)
    assert titles_on(client, 2) == ["Item 12"]


def test_sorted_by_name_consistently_across_pages(client):
    names = [f"Product {chr(65 + n % 13)}" for n in range(26)]  # every name used twice
    random.Random(4360).shuffle(names)
    for name in names:
        ProductFactory(title=name)

    pages = [client.get(URL, {"page": n}).context["products"] for n in (1, 2, 3)]
    seen = [(p.title, p.pk) for page in pages for p in page]

    assert [len(page) for page in pages] == [12, 12, 2]
    assert seen == sorted(seen)  # by name, ties by id: one fixed order
    assert len(set(seen)) == 26  # no product repeated or skipped between pages


def test_page_past_the_end_is_not_found(client):
    ProductFactory.create_batch(3)
    assert client.get(URL, {"page": 2}).status_code == 404
