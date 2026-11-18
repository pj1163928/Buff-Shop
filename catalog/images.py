"""Product image checks and storage names.

Uploads are checked by Pillow, not by their file name or browser-supplied type,
and stored under a random name. Resizing and compression come in Phase 13.
"""

import uuid
from typing import IO

from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError

MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB

# Pillow format name -> the extension used for the stored file.
ALLOWED_IMAGE_FORMATS = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}


def detect_image_format(file: IO[bytes]) -> str | None:
    """Return Pillow's format name (``"JPEG"``, ``"PNG"``, …) for ``file``, or None.

    Reads the file's contents, so a text file renamed to ``.jpg`` gives None.
    The file position is restored afterwards.
    """
    start = file.tell() if hasattr(file, "tell") else 0
    try:
        file.seek(0)
        with Image.open(file) as image:
            image_format = image.format
            image.verify()
        return image_format
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError):
        return None
    finally:
        file.seek(start)


def validate_product_image(file) -> None:
    """Refuse anything over 5 MB, or anything that isn't really a JPEG, PNG or WebP.

    Raises ``ValidationError`` with a message the person uploading can act on.
    """
    if file.size > MAX_IMAGE_BYTES:
        raise ValidationError(
            "This image is larger than 5 MB. Please upload a smaller file.",
            code="image_too_large",
        )
    if detect_image_format(file) not in ALLOWED_IMAGE_FORMATS:
        raise ValidationError(
            "Upload a JPEG, PNG or WebP image. This file isn't one of those.",
            code="image_wrong_format",
        )


def product_image_path(instance, filename: str) -> str:
    """Storage path for a product image: a random name, never the uploaded one.

    The extension comes from the detected format, not from ``filename``.
    """
    extension = ALLOWED_IMAGE_FORMATS.get(detect_image_format(instance.image.file) or "", "img")
    return f"products/{uuid.uuid4().hex}.{extension}"
