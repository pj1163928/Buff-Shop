from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction

from catalog.models import Category, Product
from catalog.tests.factories import ProductFactory

pytestmark = pytest.mark.django_db


def test_categories_are_seeded_by_migration():
    names = set(Category.objects.values_list("name", flat=True))
    assert {"Textbook", "Merchandise", "Lab Kit"} <= names


def test_database_rejects_negative_stock_written_directly():
    product = ProductFactory(stock=2)
    with pytest.raises(IntegrityError), transaction.atomic():
        Product.objects.filter(pk=product.pk).update(stock=-1)
    product.refresh_from_db()
    assert product.stock == 2


def test_database_rejects_creating_a_product_with_negative_stock():
    with pytest.raises(IntegrityError), transaction.atomic():
        ProductFactory(stock=-1)


def test_zero_stock_is_allowed():
    product = ProductFactory(stock=0)
    assert product.stock == 0


def test_alt_text_defaults_to_title_when_blank():
    product = ProductFactory(title="Buff Hoodie – Medium", alt_text="   ")
    assert product.alt_text == "Buff Hoodie – Medium"


def test_alt_text_kept_when_given():
    product = ProductFactory(title="Buff Hoodie", alt_text="Maroon hoodie, front view")
    assert product.alt_text == "Maroon hoodie, front view"


def test_product_defaults():
    product = Product.objects.create(
        title="Lab Safety Goggles",
        category=Category.objects.get(name="Lab Kit"),
        price=Decimal("12.99"),
    )
    assert product.low_stock_threshold == 5
    assert product.is_active is True
    assert product.stock == 0
    assert str(product) == "Lab Safety Goggles"


def test_product_stock_status_uses_its_own_threshold():
    assert (
        ProductFactory(stock=6, low_stock_threshold=8).stock_status.label == "Low Stock — act soon"
    )
    assert ProductFactory(stock=2, low_stock_threshold=1).stock_status.label == "In Stock"
    assert ProductFactory(stock=0).stock_status.label == "Out of Stock"
