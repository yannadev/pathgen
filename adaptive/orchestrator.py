"""Transactional coordination for adaptive session completion."""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
import logging

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from accounts.models import User
from adaptive.bkt import update_mastery
from adaptive.models import (
    ActivityQDecision,
    BKTMastery,
    BKTModelParameters,
    ExerciseQDecision,
    QAction,
)
from adaptive.qlearning import (
    get_action,
    get_state,
    load_q_table,
    rule_based_action,
)
from curriculum.models import Activity
from practice.models import (
    ActivityResponse,
    ActivitySession,
    ExerciseResponse,
    ExerciseSession,
)
from progress.models import LessonProgress, StudentProgress


logger = logging.getLogger(__name__)
SCORE_QUANTUM = Decimal("0.01")
MASTERY_QUANTUM = Decimal("0.0001")


@dataclass(frozen=True)
class ExerciseCompletionResult:
    session: ExerciseSession
    decision: ExerciseQDecision
    correct_count: int
    wrong_question_ids: tuple
    completed_now: bool


@dataclass(frozen=True)
class ActivityCompletionResult:
    """Committed outcome for one mixed-lesson activity attempt."""

    session: ActivitySession
    decision: ActivityQDecision
    correct_count: int
    wrong_question_ids: tuple
    completed_now: bool


def _validate_exercise_submission(
    student,
    lesson,
    questions,
    answers,
    study_time_seconds,
    started_at,
    hint_used_question_ids,
):
    questions = list(questions)
    if not questions:
        raise ValueError("An exercise needs at least one question.")

    question_ids = [question.id for question in questions]
    if len(question_ids) != len(set(question_ids)):
        raise ValueError("Exercise questions must be unique.")
    if any(question.lesson_id != lesson.id for question in questions):
        raise ValueError("Every exercise question must belong to the lesson.")
    if set(answers) != set(question_ids):
        raise ValueError("Every delivered exercise question must be answered.")
    if any(
        isinstance(answer, bool) or not isinstance(answer, int) or answer not in range(4)
        for answer in answers.values()
    ):
        raise ValueError("Selected answer indexes must be integers from 0 to 3.")
    if (
        isinstance(study_time_seconds, bool)
        or not isinstance(study_time_seconds, int)
        or study_time_seconds < 0
    ):
        raise ValueError("Study time must be a non-negative integer.")
    if started_at is None or timezone.is_naive(started_at):
        raise ValueError("Exercise start time must be timezone-aware.")

    hint_ids = set(hint_used_question_ids)
    if not hint_ids.issubset(question_ids):
        raise ValueError("Hint usage contains a question outside the exercise.")
    return questions, hint_ids


def _validate_activity_submission(
    student,
    activity,
    questions,
    answers,
    study_time_seconds,
    started_at,
    video_checkpoint_question_ids,
):
    """Validate an activity's exact delivered question set before writing."""
    questions = list(questions)
    if not questions:
        raise ValueError("An activity needs at least one question.")

    question_ids = [question.id for question in questions]
    if len(question_ids) != len(set(question_ids)):
        raise ValueError("Activity questions must be unique.")
    if any(question.activity_id != activity.id for question in questions):
        raise ValueError("Every activity question must belong to the activity.")
    if set(answers) != set(question_ids):
        raise ValueError("Every delivered activity question must be answered.")
    if any(
        isinstance(answer, bool) or not isinstance(answer, int) or answer not in range(4)
        for answer in answers.values()
    ):
        raise ValueError("Selected answer indexes must be integers from 0 to 3.")
    if (
        isinstance(study_time_seconds, bool)
        or not isinstance(study_time_seconds, int)
        or study_time_seconds < 0
    ):
        raise ValueError("Study time must be a non-negative integer.")
    if started_at is None or timezone.is_naive(started_at):
        raise ValueError("Activity start time must be timezone-aware.")

    checkpoint_ids = set(video_checkpoint_question_ids)
    if not checkpoint_ids.issubset(question_ids):
        raise ValueError("Video checkpoint data contains a question outside the activity.")
    video_question_ids = {
        question.id for question in questions if _question_has_video(question)
    }
    if not checkpoint_ids.issubset(video_question_ids):
        raise ValueError("Video checkpoint data contains a non-video question.")
    return questions, checkpoint_ids


