import io
import os
import subprocess
import sys

import pytest
from django.conf import settings
from django.core.files import File
from django.core.management import CommandError, call_command
from PIL import Image

from accounts.models import User
from catalog.images import validate_product_image
from catalog.models import Product, StockStatus
from demo.seed import DEMO_ACCOUNTS, DEMO_IMAGE_DIR, DEMO_PRODUCTS, stock_history_for
from stock.models import MovementKind, StockMovement

pytestmark = pytest.mark.django_db

OWNER, STAFF, ALEX = DEMO_ACCOUNTS[0], DEMO_ACCOUNTS[1], DEMO_ACCOUNTS[2]


def seed() -> str:
    out = io.StringIO()
    call_command("seed_demo", stdout=out)
    return out.getvalue()


# --- What it creates --------------------------------------------------------------


def test_seed_creates_demo_accounts_with_the_right_roles():
    seed()
    owner = User.objects.get(email=OWNER.email)
    staff = User.objects.get(email=STAFF.email)
    customers = User.objects.filter(is_staff=False, email__endswith="@buffshop.test")
    assert owner.is_superuser and owner.is_staff
    assert staff.is_staff and not staff.is_superuser
    assert customers.count() == 3
    for account in DEMO_ACCOUNTS:
        assert User.objects.get(email=account.email).check_password(account.password)


def test_seed_creates_about_fifteen_products_with_every_stock_status():
    seed()
    active = list(Product.objects.active())
    assert len(active) == 15
    statuses = {p.stock_status for p in active}
    assert statuses == {StockStatus.IN_STOCK, StockStatus.LOW_STOCK, StockStatus.OUT_OF_STOCK}
    assert {p.category.name for p in active} == {"Textbook", "Merchandise", "Lab Kit"}
    assert Product.objects.filter(is_active=False).count() == 1


def test_seed_prints_the_demo_logins():
    output = seed()
    assert "DEVELOPMENT ONLY" in output
    for account in DEMO_ACCOUNTS:
        assert account.email in output
        assert account.password in output


# --- Idempotency and protecting existing data -----------------------------------


def test_running_twice_creates_no_duplicates():
    seed()
    counts = (User.objects.count(), Product.objects.count())
    output = seed()
    assert (User.objects.count(), Product.objects.count()) == counts
    assert "0 created, 16 already there" in output


def test_rerun_never_overwrites_stock_or_reactivates_products():
    seed()
    hoodie = Product.objects.get(title="Buff Hoodie – Small")
    Product.objects.filter(pk=hoodie.pk).update(stock=99, is_active=False)
    discontinued = Product.objects.get(is_active=False, title__contains="discontinued")

    seed()

    hoodie.refresh_from_db()
    discontinued.refresh_from_db()
    assert hoodie.stock == 99
    assert hoodie.is_active is False
    assert discontinued.is_active is False


def test_rerun_never_overwrites_an_existing_superuser_password():
    User.objects.create_superuser(
        OWNER.email, "Developers-Own-Secret-9", first_name="Real", last_name="Owner"
    )
    output = seed()
    owner = User.objects.get(email=OWNER.email)
    assert owner.check_password("Developers-Own-Secret-9")
    assert owner.first_name == "Real"
    assert OWNER.password not in output
    assert "password was changed, not shown" in output


def test_rerun_shows_superuser_password_only_while_it_is_still_the_demo_one():
    seed()
    assert OWNER.password in seed()


def test_rerun_resets_designated_demo_accounts_only():
    seed()
    alex = User.objects.get(email=ALEX.email)
    alex.set_password("Changed-By-Tester-1")
    alex.first_name = "Changed"
    alex.save()
    outsider = User.objects.create_user(
        "dev@example.edu", "Developer-Keeps-This-1", first_name="Dev", last_name="Person"
    )

    seed()

    alex.refresh_from_db()
    outsider.refresh_from_db()
    assert alex.check_password(ALEX.password)
    assert alex.first_name == ALEX.first_name
    assert outsider.check_password("Developer-Keeps-This-1")


