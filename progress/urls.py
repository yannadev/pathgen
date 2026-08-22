"""Student dashboard and learning-path routes."""

from django.urls import path

from progress import views


app_name = "progress"

urlpatterns = [
    path("", views.student_dashboard, name="student_dashboard"),
    path("lessons/", views.lesson_path, name="lesson_path"),
]
