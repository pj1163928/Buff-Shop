from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.db.models.functions import Lower


def normalize_email(email: str | None) -> str:
    """Return ``email`` trimmed and fully lowercased, the one stored form of an email.

    Every path that creates or changes a user (sign-up, login lookup, the
    manager, Django admin, the ORM) uses this, so ``Pat@WTAMU.edu`` and
    ``pat@wtamu.edu`` always mean the same account.
    """
    return (email or "").strip().lower()


class UserManager(BaseUserManager):
    """Manager for the email-login User. There is no username."""

    use_in_migrations = True

    def normalize_email(self, email: str | None) -> str:
        """Lowercase the whole address, not just the domain as Django does."""
        return normalize_email(email)

    def get_by_natural_key(self, username: str) -> "User":
        """Look a user up by email, ignoring case (used by authentication)."""
        return self.get(email=normalize_email(username))

    def _create_user(self, email: str, password: str | None, **extra_fields) -> "User":
        if not email:
            raise ValueError("An email address is required.")
        user = self.model(email=self.normalize_email(email), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email: str, password: str | None = None, **extra_fields) -> "User":
        """Create a customer account (not staff, not superuser)."""
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email: str, password: str | None = None, **extra_fields) -> "User":
        """Create the superuser, who is also staff."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields["is_staff"] is not True:
            raise ValueError("A superuser must have is_staff=True.")
        if extra_fields["is_superuser"] is not True:
            raise ValueError("A superuser must have is_superuser=True.")
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """A shop user. Email is the login; first and last name are required.

    ``is_staff`` means shop staff (dashboard access). ``is_superuser`` alone
    reaches overrides, staff management and Django admin.
    """

    username = None
    email = models.EmailField("email address", unique=True)
    first_name = models.CharField("first name", max_length=150)
    last_name = models.CharField("last name", max_length=150)

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    objects = UserManager()

    class Meta:
        verbose_name = "user"
        verbose_name_plural = "users"
        constraints = [
            # Second line of defence behind normalisation: the database itself
            # refuses two emails that differ only by case.
            models.UniqueConstraint(Lower("email"), name="accounts_user_email_ci_unique"),
        ]

    def __str__(self) -> str:
        return self.email

    # clean() is inherited: AbstractUser.clean() calls objects.normalize_email(),
    # so model forms (sign-up, admin) see the lowercased email before they check
    # uniqueness.

    def save(self, *args, **kwargs) -> None:
        """Normalise the email on every save, whichever code path made the change."""
        self.email = normalize_email(self.email)
        super().save(*args, **kwargs)
