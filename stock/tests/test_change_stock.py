"""The one safe stock helper, ``stock.services.change_stock()``."""

import uuid

import pytest
from django.db import DatabaseError, IntegrityError, transaction
from django.db.models import ProtectedError
from django.utils import timezone

from accounts.tests.factories import StaffFactory
from catalog.models import Product
from catalog.tests.factories import ProductFactory
from stock.models import ImmutableHistoryError, MovementKind, StockMovement
from stock.services import (
    MAX_STOCK_CHANGE,
    DuplicateSubmission,
    InsufficientStock,
    change_stock,
)

pytestmark = pytest.mark.django_db


# --- TDD: the core stock rules ---------------------------------------------------


def test_stock_change_refused_when_result_would_be_negative():
    product = ProductFactory(stock=2)
    staff = StaffFactory()

    with pytest.raises(InsufficientStock) as refused:
        change_stock(product, -3, kind=MovementKind.ADJUST, user=staff, reason="Counted 3 broken")

    assert refused.value.available == 2
    product.refresh_from_db()
    assert product.stock == 2
    assert not StockMovement.objects.exists()


def test_stock_change_records_history():
    product = ProductFactory(stock=2)
    staff = StaffFactory()
    before = timezone.now()

    change_stock(product, 5, kind=MovementKind.RECEIVE, user=staff)

    product.refresh_from_db()
    assert product.stock == 7
    assert StockMovement.objects.count() == 1
    movement = StockMovement.objects.get()
    assert movement.product == product
    assert movement.change == 5
    assert movement.resulting_stock == 7
    assert movement.kind == MovementKind.RECEIVE
    assert movement.user == staff
    assert before <= movement.created_at <= timezone.now()


# --- Atomicity: stock and history change together or not at all -----------------


def test_failed_history_insert_rolls_back_the_stock_update(monkeypatch):
    product = ProductFactory(stock=4)

    def broken_insert(*args, **kwargs):
        raise DatabaseError("disk full while writing history")

    monkeypatch.setattr(StockMovement.objects, "create", broken_insert)

    with pytest.raises(DatabaseError):
        change_stock(product, 3, kind=MovementKind.RECEIVE, user=StaffFactory())

    assert Product.objects.get(pk=product.pk).stock == 4
    assert not StockMovement.objects.exists()


def test_refused_change_inside_an_outer_transaction_leaves_it_usable():
    """Checkout (Phase 6) will try several lines in one transaction and catch refusals."""
    short = ProductFactory(stock=1)
    plenty = ProductFactory(stock=10)
    staff = StaffFactory()

    with transaction.atomic():
        with pytest.raises(InsufficientStock):
            change_stock(short, -2, kind=MovementKind.ADJUST, user=staff, reason="Broken")
        change_stock(plenty, -2, kind=MovementKind.ADJUST, user=staff, reason="Broken")

    assert Product.objects.get(pk=short.pk).stock == 1
    assert Product.objects.get(pk=plenty.pk).stock == 8
    assert StockMovement.objects.count() == 1


# --- What the helper returns and records ------------------------------------------


def test_taking_stock_to_exactly_zero_is_allowed():
    product = ProductFactory(stock=3)
    movement = change_stock(
        product, -3, kind=MovementKind.ADJUST, user=StaffFactory(), reason="Water damage"
    )
    assert product.stock == 0  # the caller's instance is refreshed
    assert Product.objects.get(pk=product.pk).stock == 0
    assert movement.resulting_stock == 0
    assert movement.reason == "Water damage"


def test_resulting_stock_comes_from_the_database_not_a_stale_instance():
    product = ProductFactory(stock=5)
    stale = Product.objects.get(pk=product.pk)
    Product.objects.filter(pk=product.pk).update(stock=9)  # changed elsewhere meanwhile

    movement = change_stock(stale, 1, kind=MovementKind.RECEIVE, user=StaffFactory())

    assert movement.resulting_stock == 10
    assert stale.stock == 10


def test_a_stale_instance_cannot_take_stock_negative():
    product = ProductFactory(stock=5)
    stale = Product.objects.get(pk=product.pk)
    Product.objects.filter(pk=product.pk).update(stock=1)  # sold meanwhile

    with pytest.raises(InsufficientStock) as refused:
        change_stock(stale, -3, kind=MovementKind.ADJUST, user=StaffFactory(), reason="Lost")

    assert refused.value.available == 1
    assert Product.objects.get(pk=product.pk).stock == 1


def test_reason_is_trimmed_and_optional_for_a_receive():
    product = ProductFactory(stock=0)
    staff = StaffFactory()
    plain = change_stock(product, 4, kind=MovementKind.RECEIVE, user=staff)
    noted = change_stock(
        product, 2, kind=MovementKind.RECEIVE, user=staff, reason="  Late delivery  "
    )
    assert plain.reason == ""
    assert noted.reason == "Late delivery"
    assert product.stock == 6


