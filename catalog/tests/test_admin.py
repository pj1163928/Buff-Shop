import pytest
from django.urls import reverse

from accounts.tests.factories import SuperuserFactory
from catalog.models import Category
from catalog.tests.factories import ProductFactory

pytestmark = pytest.mark.django_db


def test_superuser_can_add_a_category_in_admin(client):
    client.force_login(SuperuserFactory())
    response = client.post(reverse("admin:catalog_category_add"), {"name": "Stationery"})
    assert response.status_code == 302
    assert Category.objects.filter(name="Stationery").exists()


def test_admin_product_pages_load_and_stock_is_read_only(client):
    client.force_login(SuperuserFactory())
    product = ProductFactory(stock=7)
    assert client.get(reverse("admin:catalog_product_changelist")).status_code == 200

    change_url = reverse("admin:catalog_product_change", args=[product.pk])
    response = client.get(change_url)
    assert response.status_code == 200
    assert "stock" not in response.context["adminform"].form.fields

    client.post(
        change_url,
        {
            "title": product.title,
            "category": product.category.pk,
            "description": "",
            "price": "19.99",
            "alt_text": product.alt_text,
            "low_stock_threshold": "5",
            "is_active": "on",
            "stock": "999",
        },
    )
    product.refresh_from_db()
    assert product.stock == 7
