"""Root URL configuration. Every app's URLs are named and namespaced."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("", include("catalog.urls")),
]

# Uploaded product images. static() adds nothing when DEBUG is False, so
# production must serve MEDIA_ROOT from the web server.
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
