"""Session heartbeat and forced-password middleware."""

from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse

from core.session_tracking import touch_tracked_session


class UserSessionHeartbeatMiddleware:
    """Create and periodically update a tracked session for signed-in users."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and not request.path_info.startswith(
            settings.STATIC_URL
        ):
            touch_tracked_session(request)
        return self.get_response(request)


class ForcePasswordChangeMiddleware:
    """Keep flagged users inside the password-change flow until completion."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and request.user.password_must_change:
            allowed_paths = {
                reverse("accounts:change_password"),
                reverse("accounts:logout"),
                reverse("accounts:heartbeat"),
            }
            if request.path_info not in allowed_paths:
                return redirect("accounts:change_password")
        return self.get_response(request)
