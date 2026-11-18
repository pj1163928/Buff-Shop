from decimal import Decimal

import factory

from catalog.models import Category, Product


class CategoryFactory(factory.django.DjangoModelFactory):
    """A category. Reuses the seeded Textbook / Merchandise / Lab Kit rows by name."""

    class Meta:
        model = Category
        django_get_or_create = ("name",)

    name = "Merchandise"


class ProductFactory(factory.django.DjangoModelFactory):
    """An active, in-stock product with no image."""

    class Meta:
        model = Product

    title = factory.Sequence(lambda n: f"Product {n:03d}")
    category = factory.SubFactory(CategoryFactory)
    description = "A product sold at the Buff Shop."
    price = Decimal("19.99")
    stock = 20
    low_stock_threshold = 5
    is_active = True
