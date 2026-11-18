import pytest

from catalog.models import Product
from catalog.tests.factories import ProductFactory

pytestmark = pytest.mark.django_db


def test_active_products_excludes_inactive():
    active = ProductFactory(title="Buff Hoodie – Medium", stock=10)
    ProductFactory(title="Old Lab Goggles", is_active=False, stock=10)
    sold_out = ProductFactory(title="Chemistry Lab Kit", stock=0)

    assert set(Product.objects.active()) == {active, sold_out}
