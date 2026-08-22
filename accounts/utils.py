"""Role-aware routing helpers."""

from django.core.exceptions import PermissionDenied
from django.urls import reverse

from accounts.models import ClassStudent, User


def student_has_active_class(user):
    return ClassStudent.objects.filter(
        student=user,
        classroom__is_active=True,
    ).exists()


def role_home_url(user):
    if user.role == User.Role.ADMIN:
        return reverse("monitoring:admin_dashboard")
    if user.role == User.Role.TEACHER:
        return reverse("monitoring:teacher_dashboard")
    if user.role == User.Role.STUDENT:
        if student_has_active_class(user):
            return reverse("progress:student_dashboard")
        return reverse("accounts:just_chill")
    raise PermissionDenied("This account does not have a supported role.")
