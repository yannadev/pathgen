"""Teacher and admin monitoring routes."""

from django.urls import path

from monitoring import views


app_name = "monitoring"

urlpatterns = [
    path("teacher/", views.teacher_dashboard, name="teacher_dashboard"),
    path(
        "teacher/classrooms/",
        views.teacher_classroom_list,
        name="teacher_classroom_list",
    ),
    path(
        "teacher/classrooms/<uuid:classroom_id>/",
        views.classroom_detail,
        name="classroom_detail",
    ),
    path(
        "teacher/students/<uuid:student_id>/",
        views.student_detail,
        name="student_detail",
    ),
    path("teacher/content/", views.content_page, name="content_page"),
    path(
        "teacher/content/lessons/<slug:slug>/",
        views.lesson_page,
        name="teacher_lesson_page",
    ),
    path(
        "teacher/content/activities/<uuid:activity_id>/",
        views.activity_page,
        name="teacher_activity_page",
    ),
    path("admin/", views.admin_dashboard, name="admin_dashboard"),
]
