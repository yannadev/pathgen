"""Authentication, account, class, and profile routes."""

from django.urls import path

from accounts import views


app_name = "accounts"

urlpatterns = [
    path("", views.login_view, name="login"),
    path("home/", views.home_redirect, name="home"),
    path("change-password/", views.change_password, name="change_password"),
    path("heartbeat/", views.heartbeat, name="heartbeat"),
    path("logout/", views.logout_view, name="logout"),
    path("just-chill/", views.just_chill, name="just_chill"),
]
