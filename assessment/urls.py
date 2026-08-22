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
    path("posttest/start/", views.posttest_start, name="posttest_start"),
    path("posttest/<uuid:session_id>/", views.posttest, name="posttest"),
    path(
        "posttest/<uuid:session_id>/submit/",
        views.posttest_submit,
        name="posttest_submit",
    ),
    path(
        "posttest/<uuid:session_id>/result/",
        views.posttest_result,
        name="posttest_result",
    ),
    path("completion/", views.completion, name="completion"),
]
