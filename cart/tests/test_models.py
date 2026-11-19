"""Cart model rules: capping, validation, removal, constraints, and never touching stock."""

import pytest
from django.db import IntegrityError, transaction

from accounts.tests.factories import UserFactory
from cart.models import (
    MAX_LINE_QUANTITY,
    Cart,
    CartLine,
    LineNotInCart,
    ProductUnavailable,
)
from cart.tests.factories import CartFactory, CartLineFactory
from catalog.models import Product
from catalog.tests.factories import ProductFactory
from stock.models import StockMovement

pytestmark = pytest.mark.django_db


def quantity_in(cart: Cart, product) -> int | None:
    line = CartLine.objects.filter(cart=cart, product=product).first()
    return line.quantity if line else None


# --- add() ---------------------------------------------------------------------------


def test_add_creates_a_line_then_adds_to_it():
    cart, product = CartFactory(), ProductFactory(stock=10)

    first = cart.add(product)
    second = cart.add(product, 2)

    assert (first.quantity, first.capped, first.removed) == (1, False, False)
    assert (second.quantity, second.capped) == (3, False)
    assert quantity_in(cart, product) == 3
    assert CartLine.objects.count() == 1


def test_add_up_to_exactly_the_stock_is_not_capped():
    cart, product = CartFactory(), ProductFactory(stock=3)
    cart.add(product, 2)

    update = cart.add(product, 1)

    assert (update.quantity, update.capped) == (3, False)


@pytest.mark.parametrize(("already", "adding"), [(None, 5), (2, 2), (3, 1)])
def test_add_caps_the_line_at_stock(already, adding):
    cart, product = CartFactory(), ProductFactory(stock=3)
    if already:
        CartLineFactory(cart=cart, product=product, quantity=already)

    update = cart.add(product, adding)

    assert (update.quantity, update.capped, update.available) == (3, True, 3)
    assert quantity_in(cart, product) == 3


def test_add_lowers_a_line_that_is_already_above_stock():
    """Stock fell after the customer added the item; the next add brings it back in line."""
    cart, product = CartFactory(), ProductFactory(stock=2)
    CartLineFactory(cart=cart, product=product, quantity=5)

    update = cart.add(product)

    assert (update.quantity, update.capped) == (2, True)


def test_add_out_of_stock_product_puts_nothing_in_the_cart():
    cart, product = CartFactory(), ProductFactory(stock=0)

    update = cart.add(product)

    assert (update.quantity, update.capped, update.removed) == (0, True, True)
    assert quantity_in(cart, product) is None


def test_add_out_of_stock_product_removes_an_existing_line():
    cart, product = CartFactory(), ProductFactory(stock=0)
    CartLineFactory(cart=cart, product=product, quantity=2)

    update = cart.add(product)

    assert update.removed
    assert quantity_in(cart, product) is None


def test_add_inactive_product_is_refused():
    cart, product = CartFactory(), ProductFactory(is_active=False)

    with pytest.raises(ProductUnavailable):
        cart.add(product)

    assert not CartLine.objects.exists()


@pytest.mark.parametrize("bad", [0, -1, MAX_LINE_QUANTITY + 1, 1.5, "2", True, None])
def test_add_rejects_anything_but_a_whole_number_of_at_least_one(bad):
    cart, product = CartFactory(), ProductFactory(stock=10)

    with pytest.raises(ValueError):
        cart.add(product, bad)

    assert not CartLine.objects.exists()


# --- set_quantity() -------------------------------------------------------------------


def test_set_quantity_within_stock_is_saved_as_is():
    line = CartLineFactory(product=ProductFactory(stock=5), quantity=1)

    update = line.cart.set_quantity(line.product, 5)

    assert (update.quantity, update.capped, update.removed) == (5, False, False)
    assert quantity_in(line.cart, line.product) == 5


def test_set_quantity_zero_removes_the_line():
    line = CartLineFactory(quantity=2)

    update = line.cart.set_quantity(line.product, 0)

    assert (update.quantity, update.capped, update.removed) == (0, False, True)
    assert quantity_in(line.cart, line.product) is None


def test_removing_a_line_twice_is_harmless():
    line = CartLineFactory()
    line.cart.set_quantity(line.product, 0)

    assert line.cart.set_quantity(line.product, 0).removed


def test_set_quantity_when_out_of_stock_removes_the_line_and_says_capped():
    line = CartLineFactory(product=ProductFactory(stock=0), quantity=2)

    update = line.cart.set_quantity(line.product, 1)

    assert (update.quantity, update.capped, update.removed) == (0, True, True)
    assert quantity_in(line.cart, line.product) is None


