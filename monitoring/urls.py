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
    path("admin/users/", views.user_management, name="user_management"),
    path("admin/users/create/", views.admin_create_user, name="admin_create_user"),
    path(
        "admin/users/<uuid:user_id>/edit/",
        views.admin_edit_user,
        name="admin_edit_user",
    ),
    path(
        "admin/users/<uuid:user_id>/deactivate/",
        views.admin_deactivate_user,
        name="admin_deactivate_user",
    ),
    path(
        "admin/users/<uuid:user_id>/reset-password/",
        views.admin_reset_password,
        name="admin_reset_password",
    ),
    path("admin/classes/create/", views.admin_create_class, name="admin_create_class"),
    path(
        "admin/classes/<uuid:classroom_id>/",
        views.admin_classroom_detail,
        name="admin_classroom_detail",
    ),
    path(
        "admin/classes/<uuid:classroom_id>/edit/",
        views.admin_edit_class,
        name="admin_edit_class",
    ),
    path(
        "admin/classes/<uuid:classroom_id>/students/add/",
        views.admin_add_student,
        name="admin_add_student",
    ),
    path(
        "admin/classes/<uuid:classroom_id>/students/<uuid:student_id>/remove/",
        views.admin_remove_student,
        name="admin_remove_student",
    ),
    path(
        "admin/classes/<uuid:classroom_id>/delete/",
        views.admin_delete_class,
        name="admin_delete_class",
    ),
    path("admin/overrides/", views.admin_override, name="admin_override"),
    path(
        "admin/overrides/reset-pretest/",
        views.admin_reset_pretest,
        name="admin_reset_pretest",
    ),
    path(
        "admin/overrides/force-posttest/",
        views.admin_force_posttest,
        name="admin_force_posttest",
    ),
    path(
        "admin/overrides/extend-time/",
        views.admin_extend_time,
        name="admin_extend_time",
    ),
    path("admin/activity-log/", views.activity_log, name="activity_log"),
]
