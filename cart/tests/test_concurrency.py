"""Simultaneous cart changes on real SQLite, from separate threads and connections.

Same approach as ``stock/tests/test_concurrency.py``: each thread has its own
database connection, and a barrier releases them all at once.
"""

import threading

import pytest
from django.db import connection

from accounts.models import User
from accounts.tests.factories import UserFactory
from cart.models import Cart, CartLine
from catalog.models import Product
from catalog.tests.factories import ProductFactory
from stock.models import StockMovement

# Real commits are needed so each thread's connection sees the others' writes.
pytestmark = pytest.mark.django_db(transaction=True)


def race(user_pk: int, product_pk: int, actions: list[tuple[str, int]]) -> list[str]:
    """Run one cart action per entry, all at once, each in its own thread.

    Each action is ("add", n) or ("set", n). Returns "ok" or "capped" for each,
    or the unexpected error.
    """
    barrier = threading.Barrier(len(actions))
    outcomes: list[str] = []
    lock = threading.Lock()

    def worker(action: str, n: int) -> None:
        try:
            user = User.objects.get(pk=user_pk)
            product = Product.objects.get(pk=product_pk)
            barrier.wait(timeout=10)
            cart = Cart.objects.for_user(user)  # may be created by any thread
            update = cart.add(product, n) if action == "add" else cart.set_quantity(product, n)
            outcome = "capped" if update.capped else "ok"
        except Exception as error:  # noqa: BLE001 - reported to the test, not hidden
            outcome = f"error: {error!r}"
        finally:
            connection.close()
        with lock:
            outcomes.append(outcome)

    threads = [threading.Thread(target=worker, args=a) for a in actions]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)
    return sorted(outcomes)


def test_simultaneous_first_adds_make_one_cart_and_one_line():
    user = UserFactory()
    product = ProductFactory(stock=10)

    outcomes = race(user.pk, product.pk, [("add", 1)] * 4)

    assert outcomes == ["ok"] * 4
    assert Cart.objects.filter(user=user).count() == 1
    assert list(CartLine.objects.values_list("quantity", flat=True)) == [4]  # no add lost


def test_simultaneous_adds_never_go_above_stock():
    user = UserFactory()
    product = ProductFactory(stock=3)

    outcomes = race(user.pk, product.pk, [("add", 1)] * 6)

    assert not [o for o in outcomes if o.startswith("error")]
    assert outcomes.count("ok") == 3  # exactly the 3 units in stock fit
    assert CartLine.objects.get().quantity == 3
    assert Product.objects.get(pk=product.pk).stock == 3  # the cart never touches stock
    assert not StockMovement.objects.exists()


def test_simultaneous_adds_and_sets_end_within_stock_with_one_line():
    user = UserFactory()
    product = ProductFactory(stock=5)
    Cart.objects.for_user(user).add(product, 1)

    outcomes = race(user.pk, product.pk, [("add", 2), ("set", 4), ("add", 3), ("set", 9)])

    assert not [o for o in outcomes if o.startswith("error")]
    assert CartLine.objects.count() == 1
    assert 1 <= CartLine.objects.get().quantity <= 5
