import io
import re

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image

from accounts.tests.factories import SuperuserFactory
from catalog.images import MAX_IMAGE_BYTES, validate_product_image
from catalog.models import Category, Product


def make_image(image_format: str, name: str, size=(40, 30)) -> SimpleUploadedFile:
    buffer = io.BytesIO()
    Image.new("RGB", size, (69, 0, 18)).save(buffer, format=image_format)
    return SimpleUploadedFile(name, buffer.getvalue())


@pytest.mark.parametrize(
    ("image_format", "name"), [("PNG", "a.png"), ("JPEG", "a.jpg"), ("WEBP", "a.webp")]
)
def test_jpeg_png_and_webp_are_accepted(image_format, name):
    validate_product_image(make_image(image_format, name))  # no error


@pytest.mark.parametrize(
    ("upload", "message"),
    [
        (SimpleUploadedFile("notes.jpg", b"just some text, not a picture"), "JPEG, PNG or WebP"),
        (make_image("GIF", "anim.gif"), "JPEG, PNG or WebP"),
        (make_image("BMP", "bitmap.png"), "JPEG, PNG or WebP"),
        (SimpleUploadedFile("huge.png", b"\0" * (MAX_IMAGE_BYTES + 1)), "larger than 5 MB"),
    ],
    ids=["text-renamed-jpg", "gif", "bmp-renamed-png", "over-5mb"],
)
def test_bad_uploads_are_rejected_with_clear_message(upload, message):
    with pytest.raises(ValidationError, match=message):
        validate_product_image(upload)


def test_validation_leaves_file_readable_from_the_start():
    upload = make_image("PNG", "a.png")
    validate_product_image(upload)
    assert upload.read(8) == b"\x89PNG\r\n\x1a\n"


@pytest.mark.django_db
def test_admin_upload_is_stored_under_random_name_in_media(client, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"
    client.force_login(SuperuserFactory())
    # A JPEG with an unsafe, misleading name: the stored name must ignore it.
    upload = make_image("JPEG", "../../static/evil name.png")
    response = client.post(
        reverse("admin:catalog_product_add"),
        {
            "title": "Buff Cap",
            "category": Category.objects.get(name="Merchandise").pk,
            "description": "",
            "price": "15.00",
            "image": upload,
            "alt_text": "",
            "low_stock_threshold": "5",
            "is_active": "on",
        },
    )
    assert response.status_code == 302
    product = Product.objects.get(title="Buff Cap")
    assert re.fullmatch(r"products/[0-9a-f]{32}\.jpg", product.image.name)
    stored = settings.MEDIA_ROOT / product.image.name
    assert stored.is_file()
    assert settings.STATICFILES_DIRS[0] not in stored.parents


@pytest.mark.django_db
def test_admin_rejects_renamed_text_file(client, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"
    client.force_login(SuperuserFactory())
    response = client.post(
        reverse("admin:catalog_product_add"),
        {
            "title": "Buff Cap",
            "category": Category.objects.get(name="Merchandise").pk,
            "price": "15.00",
            "image": SimpleUploadedFile("cap.jpg", b"not an image"),
            "low_stock_threshold": "5",
        },
    )
    assert response.status_code == 200
    assert not Product.objects.filter(title="Buff Cap").exists()
