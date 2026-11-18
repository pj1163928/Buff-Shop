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
from demo.seed import DEMO_ACCOUNTS, DEMO_IMAGE_DIR, DEMO_PRODUCTS

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
