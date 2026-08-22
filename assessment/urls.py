"""Pretest and posttest routes."""

from django.urls import path

from assessment import views

app_name = "assessment"
urlpatterns = [
    path("pretest/start/", views.pretest_start, name="pretest_start"),
    path("pretest/<uuid:session_id>/", views.pretest, name="pretest"),
    path(
        "pretest/<uuid:session_id>/submit/",
        views.pretest_submit,
        name="pretest_submit",
    ),
    path(
        "pretest/<uuid:session_id>/result/",
        views.pretest_result,
        name="pretest_result",
    ),
]
