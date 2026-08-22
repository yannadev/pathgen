"""Short-exercise delivery, completion, and result views."""

from datetime import datetime

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from adaptive.orchestrator import (
    process_activity_completion,
    process_exercise_completion,
)
from core.decorators import student_only
from curriculum.models import Activity, Lesson
from practice.forms import ActivityAnswerForm, ExerciseAnswerForm
from practice.models import ActivitySession, ExerciseSession
from practice.session_state import (
    activity_questions_for_attempt,
    activity_study_time_seconds,
    exercise_questions_for_attempt,
    exercise_study_time_seconds,
    finish_activity_attempt,
    finish_exercise_attempt,
    get_activity_attempt,
    get_exercise_attempt,
    start_activity_attempt,
    start_exercise_attempt,
)
from progress.models import LessonProgress
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


def _activity_access_or_response(request, activity):
    if not has_active_enrollment(request.user):
        return redirect("accounts:just_chill")
    if completed_pretest(request.user) is None:
        messages.info(request, "Complete the pretest before starting an activity.")
        return redirect("progress:student_dashboard")
    progress = student_progress(request.user)
    if progress is None:
        raise PermissionDenied("Your learning path has not been initialized.")
    required_progress = {
        entry.lesson_id: entry.status
        for entry in LessonProgress.objects.filter(
            student=request.user,
            lesson__in=(activity.lesson_1, activity.lesson_2),
        )
    }
    if any(
        required_progress.get(lesson.id) != LessonProgress.Status.PASSED
        for lesson in (activity.lesson_1, activity.lesson_2)
    ):
        raise PermissionDenied("Complete both lessons before starting this activity.")
    if progress.current_lesson_id != activity.lesson_2_id:
        raise PermissionDenied("This activity is not your current learning checkpoint.")
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


def _activity_media(question):
    """Normalize optional seed/editor media metadata for the activity template."""
    media = question.media_jsonb
    if not isinstance(media, dict):
        return None
    media_type = media.get("type") or media.get("media_type")
    url = media.get("url") or media.get("src")
    if media_type == "image" or media.get("image_url"):
        return {
            "type": "image",
            "url": media.get("image_url") or url,
            "alt": media.get("alt") or "Question illustration",
        }
    if media_type == "video" or media.get("video_url"):
        try:
            checkpoint_seconds = float(media.get("checkpoint_seconds", 0))
        except (TypeError, ValueError):
            checkpoint_seconds = 0
        return {
            "type": "video",
            "url": media.get("video_url") or url,
            "checkpoint_seconds": checkpoint_seconds,
            "caption": media.get("caption") or "Watch the video before answering.",
        }
    return None


def _activity_question_items(questions, form):
    return [
        {
            "number": number,
            "question": question,
            "field": form[form.field_name(question.id)],
            "media": _activity_media(question),
            "checkpoint_field_name": form.checkpoint_field_name(question.id),
        }
        for number, question in enumerate(questions, start=1)
    ]


def _activity_checkpoint_question_ids(question_items):
    return {
        item["question"].id
        for item in question_items
        if item["media"]
        and item["media"]["type"] == "video"
        and item["media"]["checkpoint_seconds"] > 0
    }


def _render_activity(request, activity, questions, form, attempt, *, status=200):
    question_items = _activity_question_items(questions, form)
    return render(
        request,
        "practice/activity.html",
        {
            "activity": activity,
            "form": form,
            "question_items": question_items,
            "attempt_id": attempt["attempt_id"],
        },
        status=status,
    )


@require_POST
@student_only
def activity_start(request, activity_id):
    activity = get_object_or_404(
        Activity.objects.select_related("lesson_1", "lesson_2"),
        pk=activity_id,
    )
    blocked_response = _activity_access_or_response(request, activity)
    if blocked_response is not None:
        return blocked_response
    try:
        start_activity_attempt(request, activity)
    except ValueError as error:
        messages.error(request, str(error))
        return redirect("progress:lesson_path")
    return redirect("practice:activity", activity_id=activity.id)


@require_GET
@student_only
def activity(request, activity_id):
    activity_object = get_object_or_404(
        Activity.objects.select_related("lesson_1", "lesson_2"),
        pk=activity_id,
    )
    blocked_response = _activity_access_or_response(request, activity_object)
    if blocked_response is not None:
        return blocked_response
    attempt = get_activity_attempt(request, activity_object)
    if attempt is None:
        messages.info(request, "Start the activity from your learning path first.")
        return redirect("progress:lesson_path")
    try:
        questions = activity_questions_for_attempt(activity_object, attempt)
    except ValueError as error:
        messages.error(request, str(error))
        return redirect("progress:lesson_path")
    return _render_activity(
        request,
        activity_object,
        questions,
        ActivityAnswerForm(questions),
        attempt,
    )


@require_POST
@student_only
def activity_submit(request, activity_id):
    activity_object = get_object_or_404(
        Activity.objects.select_related("lesson_1", "lesson_2"),
        pk=activity_id,
    )
    blocked_response = _activity_access_or_response(request, activity_object)
    if blocked_response is not None:
        return blocked_response
    attempt = get_activity_attempt(request, activity_object)
    if attempt is None:
        messages.info(request, "Start the activity from your learning path first.")
        return redirect("progress:lesson_path")
    try:
        questions = activity_questions_for_attempt(activity_object, attempt)
    except ValueError as error:
        messages.error(request, str(error))
        return redirect("progress:lesson_path")

    form = ActivityAnswerForm(questions, request.POST)
    question_items = _activity_question_items(questions, form)
    checkpoint_ids = _activity_checkpoint_question_ids(question_items)
    reached_checkpoint_ids = {
        question_id
        for question_id in checkpoint_ids
        if request.POST.get(form.checkpoint_field_name(question_id)) == "1"
    }
    if checkpoint_ids - reached_checkpoint_ids:
        form.add_error(None, "Reach each video checkpoint before submitting.")
    if not form.is_valid():
        return _render_activity(
            request,
            activity_object,
            questions,
            form,
            attempt,
            status=400,
        )

    result = process_activity_completion(
        student=request.user,
        activity=activity_object,
        questions=questions,
        answers=form.answers(),
        study_time_seconds=activity_study_time_seconds(request, activity_object),
        started_at=datetime.fromisoformat(attempt["started_at"]),
        video_checkpoint_question_ids=reached_checkpoint_ids,
    )
    finish_activity_attempt(
        request,
        activity_object,
        action=result.decision.action,
        wrong_question_ids=result.wrong_question_ids,
    )
    return redirect("practice:activity_result", session_id=result.session.id)


@require_GET
@student_only
def activity_result(request, session_id):
    if not has_active_enrollment(request.user):
        return redirect("accounts:just_chill")
    session = get_object_or_404(
        ActivitySession.objects.select_related(
            "activity",
            "activity__lesson_1",
            "activity__lesson_2",
            "q_decision",
        ),
        pk=session_id,
        student=request.user,
        q_decision__isnull=False,
    )
    progress = student_progress(request.user)
    return render(
        request,
        "practice/activity_result.html",
        {
            "activity_session": session,
            "decision": session.q_decision,
            "correct_count": session.responses.filter(is_correct=True).count(),
            "next_lesson": progress.current_lesson if progress else None,
        },
    )
