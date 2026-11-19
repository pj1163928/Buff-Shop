import factory

from accounts.tests.factories import UserFactory
from cart.models import Cart, CartLine
from catalog.tests.factories import ProductFactory


class CartFactory(factory.django.DjangoModelFactory):
    """A customer's (empty) cart."""

    class Meta:
        model = Cart

    user = factory.SubFactory(UserFactory)


class CartLineFactory(factory.django.DjangoModelFactory):
    """One line in a cart. Written straight to the database: no capping at stock."""

    class Meta:
        model = CartLine

    cart = factory.SubFactory(CartFactory)
    product = factory.SubFactory(ProductFactory)
    quantity = 1
