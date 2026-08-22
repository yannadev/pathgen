"""Student progress entry views."""

from django.shortcuts import redirect, render

from accounts.models import ClassStudent
from assessment.models import AssessmentSession, AssessmentType
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
    pretest_sessions = AssessmentSession.objects.filter(
        student=request.user,
        type=AssessmentType.PRETEST,
    )
    completed_pretest = pretest_sessions.filter(
        completed_at__isnull=False
    ).order_by("-completed_at").first()
    active_pretest = pretest_sessions.filter(completed_at__isnull=True).first()
    return render(
        request,
        "progress/student_dashboard.html",
        {
            "classroom": enrollment.classroom,
            "completed_pretest": completed_pretest,
            "active_pretest": active_pretest,
        },
    )
