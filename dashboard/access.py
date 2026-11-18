"""The one staff-only access check for the dashboard.

Every dashboard view inherits ``StaffRequiredMixin`` (or
``SuperuserRequiredMixin``) as its **first** base class, so the check runs in
``dispatch()`` before any handler, for every HTTP method and before any object
is looked up:

* anonymous visitors are redirected to log in, then sent back;
* logged-in users without the role get 403 ("access denied").

``dashboard/tests/test_access.py`` walks every dashboard route to prove it.
"""

from django.contrib.auth.mixins import UserPassesTestMixin


class StaffRequiredMixin(UserPassesTestMixin):
    """Allow active shop staff (``is_staff``) only."""

    def test_func(self) -> bool:
        user = self.request.user
        return user.is_authenticated and user.is_active and user.is_staff


class SuperuserRequiredMixin(StaffRequiredMixin):
    """Allow the superuser only. Plain staff get 403, like customers."""

    def test_func(self) -> bool:
        return super().test_func() and self.request.user.is_superuser
