"""Student progress entry views."""

from django.shortcuts import redirect, render

from accounts.models import ClassStudent
from core.decorators import student_only


@student_only
def student_dashboard(request):
    enrollment = (
        ClassStudent.objects.select_related("classroom", "classroom__teacher")
        .filter(student=request.user, classroom__is_active=True)
        .first()
    )
    if enrollment is None:
        return redirect("accounts:just_chill")
    return render(
        request,
        "progress/student_dashboard.html",
        {"classroom": enrollment.classroom},
    )
