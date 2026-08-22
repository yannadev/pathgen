"""Short-exercise delivery views.

Completion is deliberately added by Phase 8, where the orchestrator can write
responses, mastery, Q decisions, and feedback in one transaction.
"""

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from core.decorators import student_only
from curriculum.models import Lesson
from practice.forms import ExerciseAnswerForm
from practice.session_state import (
    exercise_questions_for_attempt,
    get_exercise_attempt,
    start_exercise_attempt,
)
from progress.services import (
    completed_pretest,
    has_active_enrollment,
    lesson_is_available,
    record_lesson_opened,
    student_progress,
)


def _lesson_access_or_response(request, lesson):
    if not has_active_enrollment(request.user):
        return redirect("accounts:just_chill")
    if completed_pretest(request.user) is None:
        messages.info(request, "Complete the pretest before starting an exercise.")
        return redirect("progress:student_dashboard")
    progress = student_progress(request.user)
    if not lesson_is_available(request.user, lesson, progress):
        raise PermissionDenied("This lesson is not available yet.")
    if progress.current_lesson_id != lesson.id:
        raise PermissionDenied("Exercises are available only for your current lesson.")
    return None


@require_POST
@student_only
def exercise_start(request, lesson_slug):
    lesson = get_object_or_404(Lesson, slug=lesson_slug)
    blocked_response = _lesson_access_or_response(request, lesson)
    if blocked_response is not None:
        return blocked_response

    try:
        start_exercise_attempt(request, lesson)
    except ValueError as error:
        messages.error(request, str(error))
        return redirect("curriculum:lesson_page", slug=lesson.slug)

    record_lesson_opened(request.user, lesson)
    return redirect("practice:short_exercise", lesson_slug=lesson.slug)


@require_GET
@student_only
def short_exercise(request, lesson_slug):
    lesson = get_object_or_404(Lesson, slug=lesson_slug)
    blocked_response = _lesson_access_or_response(request, lesson)
    if blocked_response is not None:
        return blocked_response

    attempt = get_exercise_attempt(request, lesson)
    if attempt is None:
        messages.info(request, "Start the exercise from the lesson page first.")
        return redirect("curriculum:lesson_page", slug=lesson.slug)
    try:
        questions = exercise_questions_for_attempt(lesson, attempt)
    except ValueError as error:
        messages.error(request, str(error))
        return redirect("curriculum:lesson_page", slug=lesson.slug)

    form = ExerciseAnswerForm(questions)
    question_items = [
        {
            "number": number,
            "question": question,
            "field": form[form.field_name(question.id)],
        }
        for number, question in enumerate(questions, start=1)
    ]
    return render(
        request,
        "practice/short_exercise.html",
        {
            "lesson": lesson,
            "question_items": question_items,
            "attempt_id": attempt["attempt_id"],
        },
    )
