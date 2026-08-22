"""Short-exercise delivery, completion, and result views."""

from datetime import datetime

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from adaptive.orchestrator import process_exercise_completion
from core.decorators import student_only
from curriculum.models import Lesson
from practice.forms import ExerciseAnswerForm
from practice.models import ExerciseSession
from practice.session_state import (
    exercise_questions_for_attempt,
    exercise_study_time_seconds,
    finish_exercise_attempt,
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


def _exercise_question_items(questions, form, hint_question_ids):
    hint_ids = set(hint_question_ids)
    return [
        {
            "number": number,
            "question": question,
            "field": form[form.field_name(question.id)],
            "hint_enabled": str(question.id) in hint_ids,
            "hint_field_name": form.hint_field_name(question.id),
        }
        for number, question in enumerate(questions, start=1)
    ]


def _render_short_exercise(request, lesson, questions, form, attempt, *, status=200):
    return render(
        request,
        "practice/short_exercise.html",
        {
            "lesson": lesson,
            "question_items": _exercise_question_items(
                questions,
                form,
                attempt.get("hint_question_ids", []),
            ),
            "attempt_id": attempt["attempt_id"],
            "retake_mode": bool(attempt.get("hint_question_ids")),
        },
        status=status,
    )


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

    return _render_short_exercise(
        request,
        lesson,
        questions,
        ExerciseAnswerForm(questions),
        attempt,
    )


@require_POST
@student_only
def exercise_submit(request, lesson_slug):
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

    form = ExerciseAnswerForm(questions, request.POST)
    if not form.is_valid():
        return _render_short_exercise(
            request,
            lesson,
            questions,
            form,
            attempt,
            status=400,
        )

    enabled_hint_ids = {
        question.id
        for question in questions
        if str(question.id) in attempt.get("hint_question_ids", [])
    }
    used_hint_ids = {
        question_id
        for question_id in enabled_hint_ids
        if request.POST.get(form.hint_field_name(question_id)) == "1"
    }
    result = process_exercise_completion(
        student=request.user,
        lesson=lesson,
        questions=questions,
        answers=form.answers(),
        study_time_seconds=exercise_study_time_seconds(request, lesson),
        started_at=datetime.fromisoformat(attempt["started_at"]),
        hint_used_question_ids=used_hint_ids,
    )
    finish_exercise_attempt(
        request,
        lesson,
        action=result.decision.action,
        wrong_question_ids=result.wrong_question_ids,
    )
    return redirect("practice:exercise_result", session_id=result.session.id)


@require_GET
@student_only
def exercise_result(request, session_id):
    if not has_active_enrollment(request.user):
        return redirect("accounts:just_chill")
    session = get_object_or_404(
        ExerciseSession.objects.select_related("lesson", "q_decision"),
        pk=session_id,
        student=request.user,
        q_decision__isnull=False,
    )
    progress = student_progress(request.user)
    return render(
        request,
        "practice/short_exercise_result.html",
        {
            "exercise_session": session,
            "decision": session.q_decision,
            "correct_count": session.responses.filter(is_correct=True).count(),
            "next_lesson": progress.current_lesson if progress else None,
        },
    )
