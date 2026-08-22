"""Exercise and activity routes."""

from django.urls import path

from practice import views

app_name = "practice"
urlpatterns = [
    path(
        "lessons/<slug:lesson_slug>/exercise/start/",
        views.exercise_start,
        name="exercise_start",
    ),
    path(
        "lessons/<slug:lesson_slug>/exercise/",
        views.short_exercise,
        name="short_exercise",
    ),
]
