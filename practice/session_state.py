"""Server-side state for an in-progress short exercise.

ExerciseSession is intentionally created only by the Phase 8 completion
orchestrator, because it must be committed atomically with its responses,
mastery update, and Q-learning decision.
"""

import uuid
from datetime import datetime

from django.utils import timezone

from accounts.models import UserSession
from core.session_tracking import (
    SESSION_RECORD_KEY,
    touch_tracked_session,
)
from curriculum.models import ExerciseQuestion


EXERCISE_ATTEMPT_SESSION_KEY = "_pathgen_exercise_attempt"
EXERCISE_QUESTION_COUNT = 15


def _serialize_attempt(lesson, questions, tracked_session):
    return {
        "attempt_id": str(uuid.uuid4()),
        "lesson_id": str(lesson.id),
        "question_ids": [str(question.id) for question in questions],
        "started_at": timezone.now().isoformat(),
        "tracked_session_id": tracked_session.session_id,
        "starting_active_duration_seconds": tracked_session.active_duration_seconds,
    }


def _tracked_session_for_request(request):
    touch_tracked_session(request, force=True)
    tracked_session_id = request.session.get(SESSION_RECORD_KEY)
    return UserSession.objects.get(
        pk=tracked_session_id,
        user=request.user,
        logout_at__isnull=True,
    )


def start_exercise_attempt(request, lesson):
    """Create a resumable, server-side attempt with randomly selected items."""
    existing = get_exercise_attempt(request, lesson)
    if existing is not None:
        return existing

    questions = list(
        ExerciseQuestion.objects.filter(lesson=lesson).order_by("?")[
            :EXERCISE_QUESTION_COUNT
        ]
    )
    if len(questions) != EXERCISE_QUESTION_COUNT:
        raise ValueError(
            f"Lesson {lesson.order_index} needs {EXERCISE_QUESTION_COUNT} exercise questions."
        )

    tracked_session = _tracked_session_for_request(request)
    state = _serialize_attempt(lesson, questions, tracked_session)
    request.session[EXERCISE_ATTEMPT_SESSION_KEY] = state
    request.session.modified = True
    return state


def get_exercise_attempt(request, lesson):
    """Return valid attempt state for the requested lesson, if any."""
    state = request.session.get(EXERCISE_ATTEMPT_SESSION_KEY)
    if not isinstance(state, dict) or state.get("lesson_id") != str(lesson.id):
        return None
    question_ids = state.get("question_ids")
    if not isinstance(question_ids, list) or len(question_ids) != EXERCISE_QUESTION_COUNT:
        return None
    if not isinstance(state.get("tracked_session_id"), int):
        return None
    if not isinstance(state.get("starting_active_duration_seconds"), int):
        return None
    try:
        datetime.fromisoformat(state["started_at"])
        [uuid.UUID(question_id) for question_id in question_ids]
    except (KeyError, TypeError, ValueError):
        return None
    return state


def exercise_questions_for_attempt(lesson, attempt):
    """Return the selected questions in their stored random order."""
    question_ids = [uuid.UUID(question_id) for question_id in attempt["question_ids"]]
    by_id = {
        question.id: question
        for question in ExerciseQuestion.objects.filter(lesson=lesson, id__in=question_ids)
    }
    try:
        questions = [by_id[question_id] for question_id in question_ids]
    except KeyError as error:
        raise ValueError("An exercise question is no longer available.") from error
    if len(questions) != EXERCISE_QUESTION_COUNT:
        raise ValueError("The exercise question set is incomplete.")
    return questions


def exercise_study_time_seconds(request, lesson):
    """Return heartbeat-tracked active seconds since this exercise began.

    Phase 8 uses this value when it creates ExerciseSession atomically.
    """
    attempt = get_exercise_attempt(request, lesson)
    if attempt is None:
        return 0
    touch_tracked_session(request, force=True)
    tracked_session = UserSession.objects.filter(
        pk=attempt["tracked_session_id"],
        user=request.user,
    ).first()
    if tracked_session is None:
        return 0
    return max(
        0,
        tracked_session.active_duration_seconds
        - attempt["starting_active_duration_seconds"],
    )