def _score(correct_count, total_questions):
    return (Decimal(correct_count * 100) / Decimal(total_questions)).quantize(
        SCORE_QUANTUM,
        rounding=ROUND_HALF_UP,
    )


def _question_has_video(question):
    media = question.media_jsonb
    return isinstance(media, dict) and (
        media.get("type") == "video"
        or media.get("media_type") == "video"
        or bool(media.get("video_url"))
    )


def _updated_mastery(student, lesson, correct_count, wrong_count):
    mastery_row = (
        BKTMastery.objects.select_for_update()
        .filter(student=student, lesson=lesson)
        .first()
    )
    prior = mastery_row.p_known if mastery_row else Decimal("0.5000")

    try:
        parameters = BKTModelParameters.objects.get()
        updated = update_mastery(
            p_known=float(prior),
            n_correct=correct_count,
            n_wrong=wrong_count,
            p_learn=float(parameters.p_learn),
            p_slip=float(parameters.p_slip),
            p_guess=float(parameters.p_guess),
        )
    except (
        BKTModelParameters.DoesNotExist,
        BKTModelParameters.MultipleObjectsReturned,
        ArithmeticError,
        TypeError,
        ValueError,
    ) as error:
        logger.warning("BKT update failed; using prior mastery: %s", error)
        return prior

    mastery = Decimal(str(updated)).quantize(MASTERY_QUANTUM)
    if mastery_row is None:
        BKTMastery.objects.create(
            student=student,
            lesson=lesson,
            p_known=mastery,
        )
    else:
        mastery_row.p_known = mastery
        mastery_row.save(update_fields=["p_known", "updated_at"])
    return mastery


def _choose_action(mastery, attempt_count, session_score):
    mastery_value = float(mastery)
    score_value = float(session_score)
    try:
        state = get_state(mastery_value, attempt_count)
        return get_action(
            state,
            load_q_table(),
            mastery=mastery_value,
            attempt_count=attempt_count,
            session_score=score_value,
        )
    except (OSError, TypeError, ValueError) as error:
        logger.warning("Q-learning failed; using rule fallback: %s", error)
        return rule_based_action(mastery_value, attempt_count, score_value)


def _apply_exercise_action(student, lesson, action, completed_at):
    progress = StudentProgress.objects.select_for_update().get(student=student)
    lesson_progress, _ = LessonProgress.objects.select_for_update().get_or_create(
        student=student,
        lesson=lesson,
        defaults={
            "status": LessonProgress.Status.IN_PROGRESS,
            "first_started_at": completed_at,
            "last_activity_at": completed_at,
        },
    )
    if lesson_progress.first_started_at is None:
        lesson_progress.first_started_at = completed_at
    lesson_progress.last_activity_at = completed_at

    if action == QAction.ADVANCE:
        lesson_progress.status = LessonProgress.Status.PASSED
        # An activity is a mandatory checkpoint after its second lesson.  Keep
        # the student anchored on that lesson until the paired activity decides
        # whether to advance, review, or retake.
        if Activity.objects.filter(lesson_2=lesson).exists():
            progress.current_lesson = lesson
            progress.status = StudentProgress.Status.IN_PROGRESS
        else:
            next_lesson = lesson.__class__.objects.filter(
                order_index__gt=lesson.order_index
            ).order_by("order_index").first()
            progress.current_lesson = next_lesson
            progress.status = (
                StudentProgress.Status.IN_PROGRESS
                if next_lesson is not None
                else StudentProgress.Status.COMPLETED
            )
    elif action == QAction.REVIEW:
        lesson_progress.status = LessonProgress.Status.NEEDS_REVIEW
        progress.current_lesson = lesson
        progress.status = StudentProgress.Status.IN_PROGRESS
    elif action == QAction.RETAKE:
        lesson_progress.status = LessonProgress.Status.IN_PROGRESS
        progress.current_lesson = lesson
        progress.status = StudentProgress.Status.IN_PROGRESS
    else:
        raise ValueError(f"Unsupported Q-learning action: {action}")

    lesson_progress.save(
        update_fields=["status", "first_started_at", "last_activity_at"]
    )
    progress.last_activity_at = completed_at
    progress.save(
        update_fields=["current_lesson", "status", "last_activity_at"]
    )


