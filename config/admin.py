"""Django's built-in admin, restricted to the superuser.

Plain staff use the custom dashboard instead. The default admin lets in anyone
with ``is_staff``; this site lets in only an active superuser, on every admin
page and action, and its login form refuses everyone else too.

It is installed as the default ``admin.site`` by ``config.apps.SuperuserAdminConfig``,
so the existing ``@admin.register`` calls (User, Category, Product) still work.
"""

from django.contrib.admin import AdminSite
from django.contrib.admin.forms import AdminAuthenticationForm
from django.core.exceptions import ValidationError


class SuperuserAdminAuthenticationForm(AdminAuthenticationForm):
    """The admin login form, refusing anyone who isn't a superuser."""

    error_messages = {
        **AdminAuthenticationForm.error_messages,
        "invalid_login": (
            "Please enter the correct %(username)s and password for a superuser account."
        ),
    }

    def confirm_login_allowed(self, user) -> None:
        super().confirm_login_allowed(user)
        if not user.is_superuser:
            raise ValidationError(
                self.error_messages["invalid_login"],
                code="invalid_login",
                params={"username": self.username_field.verbose_name},
            )


class SuperuserAdminSite(AdminSite):
    """The admin site, for the superuser only."""

    login_form = SuperuserAdminAuthenticationForm
    site_header = "Buff Shop admin (superuser only)"
    site_title = "Buff Shop admin"

    def has_permission(self, request) -> bool:
        return request.user.is_active and request.user.is_superuser
