"""The staff stock page: Receive Stock, Stock Adjustment and the stock history."""

import re
import uuid
from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from accounts.tests.factories import StaffFactory
from catalog.tests.factories import ProductFactory
from stock.models import MovementKind, StockMovement
from stock.services import change_stock

pytestmark = pytest.mark.django_db


@pytest.fixture
def staff(db):
    return StaffFactory(first_name="Casey", last_name="Morgan", is_superuser=False)


@pytest.fixture
def staff_client(client, staff):
    client.force_login(staff)
    return client


def stock_url(product) -> str:
    return reverse("dashboard:product_stock", args=[product.pk])


def receive(client, product, amount, reason="", token=None):
    return client.post(
        stock_url(product),
        {
            "action": "receive",
            "receive-amount": amount,
            "receive-reason": reason,
            "receive-token": token or uuid.uuid4(),
        },
    )


def adjust(client, product, amount, reason, token=None):
    return client.post(
        stock_url(product),
        {
            "action": "adjust",
            "adjust-amount": amount,
            "adjust-reason": reason,
            "adjust-token": token or uuid.uuid4(),
        },
    )


def stock_of(product) -> int:
    product.refresh_from_db()
    return product.stock


def page_messages(response) -> list[str]:
    return [str(m) for m in response.context["messages"]]


# --- The page ---------------------------------------------------------------------


def test_stock_page_shows_the_product_its_stock_and_both_forms(staff_client):
    product = ProductFactory(title="Chemistry Lab Kit", stock=3, low_stock_threshold=5)
    html = staff_client.get(stock_url(product)).content.decode()
    assert "Stock: Chemistry Lab Kit" in html
    assert re.search(r"In stock now: <strong[^>]*>3</strong>", html)
    assert "<span>Low Stock</span>" in html  # the shared staff badge
    assert "Receive Stock" in html and "Stock Adjustment" in html
    assert 'name="action" value="receive"' in html
    assert 'name="action" value="adjust"' in html
    assert '<label for="id_receive-amount"' in html
    assert '<label for="id_adjust-reason"' in html
    assert "No stock changes have been recorded for this product yet." in html


def test_each_form_gets_a_fresh_one_time_token(staff_client):
    product = ProductFactory()
    first = staff_client.get(stock_url(product)).content.decode()
    second = staff_client.get(stock_url(product)).content.decode()
    tokens = re.findall(r'name="(?:receive|adjust)-token" value="([0-9a-f-]{36})"', first)
    assert len(set(tokens)) == 2
    assert not set(tokens) & set(re.findall(r'value="([0-9a-f-]{36})"', second))


def test_inactive_products_have_a_stock_page_too(staff_client):
    product = ProductFactory(is_active=False)
    response = staff_client.get(stock_url(product))
    assert response.status_code == 200
    assert "<span>Inactive</span>" in response.content.decode()


def test_unknown_product_is_not_found(staff_client):
    assert staff_client.get(reverse("dashboard:product_stock", args=[999999])).status_code == 404


def test_product_list_links_to_each_stock_page(staff_client):
    product = ProductFactory(title="Maroon Water Bottle")
    html = staff_client.get(reverse("dashboard:product_list")).content.decode()
    assert f'href="{stock_url(product)}"' in html
    assert 'Manage stock<span class="sr-only"> for Maroon Water Bottle</span>' in html


# --- Receive Stock ------------------------------------------------------------------


def test_receive_stock_adds_records_and_redirects_with_a_message(staff_client, staff):
    product = ProductFactory(title="Buffs Lanyard", stock=2)

    response = receive(staff_client, product, 5, reason="Invoice 1042")

    assert response.status_code == 302
    assert response.url == stock_url(product)
    assert stock_of(product) == 7
    movement = StockMovement.objects.get()
    assert (movement.kind, movement.change, movement.resulting_stock) == ("receive", 5, 7)
    assert (movement.user, movement.reason) == (staff, "Invoice 1042")
    page = staff_client.get(response.url)
    assert page_messages(page) == ["Received 5 units for Buffs Lanyard. Stock is now 7."]


def test_receive_stock_note_is_optional(staff_client):
    product = ProductFactory(stock=0)
    assert receive(staff_client, product, 1).status_code == 302
    assert stock_of(product) == 1
    assert StockMovement.objects.get().reason == ""


