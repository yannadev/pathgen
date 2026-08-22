"""Teacher and admin monitoring routes."""

from django.urls import path

from monitoring import views


app_name = "monitoring"

urlpatterns = [
    path("teacher/", views.teacher_dashboard, name="teacher_dashboard"),
    path("admin/", views.admin_dashboard, name="admin_dashboard"),
]
