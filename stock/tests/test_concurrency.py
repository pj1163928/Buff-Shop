"""Simultaneous stock changes on real SQLite, from separate threads and connections.

These tests check what actually happens when writers race, rather than
assuming the IMMEDIATE transaction setting works. Each thread gets its own
database connection, and a barrier releases them all at once.
"""

import threading

import pytest
from django.db import connection

from accounts.tests.factories import StaffFactory
from catalog.models import Product
from catalog.tests.factories import ProductFactory
from stock.models import MovementKind, StockMovement
from stock.services import InsufficientStock, change_stock

# Real commits are needed so each thread's connection sees the others' writes.
pytestmark = pytest.mark.django_db(transaction=True)


def race(product_pk: int, user, changes: list[int]) -> list[str]:
    """Run one ``change_stock`` per entry in ``changes``, all at once.

    Returns each thread's outcome: "ok", "refused", or the unexpected error.
    """
    barrier = threading.Barrier(len(changes))
    outcomes: list[str] = []
    lock = threading.Lock()

    def worker(change: int) -> None:
        try:
            product = Product.objects.get(pk=product_pk)  # each thread's own copy
            barrier.wait(timeout=10)
            try:
                change_stock(product, change, kind=MovementKind.ADJUST, user=user, reason="Race")
                outcome = "ok"
            except InsufficientStock:
                outcome = "refused"
        except Exception as error:  # noqa: BLE001 - reported to the test, not hidden
            outcome = f"error: {error!r}"
        finally:
            connection.close()
        with lock:
            outcomes.append(outcome)

    threads = [threading.Thread(target=worker, args=(c,)) for c in changes]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)
    return sorted(outcomes)


def test_two_simultaneous_deductions_of_the_last_unit_only_one_succeeds():
    product = ProductFactory(stock=1)
    staff = StaffFactory()

    outcomes = race(product.pk, staff, [-1, -1])

    assert outcomes == ["ok", "refused"]
    assert Product.objects.get(pk=product.pk).stock == 0
    assert StockMovement.objects.count() == 1


def test_many_simultaneous_deductions_never_take_stock_negative():
    product = ProductFactory(stock=3)
    staff = StaffFactory()

    outcomes = race(product.pk, staff, [-1] * 8)

    assert outcomes == ["ok"] * 3 + ["refused"] * 5
    assert Product.objects.get(pk=product.pk).stock == 0
    movements = list(StockMovement.objects.order_by("pk"))
    assert len(movements) == 3
    # Every history row's resulting stock is a real, distinct step: 2, 1, 0.
    assert [m.resulting_stock for m in movements] == [2, 1, 0]


def test_simultaneous_receives_and_deductions_add_up_exactly():
    product = ProductFactory(stock=6)
    staff = StaffFactory()

    # Even if all the deductions win the race, 6 - 2 - 3 - 1 = 0, so all succeed.
    outcomes = race(product.pk, staff, [+4, -2, +1, -3, -1, +2])

    assert outcomes == ["ok"] * 6
    assert Product.objects.get(pk=product.pk).stock == 7
    # The history is one unbroken chain: each row's result is the last result
    # plus its change, so no two writers ever saw the same starting stock.
    running = 6
    for movement in StockMovement.objects.order_by("pk"):
        running += movement.change
        assert movement.resulting_stock == running
    assert running == 7