def test_set_quantity_needs_an_existing_line():
    cart, product = CartFactory(), ProductFactory()

    with pytest.raises(LineNotInCart):
        cart.set_quantity(product, 2)

    assert not CartLine.objects.exists()


def test_set_quantity_on_an_inactive_product_is_refused_and_the_line_kept():
    line = CartLineFactory(product=ProductFactory(is_active=False), quantity=2)

    with pytest.raises(ProductUnavailable):
        line.cart.set_quantity(line.product, 1)

    assert quantity_in(line.cart, line.product) == 2


@pytest.mark.parametrize("bad", [-1, -5, MAX_LINE_QUANTITY + 1, 2.0, "1", False])
def test_set_quantity_rejects_negatives_and_non_whole_numbers(bad):
    line = CartLineFactory(quantity=2)

    with pytest.raises(ValueError):
        line.cart.set_quantity(line.product, bad)

    assert quantity_in(line.cart, line.product) == 2


# --- The cart never changes stock -----------------------------------------------------


def test_cart_changes_never_touch_stock_or_stock_history():
    cart = CartFactory()
    product = ProductFactory(stock=4)
    out = ProductFactory(stock=0)

    cart.add(product, 2)
    cart.add(product, 10)  # capped
    cart.set_quantity(product, 1)
    cart.set_quantity(product, 9)  # capped
    cart.add(out)  # out of stock
    cart.set_quantity(product, 0)  # removed

    assert Product.objects.get(pk=product.pk).stock == 4
    assert Product.objects.get(pk=out.pk).stock == 0
    assert not StockMovement.objects.exists()


# --- Database constraints -------------------------------------------------------------


def test_database_keeps_one_line_per_cart_and_product():
    line = CartLineFactory()

    with pytest.raises(IntegrityError), transaction.atomic():
        CartLine.objects.create(cart=line.cart, product=line.product, quantity=1)


def test_database_refuses_an_empty_line():
    with pytest.raises(IntegrityError), transaction.atomic():
        CartLineFactory(quantity=0)


def test_one_cart_per_user():
    user = UserFactory()
    assert Cart.objects.for_user(user) == Cart.objects.for_user(user)

    with pytest.raises(IntegrityError), transaction.atomic():
        Cart.objects.create(user=user)


# --- What customers see: contents() and item_count() ----------------------------------


def test_contents_and_count_skip_inactive_lines_but_keep_them():
    cart = CartFactory()
    hoodie = ProductFactory(title="Hoodie", price="40.00")
    kit = ProductFactory(title="Lab Kit", price="10.00")
    CartLineFactory(cart=cart, product=hoodie, quantity=2)
    CartLineFactory(cart=cart, product=kit, quantity=3)
    lines = CartLine.objects.for_user(cart.user)

    assert lines.item_count() == 5  # units, not lines
    assert lines.contents().total == 110

    Product.objects.filter(pk=kit.pk).update(is_active=False)
    assert lines.item_count() == 2
    assert [line.product for line in lines.contents().lines] == [hoodie]
    assert CartLine.objects.filter(product=kit).exists()  # kept, not deleted

    Product.objects.filter(pk=kit.pk).update(is_active=True)
    assert lines.item_count() == 5  # reactivated: back in the cart


def test_item_count_is_zero_without_active_items():
    user = UserFactory()
    assert CartLine.objects.for_user(user).item_count() == 0

    CartLineFactory(cart=CartFactory(user=user), product=ProductFactory(is_active=False))
    assert CartLine.objects.for_user(user).item_count() == 0


def test_contents_are_sorted_by_product_name_with_line_totals():
    cart = CartFactory()
    CartLineFactory(cart=cart, product=ProductFactory(title="Zip Hoodie", price="20.00"))
    CartLineFactory(cart=cart, product=ProductFactory(title="Atlas", price="12.50"), quantity=2)

    contents = CartLine.objects.for_user(cart.user).contents()

    assert [line.product.title for line in contents.lines] == ["Atlas", "Zip Hoodie"]
    assert [str(line.line_total) for line in contents.lines] == ["25.00", "20.00"]
    assert str(contents.total) == "45.00"


def test_contents_only_include_the_users_own_lines():
    mine = CartLineFactory(product=ProductFactory(title="Mine"))
    CartLineFactory(product=ProductFactory(title="Someone else's"))

    contents = CartLine.objects.for_user(mine.cart.user).contents()

    assert [line.product.title for line in contents.lines] == ["Mine"]
