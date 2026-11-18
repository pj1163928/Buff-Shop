import os
import subprocess
import sys
from pathlib import Path

from django.conf import settings

BASE_DIR = Path(settings.BASE_DIR)


def test_sqlite_uses_immediate_transactions_with_busy_timeout():
    db = settings.DATABASES["default"]
    assert db["ENGINE"] == "django.db.backends.sqlite3"
    assert db["OPTIONS"]["transaction_mode"] == "IMMEDIATE"
    assert db["OPTIONS"]["timeout"] == 20
    assert db["ATOMIC_REQUESTS"] is False


def test_dev_uses_console_email_backend():
    # Read the dev module itself: the test runner swaps in an in-memory mailer.
    from config.settings import dev

    assert dev.MAILERS["default"]["BACKEND"] == "django.core.mail.backends.console.EmailBackend"


def test_custom_user_model_is_configured():
    assert settings.AUTH_USER_MODEL == "accounts.User"


def test_four_default_password_validators():
    names = [v["NAME"].rsplit(".", 1)[1] for v in settings.AUTH_PASSWORD_VALIDATORS]
    assert names == [
        "UserAttributeSimilarityValidator",
        "MinimumLengthValidator",
        "CommonPasswordValidator",
        "NumericPasswordValidator",
    ]


def _run_manage(*args, env_overrides):
    env = {k: v for k, v in os.environ.items() if not k.startswith("DJANGO_")}
    env.update(env_overrides)
    return subprocess.run(
        [sys.executable, "manage.py", *args],
        cwd=BASE_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_production_settings_pass_check_deploy():
    result = _run_manage(
        "check",
        "--deploy",
        "--fail-level",
        "WARNING",
        env_overrides={
            "DJANGO_SETTINGS_MODULE": "config.settings.prod",
            "DJANGO_SECRET_KEY": "test-only-" + "k8Qz2xWv9Lm4Rt7Yp3Nc6Bh1Jd5Gf0Sa" * 2,
            "DJANGO_ALLOWED_HOSTS": "shop.example.edu",
        },
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_production_settings_refuse_to_start_without_secret_key():
    result = _run_manage(
        "check",
        env_overrides={
            "DJANGO_SETTINGS_MODULE": "config.settings.prod",
            "DJANGO_ALLOWED_HOSTS": "shop.example.edu",
        },
    )
    assert result.returncode != 0
    assert "DJANGO_SECRET_KEY" in result.stderr
