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
    path(
        "lessons/<slug:lesson_slug>/exercise/submit/",
        views.exercise_submit,
        name="exercise_submit",
    ),
    path(
        "exercise-results/<uuid:session_id>/",
        views.exercise_result,
        name="exercise_result",
    ),
]
