"""Authentication, account, class, and profile routes."""

from django.urls import path

from accounts import views


app_name = "accounts"

urlpatterns = [
    path("", views.login_view, name="login"),
    path("home/", views.home_redirect, name="home"),
    path("change-password/", views.change_password, name="change_password"),
    path("profile/student/", views.student_profile, name="student_profile"),
    path("profile/teacher/", views.teacher_profile, name="teacher_profile"),
    path("profile/admin/", views.admin_profile, name="admin_profile"),
    path("heartbeat/", views.heartbeat, name="heartbeat"),
    path("logout/", views.logout_view, name="logout"),
    path("just-chill/", views.just_chill, name="just_chill"),
]
