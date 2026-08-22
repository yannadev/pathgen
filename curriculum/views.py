"""Student curriculum reading views."""

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from core.decorators import student_only
from curriculum.models import Lesson
from progress.services import (
    completed_pretest,
    has_active_enrollment,
    lesson_is_available,
    record_lesson_opened,
    student_progress,
)


@student_only
def lesson_page(request, slug):
    if not has_active_enrollment(request.user):
        return redirect("accounts:just_chill")
    if completed_pretest(request.user) is None:
        messages.info(request, "Complete the pretest before opening lessons.")
        return redirect("progress:student_dashboard")

    lesson = get_object_or_404(Lesson, slug=slug)
    progress = student_progress(request.user)
    if not lesson_is_available(request.user, lesson, progress):
        raise PermissionDenied("Complete the current lesson before opening this one.")

    record_lesson_opened(request.user, lesson)
    return render(request, "curriculum/lesson_page.html", {"lesson": lesson})