def _apply_activity_action(student, activity, action, completed_at):
    """Apply a single Q-learning action to the two lessons an activity covers."""
    progress = StudentProgress.objects.select_for_update().get(student=student)
    lessons = (activity.lesson_1, activity.lesson_2)
    lesson_progresses = []
    for lesson in lessons:
        lesson_progress, _ = LessonProgress.objects.select_for_update().get_or_create(
            student=student,
            lesson=lesson,
            defaults={
                "status": LessonProgress.Status.IN_PROGRESS,
                "first_started_at": completed_at,
                "last_activity_at": completed_at,
            },
        )
        if lesson_progress.first_started_at is None:
            lesson_progress.first_started_at = completed_at
        lesson_progress.last_activity_at = completed_at
        lesson_progresses.append(lesson_progress)

    if action == QAction.ADVANCE:
        for lesson_progress in lesson_progresses:
            lesson_progress.status = LessonProgress.Status.PASSED
        next_lesson = activity.lesson_2.__class__.objects.filter(
            order_index__gt=activity.lesson_2.order_index
        ).order_by("order_index").first()
        progress.current_lesson = next_lesson
        progress.status = (
            StudentProgress.Status.IN_PROGRESS
            if next_lesson is not None
            else StudentProgress.Status.COMPLETED
        )
    elif action == QAction.REVIEW:
        for lesson_progress in lesson_progresses:
            lesson_progress.status = LessonProgress.Status.NEEDS_REVIEW
        progress.current_lesson = activity.lesson_1
        progress.status = StudentProgress.Status.IN_PROGRESS
    elif action == QAction.RETAKE:
        # The activity is retried as the same 30-question set.  Both lessons
        # remain passed so its start gate stays available.
        for lesson_progress in lesson_progresses:
            lesson_progress.status = LessonProgress.Status.PASSED
        progress.current_lesson = activity.lesson_2
        progress.status = StudentProgress.Status.IN_PROGRESS
    else:
        raise ValueError(f"Unsupported Q-learning action: {action}")

    for lesson_progress in lesson_progresses:
        lesson_progress.save(
            update_fields=["status", "first_started_at", "last_activity_at"]
        )
    progress.last_activity_at = completed_at
    progress.save(update_fields=["current_lesson", "status", "last_activity_at"])


@transaction.atomic
def process_exercise_completion(
    *,
    student,
    lesson,
    questions,
    answers,
    study_time_seconds,
    started_at,
    hint_used_question_ids=(),
):
    """Grade and commit one exercise through BKT, Q-learning, and action apply."""
    questions, hint_ids = _validate_exercise_submission(
        student,
        lesson,
        questions,
        answers,
        study_time_seconds,
        started_at,
        hint_used_question_ids,
    )

    # Serialize completion per student and make retries with the same start
    # timestamp idempotent.
    User.objects.select_for_update().get(pk=student.pk)
    existing = (
        ExerciseSession.objects.select_related("q_decision")
        .prefetch_related("responses")
        .filter(student=student, lesson=lesson, started_at=started_at)
        .first()
    )
    if existing is not None:
        responses = list(existing.responses.all())
        return ExerciseCompletionResult(
            session=existing,
            decision=existing.q_decision,
            correct_count=sum(response.is_correct for response in responses),
            wrong_question_ids=tuple(
                response.exercise_question_id
                for response in responses
                if not response.is_correct
            ),
            completed_now=False,
        )

    completed_at = max(timezone.now(), started_at)
    response_rows = []
    wrong_question_ids = []
    correct_count = 0
    for question in questions:
        is_correct = answers[question.id] == question.correct_answer_index
        correct_count += int(is_correct)
        if not is_correct:
            wrong_question_ids.append(question.id)
        response_rows.append(
            ExerciseResponse(
                exercise_question=question,
                selected_answer_index=answers[question.id],
                is_correct=is_correct,
                hint_used=question.id in hint_ids,
            )
        )

    session_score = _score(correct_count, len(questions))
    session = ExerciseSession.objects.create(
        student=student,
        lesson=lesson,
        score=session_score,
        total_questions=len(questions),
        study_time_seconds=study_time_seconds,
        started_at=started_at,
        completed_at=completed_at,
    )
    for response in response_rows:
        response.exercise_session = session
    ExerciseResponse.objects.bulk_create(response_rows)

    mastery = _updated_mastery(
        student,
        lesson,
        correct_count,
        len(questions) - correct_count,
    )
    lesson_sessions = ExerciseSession.objects.filter(student=student, lesson=lesson)
    attempt_count = lesson_sessions.count()
    cumulative_study_time = (
        lesson_sessions.aggregate(total=Sum("study_time_seconds"))["total"] or 0
    )
    cumulative_hint_count = ExerciseResponse.objects.filter(
        exercise_session__student=student,
        exercise_session__lesson=lesson,
        hint_used=True,
    ).count()
    action = _choose_action(mastery, attempt_count, session_score)
    decision = ExerciseQDecision.objects.create(
        student=student,
        lesson=lesson,
        exercise_session=session,
        action=action,
        mastery_at_decision=mastery,
        study_time_seconds=cumulative_study_time,
        attempt_count=attempt_count,
        session_score=session_score,
        hint_count=cumulative_hint_count,
    )
    _apply_exercise_action(student, lesson, action, completed_at)

    return ExerciseCompletionResult(
        session=session,
        decision=decision,
        correct_count=correct_count,
        wrong_question_ids=tuple(wrong_question_ids),
        completed_now=True,
    )


