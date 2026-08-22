"""Root URL configuration for Pathgen."""

from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("accounts.urls")),
    path("curriculum/", include("curriculum.urls")),
    path("progress/", include("progress.urls")),
    path("assessment/", include("assessment.urls")),
    path("practice/", include("practice.urls")),
    path("monitoring/", include("monitoring.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
