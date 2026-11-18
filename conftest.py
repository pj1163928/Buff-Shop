"""Settings shared by every test."""

import pytest


@pytest.fixture(autouse=True)
def media_in_tmp_path(settings, tmp_path):
    """Store uploaded and seeded files in a temporary folder, never in ``media/``."""
    settings.MEDIA_ROOT = tmp_path / "media"