@transaction.atomic
def process_activity_completion(
    *,
    student,
    activity,
    questions,
    answers,
    study_time_seconds,
    started_at,
    video_checkpoint_question_ids=(),
):
    """Grade an activity, update both covered lessons, and freeze its decision.

    Activity questions are not tagged to an individual lesson in the schema, so
    the aggregate activity performance is intentionally applied to each of the
    activity's two adjacent lessons.
    """
    questions, checkpoint_ids = _validate_activity_submission(
        student,
        activity,
        questions,
        answers,
        study_time_seconds,
        started_at,
        video_checkpoint_question_ids,
    )

    User.objects.select_for_update().get(pk=student.pk)
    existing = (
        ActivitySession.objects.select_related("q_decision")
        .prefetch_related("responses")
        .filter(student=student, activity=activity, started_at=started_at)
        .first()
    )
    if existing is not None:
        responses = list(existing.responses.all())
        return ActivityCompletionResult(
            session=existing,
            decision=existing.q_decision,
            correct_count=sum(response.is_correct for response in responses),
            wrong_question_ids=tuple(
                response.activity_question_id
                for response in responses
                if not response.is_correct
            ),
            completed_now=False,
        )

    completed_at = max(timezone.now(), started_at)
    response_rows = []
    wrong_question_ids = []
    correct_count = 0
    for question in questions:
        is_correct = answers[question.id] == question.correct_answer_index
        correct_count += int(is_correct)
        if not is_correct:
            wrong_question_ids.append(question.id)
        response_rows.append(
            ActivityResponse(
                activity_question=question,
                selected_answer_index=answers[question.id],
                is_correct=is_correct,
                video_checkpoint_reached=(
                    question.id in checkpoint_ids if _question_has_video(question) else None
                ),
            )
        )

    session_score = _score(correct_count, len(questions))
    session = ActivitySession.objects.create(
        student=student,
        activity=activity,
        score=session_score,
        total_questions=len(questions),
        study_time_seconds=study_time_seconds,
        started_at=started_at,
        completed_at=completed_at,
    )
    for response in response_rows:
        response.activity_session = session
    ActivityResponse.objects.bulk_create(response_rows)

    wrong_count = len(questions) - correct_count
    mastery_by_lesson_id = {
        lesson.id: _updated_mastery(student, lesson, correct_count, wrong_count)
        for lesson in (activity.lesson_1, activity.lesson_2)
    }
    activity_sessions = ActivitySession.objects.filter(student=student, activity=activity)
    attempt_count = activity_sessions.count()
    cumulative_study_time = (
        activity_sessions.aggregate(total=Sum("study_time_seconds"))["total"] or 0
    )
    action_lesson = activity.lesson_2
    action = _choose_action(
        mastery_by_lesson_id[action_lesson.id],
        attempt_count,
        session_score,
    )
    decision = ActivityQDecision.objects.create(
        student=student,
        # The terminal lesson is the paired activity's learning-path anchor.
        lesson=action_lesson,
        activity_session=session,
        action=action,
        mastery_at_decision=mastery_by_lesson_id[action_lesson.id],
        study_time_seconds=cumulative_study_time,
        attempt_count=attempt_count,
        session_score=session_score,
        hint_count=0,
    )
    _apply_activity_action(student, activity, action, completed_at)

    return ActivityCompletionResult(
        session=session,
        decision=decision,
        correct_count=correct_count,
        wrong_question_ids=tuple(wrong_question_ids),
        completed_now=True,
    )