@pytest.mark.parametrize(
    ("change", "kind", "reason", "message"),
    [
        (0, MovementKind.RECEIVE, "", "changes nothing"),
        (0, MovementKind.ADJUST, "Count", "changes nothing"),
        (-1, MovementKind.RECEIVE, "", "must add stock"),
        (-1, MovementKind.CANCEL, "", "must add stock"),
        (1, MovementKind.CHECKOUT, "", "must remove stock"),
        (-1, MovementKind.ADJUST, "", "needs a reason"),
        (2, MovementKind.ADJUST, "   ", "needs a reason"),
        (MAX_STOCK_CHANGE + 1, MovementKind.RECEIVE, "", "more than 10,000"),
        (-(MAX_STOCK_CHANGE + 1), MovementKind.ADJUST, "Count", "more than 10,000"),
        (1, MovementKind.ADJUST, "x" * 201, "longer than 200"),
        (1.5, MovementKind.RECEIVE, "", "whole number"),
        ("3", MovementKind.RECEIVE, "", "whole number"),
        (True, MovementKind.RECEIVE, "", "whole number"),
        (1, "gift", "", "Unknown kind"),
    ],
)
def test_requests_that_break_the_rules_are_refused(change, kind, reason, message):
    product = ProductFactory(stock=50)

    with pytest.raises(ValueError, match=message):
        change_stock(product, change, kind=kind, user=StaffFactory(), reason=reason)

    assert Product.objects.get(pk=product.pk).stock == 50
    assert not StockMovement.objects.exists()


def test_the_limit_itself_is_allowed():
    product = ProductFactory(stock=MAX_STOCK_CHANGE)
    staff = StaffFactory()
    change_stock(product, MAX_STOCK_CHANGE, kind=MovementKind.RECEIVE, user=staff)
    change_stock(product, -MAX_STOCK_CHANGE, kind=MovementKind.ADJUST, user=staff, reason="Recount")
    assert product.stock == MAX_STOCK_CHANGE


# --- Repeated submissions ---------------------------------------------------------


def test_a_submission_token_can_be_used_only_once():
    product = ProductFactory(stock=0)
    staff = StaffFactory()
    token = uuid.uuid4()

    change_stock(product, 5, kind=MovementKind.RECEIVE, user=staff, submission_token=token)
    with pytest.raises(DuplicateSubmission):
        change_stock(product, 5, kind=MovementKind.RECEIVE, user=staff, submission_token=token)

    assert Product.objects.get(pk=product.pk).stock == 5
    assert StockMovement.objects.count() == 1


def test_the_database_refuses_a_reused_submission_token_on_its_own():
    token = uuid.uuid4()
    first = change_stock(
        ProductFactory(), 1, kind=MovementKind.RECEIVE, user=StaffFactory(), submission_token=token
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        StockMovement.objects.create(
            product=first.product,
            change=1,
            resulting_stock=99,
            kind=MovementKind.RECEIVE,
            user=first.user,
            submission_token=token,
        )


def test_changes_without_a_token_are_never_treated_as_duplicates():
    product = ProductFactory(stock=0)
    staff = StaffFactory()
    change_stock(product, 1, kind=MovementKind.RECEIVE, user=staff)
    change_stock(product, 1, kind=MovementKind.RECEIVE, user=staff)
    assert StockMovement.objects.count() == 2


# --- History is append-only ---------------------------------------------------------


@pytest.fixture
def movement():
    return change_stock(ProductFactory(stock=1), 2, kind=MovementKind.RECEIVE, user=StaffFactory())


def test_a_history_row_cannot_be_edited(movement):
    movement.change = 200
    with pytest.raises(ImmutableHistoryError):
        movement.save()
    with pytest.raises(ImmutableHistoryError):
        StockMovement.objects.filter(pk=movement.pk).update(change=200)
    with pytest.raises(ImmutableHistoryError):
        StockMovement.objects.bulk_update([movement], ["change"])
    assert StockMovement.objects.get(pk=movement.pk).change == 2


def test_a_history_row_cannot_be_deleted(movement):
    with pytest.raises(ImmutableHistoryError):
        movement.delete()
    with pytest.raises(ImmutableHistoryError):
        StockMovement.objects.all().delete()
    assert StockMovement.objects.filter(pk=movement.pk).exists()


def test_a_product_or_user_with_history_cannot_be_deleted(movement):
    with pytest.raises(ProtectedError):
        movement.product.delete()
    with pytest.raises(ProtectedError):
        movement.user.delete()


def test_the_database_refuses_a_zero_change_row():
    product = ProductFactory()
    with pytest.raises(IntegrityError), transaction.atomic():
        StockMovement.objects.create(
            product=product, change=0, resulting_stock=1, kind="adjust", user=StaffFactory()
        )


def test_history_reads_well_in_admin_lists(movement):
    assert str(movement) == f"{movement.product.title} +2 (Received)"
