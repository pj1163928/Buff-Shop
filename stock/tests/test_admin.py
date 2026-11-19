"""Stock history in /admin/ is view-only, even for the superuser."""

import pytest
from django.urls import reverse

from accounts.tests.factories import StaffFactory, SuperuserFactory
from catalog.tests.factories import ProductFactory
from stock.models import MovementKind, StockMovement
from stock.services import change_stock

pytestmark = pytest.mark.django_db


@pytest.fixture
def movement():
    return change_stock(ProductFactory(stock=0), 4, kind=MovementKind.RECEIVE, user=StaffFactory())


def test_superuser_can_view_stock_history_in_admin(client, movement):
    client.force_login(SuperuserFactory())
    listing = client.get(reverse("admin:stock_stockmovement_changelist"))
    assert listing.status_code == 200
    assert movement.product.title in listing.content.decode()
    detail = client.get(reverse("admin:stock_stockmovement_change", args=[movement.pk]))
    assert detail.status_code == 200  # shown read-only


def test_stock_history_cannot_be_added_changed_or_deleted_in_admin(client, movement):
    client.force_login(SuperuserFactory())
    assert client.get(reverse("admin:stock_stockmovement_add")).status_code == 403
    delete_url = reverse("admin:stock_stockmovement_delete", args=[movement.pk])
    assert client.post(delete_url, {"post": "yes"}).status_code == 403
    change_url = reverse("admin:stock_stockmovement_change", args=[movement.pk])
    assert client.post(change_url, {"change": 400}).status_code == 403
    assert StockMovement.objects.get(pk=movement.pk).change == 4