@pytest.mark.parametrize(
    ("amount", "error"),
    [
        (0, "Enter an amount of at least 1."),
        (-4, "Enter an amount of at least 1."),
        (10_001, "Enter an amount of at most 10,000."),
        ("", "This field is required."),
        ("lots", "Enter a whole number."),
        ("2.5", "Enter a whole number."),
    ],
)
def test_receive_stock_rejects_amounts_that_are_not_positive(staff_client, amount, error):
    product = ProductFactory(stock=4)

    response = receive(staff_client, product, amount)

    assert response.status_code == 200
    form = response.context["receive_form"]
    assert form.errors["amount"] == [error]
    assert error in response.content.decode()
    assert 'aria-invalid="true"' in response.content.decode()
    assert stock_of(product) == 4
    assert not StockMovement.objects.exists()


# --- Stock Adjustment -----------------------------------------------------------------


def test_adjustment_down_with_a_reason(staff_client, staff):
    product = ProductFactory(title="Lab Safety Goggles", stock=10)

    response = adjust(staff_client, product, -2, "2 cracked in storage")

    assert response.status_code == 302
    assert stock_of(product) == 8
    movement = StockMovement.objects.get()
    assert (movement.kind, movement.change, movement.resulting_stock) == ("adjust", -2, 8)
    assert (movement.user, movement.reason) == (staff, "2 cracked in storage")
    assert page_messages(staff_client.get(response.url)) == [
        "Adjusted stock by -2 (2 units removed) for Lab Safety Goggles. Stock is now 8."
    ]


def test_adjustment_up_with_a_reason(staff_client):
    product = ProductFactory(title="Buffs Lanyard", stock=1)
    response = adjust(staff_client, product, 1, "Found one in the back room")
    assert stock_of(product) == 2
    assert page_messages(staff_client.get(response.url)) == [
        "Adjusted stock by +1 (1 unit added) for Buffs Lanyard. Stock is now 2."
    ]


@pytest.mark.parametrize("reason", ["", "   "])
def test_adjustment_rejects_a_missing_reason(staff_client, reason):
    product = ProductFactory(stock=10)

    response = adjust(staff_client, product, -2, reason)

    assert response.status_code == 200
    assert response.context["adjust_form"].errors["reason"] == [
        "Enter a reason for the adjustment."
    ]
    assert stock_of(product) == 10
    assert not StockMovement.objects.exists()


@pytest.mark.parametrize(
    ("amount", "error"),
    [
        (0, "Enter a change other than 0."),
        (-10_001, "Remove at most 10,000 units at a time."),
        (10_001, "Add at most 10,000 units at a time."),
        ("", "This field is required."),
    ],
)
def test_adjustment_rejects_bad_amounts(staff_client, amount, error):
    product = ProductFactory(stock=10)
    response = adjust(staff_client, product, amount, "Recount")
    assert response.context["adjust_form"].errors["amount"] == [error]
    assert stock_of(product) == 10
    assert not StockMovement.objects.exists()


def test_adjustment_that_would_go_below_zero_is_refused_with_the_real_count(staff_client):
    product = ProductFactory(stock=2)

    response = adjust(staff_client, product, -3, "Counted 3 broken")

    assert response.status_code == 200
    assert response.context["adjust_form"].errors["amount"] == [
        "That would take stock below zero: there are only 2 in stock."
    ]
    assert stock_of(product) == 2
    assert not StockMovement.objects.exists()


def test_a_failed_form_keeps_what_was_typed_and_leaves_the_other_form_fresh(staff_client):
    product = ProductFactory(stock=2)
    token = uuid.uuid4()

    response = adjust(staff_client, product, -3, "Counted 3 broken", token=token)

    html = response.content.decode()
    assert 'value="Counted 3 broken"' in html
    assert f'name="adjust-token" value="{token}"' in html  # unused, so still valid
    assert response.context["receive_form"].is_bound is False


