"""Reusable role and classroom authorization guards."""

from functools import wraps

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import (
    ImproperlyConfigured,
    PermissionDenied,
    ValidationError,
)


def role_required(*allowed_roles):
    """Require authentication and membership in one of ``allowed_roles``."""

    allowed = {str(role) for role in allowed_roles}
    if not allowed:
        raise ValueError("role_required needs at least one allowed role.")

    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path(), settings.LOGIN_URL)
            if request.user.role not in allowed:
                raise PermissionDenied("You do not have permission to view this page.")
            return view_func(request, *args, **kwargs)

        return wrapped

    return decorator


def admin_only(view_func):
    """Allow admin users only."""

    return role_required("admin")(view_func)


def teacher_only(view_func):
    """Allow teacher users only."""

    return role_required("teacher")(view_func)


def student_only(view_func):
    """Allow student users only."""

    return role_required("student")(view_func)


def teacher_own_class(view_func):
    """Allow a teacher to access only an active class assigned to them.

    The decorated route must expose ``class_id``, ``classroom_id``, or ``pk``.
    """

    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path(), settings.LOGIN_URL)
        if request.user.role != "teacher":
            raise PermissionDenied("Teacher access is required.")

        lookup_value = next(
            (
                kwargs[name]
                for name in ("class_id", "classroom_id", "pk")
                if name in kwargs
            ),
            None,
        )
        if lookup_value is None:
            raise ImproperlyConfigured(
                "teacher_own_class requires class_id, classroom_id, or pk."
            )

        from accounts.models import Classroom

        try:
            owns_class = Classroom.objects.filter(
                pk=lookup_value,
                teacher=request.user,
                is_active=True,
            ).exists()
        except (TypeError, ValueError, ValidationError):
            owns_class = False

        if not owns_class:
            raise PermissionDenied("You can only view your own active classes.")
        return view_func(request, *args, **kwargs)

    return wrapped
