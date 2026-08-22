"""Root URL configuration for Pathgen."""

from django.contrib import admin
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
