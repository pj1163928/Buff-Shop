import pytest
from django.db import IntegrityError, connection
from django.db.migrations.loader import MigrationLoader

from accounts.models import User

pytestmark = pytest.mark.django_db


def test_custom_user_model_is_in_first_migration():
    loader = MigrationLoader(connection)
    first = loader.get_migration("accounts", "0001_initial")
    created = [op.name for op in first.operations if op.__class__.__name__ == "CreateModel"]
    assert "User" in created


def test_user_has_no_username_and_logs_in_by_email():
    assert User.USERNAME_FIELD == "email"
    assert not hasattr(User, "username") or User.username is None
    assert User.REQUIRED_FIELDS == ["first_name", "last_name"]


def test_manager_lowercases_the_whole_email():
    user = User.objects.create_user("Pat.Buff@WTAMU.Edu ", "x", first_name="Pat", last_name="Buff")
    assert user.email == "pat.buff@wtamu.edu"


def test_save_normalises_email_on_any_code_path():
    user = User(email="  MIXED@Example.COM", first_name="A", last_name="B")
    user.save()
    user.refresh_from_db()
    assert user.email == "mixed@example.com"


def test_database_rejects_case_variant_duplicate_even_without_normalisation():
    User.objects.create_user("pat@wtamu.edu", "x", first_name="Pat", last_name="Buff")
    # Bypass save() normalisation with a raw UPDATE-style bulk path: the
    # case-insensitive unique constraint must still refuse it.
    with pytest.raises(IntegrityError):
        User.objects.bulk_create([User(email="Pat@WTAMU.edu", first_name="Pat", last_name="Two")])


def test_create_user_requires_email():
    with pytest.raises(ValueError):
        User.objects.create_user("", "x", first_name="A", last_name="B")


def test_create_user_is_customer_and_superuser_is_staff():
    customer = User.objects.create_user("c@x.edu", "x", first_name="C", last_name="U")
    boss = User.objects.create_superuser("s@x.edu", "x", first_name="S", last_name="U")
    assert not customer.is_staff and not customer.is_superuser
    assert boss.is_staff and boss.is_superuser


@pytest.mark.parametrize("flag", ["is_staff", "is_superuser"])
def test_create_superuser_refuses_missing_flags(flag):
    with pytest.raises(ValueError):
        User.objects.create_superuser(
            "s@x.edu", "x", first_name="S", last_name="U", **{flag: False}
        )


def test_lookup_by_email_ignores_case():
    user = User.objects.create_user("pat@wtamu.edu", "x", first_name="Pat", last_name="Buff")
    assert User.objects.get_by_natural_key("PAT@Wtamu.EDU") == user


def test_str_is_email():
    assert str(User(email="pat@wtamu.edu")) == "pat@wtamu.edu"