def test_demo_email_that_belongs_to_a_superuser_is_skipped():
    User.objects.create_superuser(
        STAFF.email, "Promoted-Secret-77", first_name="Promoted", last_name="Person"
    )
    output = seed()
    user = User.objects.get(email=STAFF.email)
    assert user.is_superuser
    assert user.check_password("Promoted-Secret-77")
    assert STAFF.password not in output


# --- Refusing to run outside development ----------------------------------------------


def test_refuses_when_settings_do_not_allow_it(settings):
    settings.ALLOW_DEMO_SEED = False
    with pytest.raises(CommandError, match="development only"):
        call_command("seed_demo", stdout=io.StringIO())
    assert not User.objects.exists()
    assert not Product.objects.exists()


def test_refuses_under_production_settings(tmp_path):
    env = {k: v for k, v in os.environ.items() if not k.startswith("DJANGO_")}
    env.update(
        {
            "DJANGO_SETTINGS_MODULE": "config.settings.prod",
            "DJANGO_SECRET_KEY": "test-only-" + "k8Qz2xWv9Lm4Rt7Yp3Nc6Bh1Jd5Gf0Sa" * 2,
            "DJANGO_ALLOWED_HOSTS": "shop.example.edu",
            "DJANGO_SQLITE_PATH": str(tmp_path / "prod.sqlite3"),
        }
    )
    result = subprocess.run(
        [sys.executable, "manage.py", "seed_demo"],
        cwd=settings.BASE_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode != 0
    assert "development only" in result.stderr
    assert not (tmp_path / "prod.sqlite3").exists()


# --- Stock history ----------------------------------------------------------------


def test_every_demo_products_history_adds_up_to_its_demo_stock():
    for item in DEMO_PRODUCTS:
        assert sum(step.change for step in stock_history_for(item)) == item.stock, item.title


def test_seed_reaches_each_demo_stock_through_recorded_history():
    output = seed()
    staff = User.objects.get(email=STAFF.email)
    for item in DEMO_PRODUCTS:
        product = Product.objects.get(title=item.title)
        movements = list(product.stock_movements.order_by("pk"))
        assert product.stock == item.stock, item.title
        assert sum(m.change for m in movements) == item.stock
        assert all(m.user == staff for m in movements)
        if movements:
            assert movements[-1].resulting_stock == item.stock
    expected = sum(len(stock_history_for(item)) for item in DEMO_PRODUCTS)
    assert f"Stock history: {expected} changes recorded" in output


def test_seed_creates_receive_and_adjust_history_with_reasons():
    seed()
    adjustments = StockMovement.objects.filter(kind=MovementKind.ADJUST)
    assert StockMovement.objects.filter(kind=MovementKind.RECEIVE).exists()
    assert adjustments.filter(change__lt=0).exists()
    assert adjustments.filter(change__gt=0).exists()
    assert all(a.reason for a in adjustments)
    goggles = Product.objects.get(title="Lab Safety Goggles")
    assert [(m.kind, m.change) for m in goggles.stock_movements.order_by("pk")] == [
        ("receive", 24),
        ("receive", 8),
        ("adjust", -2),
    ]


def test_rerun_records_no_new_history_and_leaves_stock_alone():
    seed()
    before = StockMovement.objects.count()
    stock = dict(Product.objects.values_list("title", "stock"))

    output = seed()

    assert StockMovement.objects.count() == before
    assert dict(Product.objects.values_list("title", "stock")) == stock
    assert "Stock history: 0 changes recorded" in output


def test_existing_products_get_no_history():
    """A database seeded before Phase 4 keeps its stock exactly as it was."""
    seed()
    hoodie = Product.objects.get(title="Buff Hoodie – Small")
    hoodie_movements = hoodie.stock_movements.count()
    Product.objects.filter(pk=hoodie.pk).update(stock=50)  # e.g. counted by hand

    seed()

    hoodie.refresh_from_db()
    assert hoodie.stock == 50
    assert hoodie.stock_movements.count() == hoodie_movements


# --- Product photos -------------------------------------------------------------


def media_files(settings) -> list:
    root = settings.MEDIA_ROOT
    return sorted(p for p in root.rglob("*") if p.is_file()) if root.exists() else []


def test_every_demo_product_gets_its_photo_with_alt_text(settings):
    output = seed()
    for item in DEMO_PRODUCTS:
        product = Product.objects.get(title=item.title)
        assert product.image, item.title
        assert (settings.MEDIA_ROOT / product.image.name).is_file()
        assert product.image.name.startswith("products/")
        assert product.image.name != f"products/{item.image}"  # stored under a random name
        assert product.alt_text == item.alt_text != product.title
    assert f"Product photos: {len(DEMO_PRODUCTS)} attached" in output


def test_rerun_attaches_no_new_photos(settings):
    seed()
    names = {p.title: p.image.name for p in Product.objects.all()}
    files = media_files(settings)

    output = seed()

    assert {p.title: p.image.name for p in Product.objects.all()} == names
    assert media_files(settings) == files
    assert "Product photos: 0 attached" in output


def test_an_existing_image_is_never_replaced():
    seed()
    hoodie = Product.objects.get(title="Buff Hoodie – Small")
    staff_photo = DEMO_IMAGE_DIR.joinpath("lanyard.jpg").read_bytes()  # any real image
    hoodie.image = File(io.BytesIO(staff_photo), "staff-upload.jpg")
    hoodie.alt_text = "Staff photo of the hoodie"
    hoodie.save()
    uploaded_name = hoodie.image.name

    output = seed()

    hoodie.refresh_from_db()
    assert hoodie.image.name == uploaded_name
    assert hoodie.alt_text == "Staff photo of the hoodie"
    assert "Product photos: 0 attached" in output


def test_a_photo_whose_file_went_missing_is_attached_again(settings):
    seed()
    bottle = Product.objects.get(title="Maroon Water Bottle")
    (settings.MEDIA_ROOT / bottle.image.name).unlink()

    seed()

    bottle.refresh_from_db()
    assert (settings.MEDIA_ROOT / bottle.image.name).is_file()


def test_demo_photos_are_valid_small_and_credited():
    credits = DEMO_IMAGE_DIR.joinpath("CREDITS.md").read_text()
    for name in {item.image for item in DEMO_PRODUCTS}:
        path = DEMO_IMAGE_DIR / name
        with Image.open(path) as photo:
            assert photo.format == "JPEG"
            assert photo.width <= 800
        validate_product_image(File(path.open("rb"), name))  # the upload rules accept it
        assert f"`{name}`" in credits, f"{name} has no credit in CREDITS.md"


# --- Alex's demo cart ----------------------------------------------------------------


def alex_cart_lines():
    from cart.models import CartLine

    return CartLine.objects.filter(cart__user__email=ALEX.email)


def test_seed_fills_alex_cart_with_active_items_and_one_hidden_discontinued_one():
    output = seed()

    lines = alex_cart_lines()
    assert lines.count() == 4
    assert lines.item_count() == 5  # active units, shown as "Cart (5)"
    assert [line.product.title for line in lines.contents().lines] == [
        "Buff Hoodie – Medium",
        "Chemistry Lab Kit",
        "Lab Safety Goggles",
    ]
    assert lines.filter(product__is_active=False).count() == 1
    assert "Cart: 4 lines put in alex@buffshop.test's cart" in output
    # Every active line is within stock.
    assert all(line.quantity <= line.product.stock for line in lines.contents().lines)


def test_seeded_cart_changes_no_stock():
    seed()
    for title in ("Buff Hoodie – Medium", "Chemistry Lab Kit", "Lab Safety Goggles"):
        product = Product.objects.get(title=title)
        assert not StockMovement.objects.filter(product=product, kind=MovementKind.CHECKOUT)
    assert Product.objects.get(title="Buff Hoodie – Medium").stock == 3


def test_rerun_leaves_a_cart_with_items_alone():
    seed()
    lines = alex_cart_lines()
    lines.filter(product__title="Chemistry Lab Kit").delete()
    lines.filter(product__title="Lab Safety Goggles").update(quantity=7)

    output = seed()

    assert lines.count() == 3
    assert lines.get(product__title="Lab Safety Goggles").quantity == 7
    assert "already had items (left unchanged)" in output


def test_rerun_refills_an_emptied_cart():
    seed()
    alex_cart_lines().delete()

    seed()

    assert alex_cart_lines().count() == 4
