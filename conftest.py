"""Settings shared by every test."""

import pytest


@pytest.fixture(scope="session")
def django_db_modify_db_settings(django_db_modify_db_settings_parallel_suffix, tmp_path_factory):
    """Run the tests on a SQLite *file*, like the real app, not Django's in-memory default.

    Django's default test database is in-memory with a shared cache. There, a
    second connection that meets a lock fails at once with "database table is
    locked" instead of waiting its turn, so the concurrency tests would be
    testing a database that behaves differently from ``db.sqlite3``. On a file,
    IMMEDIATE transactions and the busy timeout behave exactly as they do in
    development and production.

    ``synchronous=OFF`` only skips waiting for each write to reach the disk
    (the test database is thrown away anyway). Locking is unchanged.
    """
    from django.conf import settings

    database = settings.DATABASES["default"]
    test_db = tmp_path_factory.mktemp("db") / "test.sqlite3"
    database.setdefault("TEST", {})["NAME"] = str(test_db)
    database["OPTIONS"] = {**database["OPTIONS"], "init_command": "PRAGMA synchronous=OFF;"}


@pytest.fixture(autouse=True)
def media_in_tmp_path(settings, tmp_path):
    """Store uploaded and seeded files in a temporary folder, never in ``media/``."""
    settings.MEDIA_ROOT = tmp_path / "media"
