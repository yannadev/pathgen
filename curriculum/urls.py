"""Curriculum routes."""

from django.urls import path

from curriculum import views

app_name = "curriculum"
urlpatterns = [
    path("lessons/<slug:slug>/", views.lesson_page, name="lesson_page"),
]