def test_a_retry_with_the_same_token_after_a_refusal_works(staff_client):
    """A refused change used nothing up, so fixing the number and resending succeeds."""
    product = ProductFactory(stock=2)
    token = uuid.uuid4()
    adjust(staff_client, product, -3, "Counted broken", token=token)

    response = adjust(staff_client, product, -2, "Counted broken", token=token)

    assert response.status_code == 302
    assert stock_of(product) == 0


# --- Repeated submissions -----------------------------------------------------------


@pytest.mark.parametrize("post", [receive, adjust])
def test_posting_the_same_form_twice_applies_the_change_once(staff_client, post):
    product = ProductFactory(stock=10)
    token = uuid.uuid4()
    args = (3, "Recount") if post is adjust else (3, "")

    # A double click: the second post arrives before the page has reloaded.
    post(staff_client, product, *args, token=token)
    second = post(staff_client, product, *args, token=token)

    assert second.status_code == 302
    assert stock_of(product) == 13
    assert StockMovement.objects.count() == 1
    shown = page_messages(staff_client.get(second.url))
    assert len(shown) == 2
    assert shown[0].endswith("Stock is now 13.")
    assert shown[1] == "That change was already recorded, so it wasn't applied again."


def test_a_form_without_its_token_is_refused(staff_client):
    product = ProductFactory(stock=5)
    response = staff_client.post(
        stock_url(product), {"action": "receive", "receive-amount": 2, "receive-token": ""}
    )
    assert response.status_code == 200
    assert "This form is out of date. Reload the page and try again." in response.content.decode()
    assert stock_of(product) == 5


def test_an_unknown_action_is_a_bad_request(staff_client):
    product = ProductFactory(stock=5)
    response = staff_client.post(stock_url(product), {"action": "delete", "delete-amount": 5})
    assert response.status_code == 400
    assert stock_of(product) == 5


# --- History ------------------------------------------------------------------------


def test_history_lists_movements_newest_first_with_who_when_kind_and_reason(
    staff_client, staff, monkeypatch
):
    product = ProductFactory(stock=0)
    other = StaffFactory(first_name="Jo", last_name="Park")
    start = timezone.now() - timedelta(days=3)
    for days, change, kind, user, reason in [
        (0, 10, MovementKind.RECEIVE, staff, "First delivery"),
        (1, -2, MovementKind.ADJUST, other, "2 damaged"),
        (2, 5, MovementKind.RECEIVE, staff, ""),
    ]:
        monkeypatch.setattr(timezone, "now", lambda d=days: start + timedelta(days=d))
        change_stock(product, change, kind=kind, user=user, reason=reason)
    monkeypatch.undo()

    html = staff_client.get(stock_url(product)).content.decode()

    rows = re.findall(r'<tr id="movement-\d+">(.*?)</tr>', html, re.S)
    cells = [re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", row, re.S) for row in rows]
    text = [[re.sub(r"<[^>]+>", "", c).strip() for c in row] for row in cells]
    assert [row[1:] for row in text] == [
        ["Received", "+5", "13", "Casey Morgan", "—"],
        ["Adjustment", "-2", "8", "Jo Park", "2 damaged"],
        ["Received", "+10", "10", "Casey Morgan", "First delivery"],
    ]
    newest = timezone.localtime(start + timedelta(days=2))
    assert f'datetime="{newest.isoformat()}"' in rows[0]
    assert "Newest first · showing 1–3 of 3 changes" in html


def test_history_shows_only_this_products_movements(staff_client, staff):
    product = ProductFactory(stock=0)
    other = ProductFactory(stock=0)
    change_stock(product, 1, kind=MovementKind.RECEIVE, user=staff)
    change_stock(other, 9, kind=MovementKind.RECEIVE, user=staff)
    response = staff_client.get(stock_url(product))
    assert [m.product for m in response.context["history"]] == [product]


def test_history_is_paginated_25_per_page(staff_client, staff):
    product = ProductFactory(stock=0)
    for _ in range(26):
        change_stock(product, 1, kind=MovementKind.RECEIVE, user=staff)

    first = staff_client.get(stock_url(product))
    second = staff_client.get(stock_url(product), {"page": 2})

    assert [m.resulting_stock for m in first.context["history"]] == list(range(26, 1, -1))
    assert "Page 1 of 2" in first.content.decode()
    assert [m.resulting_stock for m in second.context["history"]] == [1]
