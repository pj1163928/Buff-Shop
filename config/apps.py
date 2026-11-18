from django.contrib.admin.apps import AdminConfig


class SuperuserAdminConfig(AdminConfig):
    """Installs ``SuperuserAdminSite`` as the default ``admin.site``."""

    default_site = "config.admin.SuperuserAdminSite"
