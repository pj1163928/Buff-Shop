"""The cart's two critical rules, built test-first (plan Phase 5, TDD)."""

from decimal import Decimal

import pytest
from django.urls import reverse

from cart.tests.factories import CartLineFactory
from catalog.tests.factories import ProductFactory

pytestmark = pytest.mark.django_db


def test_cart_quantity_capped_at_stock(client):
    product = ProductFactory(title="Buff Hoodie – Medium", stock=3)
    line = CartLineFactory(product=product, quantity=1)
    client.force_login(line.cart.user)

    response = client.post(reverse("cart:line", args=[product.pk]), {"quantity": 10}, follow=True)

    line.refresh_from_db()
    assert line.quantity == 3
    assert "Only 3 are in stock, so Buff Hoodie – Medium was set to 3" in response.content.decode()


def test_cart_total_ignores_inactive_products(client):
    active = ProductFactory(title="Maroon Water Bottle", price="14.50", stock=10)
    inactive = ProductFactory(
        title="Buff Hoodie – XS (discontinued)", price="39.99", stock=10, is_active=False
    )
    line = CartLineFactory(product=active, quantity=2)
    CartLineFactory(cart=line.cart, product=inactive, quantity=1)
    client.force_login(line.cart.user)

    response = client.get(reverse("cart:detail"))

    html = response.content.decode()
    assert "Maroon Water Bottle" in html
    assert "Buff Hoodie – XS (discontinued)" not in html
    assert [shown.product for shown in response.context["cart"].lines] == [active]
    assert response.context["cart"].total == Decimal("29.00")
    assert response.context["cart"].item_count == 2
    assert "$29.00" in html
