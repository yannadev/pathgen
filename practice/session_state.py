"""Server-side state for an in-progress short exercise.

ExerciseSession is created only by the completion orchestrator so it commits
atomically with responses, mastery, and the Q-learning decision.
"""

import uuid
from datetime import datetime

from django.utils import timezone

from accounts.models import UserSession
from core.session_tracking import (
    SESSION_RECORD_KEY,
    touch_tracked_session,
)
from curriculum.models import ActivityQuestion, ExerciseQuestion


EXERCISE_ATTEMPT_SESSION_KEY = "_pathgen_exercise_attempt"
EXERCISE_RETAKE_SESSION_KEY = "_pathgen_exercise_retake"
EXERCISE_QUESTION_COUNT = 15
ACTIVITY_ATTEMPT_SESSION_KEY = "_pathgen_activity_attempt"
ACTIVITY_RETAKE_SESSION_KEY = "_pathgen_activity_retake"
ACTIVITY_QUESTION_COUNT = 30


def _serialize_attempt(lesson, questions, tracked_session, *, hint_question_ids=()):
    return {
        "attempt_id": str(uuid.uuid4()),
        "lesson_id": str(lesson.id),
        "question_ids": [str(question.id) for question in questions],
        "started_at": timezone.now().isoformat(),
        "tracked_session_id": tracked_session.session_id,
        "starting_active_duration_seconds": tracked_session.active_duration_seconds,
        "hint_question_ids": [str(question_id) for question_id in hint_question_ids],
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

    retake = _get_retake_state(request, lesson)
    if retake is not None:
        questions = exercise_questions_for_attempt(lesson, retake)
        hint_question_ids = retake["hint_question_ids"]
        request.session.pop(EXERCISE_RETAKE_SESSION_KEY, None)
    else:
        questions = list(
            ExerciseQuestion.objects.filter(lesson=lesson).order_by("?")[
                :EXERCISE_QUESTION_COUNT
            ]
        )
        hint_question_ids = ()
    if len(questions) != EXERCISE_QUESTION_COUNT:
        raise ValueError(
            f"Lesson {lesson.order_index} needs {EXERCISE_QUESTION_COUNT} exercise questions."
        )

    tracked_session = _tracked_session_for_request(request)
    state = _serialize_attempt(
        lesson,
        questions,
        tracked_session,
        hint_question_ids=hint_question_ids,
    )
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
    hint_question_ids = state.get("hint_question_ids", [])
    if not isinstance(hint_question_ids, list):
        return None
    try:
        datetime.fromisoformat(state["started_at"])
        parsed_question_ids = {uuid.UUID(question_id) for question_id in question_ids}
        parsed_hint_ids = {uuid.UUID(question_id) for question_id in hint_question_ids}
    except (KeyError, TypeError, ValueError):
        return None
    if not parsed_hint_ids.issubset(parsed_question_ids):
        return None
    return state


def _get_retake_state(request, lesson):
    state = request.session.get(EXERCISE_RETAKE_SESSION_KEY)
    if not isinstance(state, dict) or state.get("lesson_id") != str(lesson.id):
        return None
    question_ids = state.get("question_ids")
    hint_question_ids = state.get("hint_question_ids")
    if not isinstance(question_ids, list) or len(question_ids) != EXERCISE_QUESTION_COUNT:
        return None
    if not isinstance(hint_question_ids, list):
        return None
    try:
        parsed_questions = {uuid.UUID(question_id) for question_id in question_ids}
        parsed_hints = {uuid.UUID(question_id) for question_id in hint_question_ids}
    except (TypeError, ValueError):
        return None
    if not parsed_hints.issubset(parsed_questions):
        return None
    return state


def finish_exercise_attempt(request, lesson, *, action, wrong_question_ids):
    """Clear the completed attempt and queue a same-question hinted retake."""
    attempt = get_exercise_attempt(request, lesson)
    request.session.pop(EXERCISE_ATTEMPT_SESSION_KEY, None)
    request.session.pop(EXERCISE_RETAKE_SESSION_KEY, None)
    if action == "retake" and attempt is not None:
        request.session[EXERCISE_RETAKE_SESSION_KEY] = {
            "lesson_id": str(lesson.id),
            "question_ids": attempt["question_ids"],
            "hint_question_ids": [str(question_id) for question_id in wrong_question_ids],
        }
    request.session.modified = True


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

    The completion orchestrator stores this value on ExerciseSession.
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


def _serialize_activity_attempt(activity, questions, tracked_session, *, hint_question_ids=()):
    return {
        "attempt_id": str(uuid.uuid4()),
        "activity_id": str(activity.id),
        "question_ids": [str(question.id) for question in questions],
        "started_at": timezone.now().isoformat(),
        "tracked_session_id": tracked_session.session_id,
        "starting_active_duration_seconds": tracked_session.active_duration_seconds,
        "hint_question_ids": [str(question_id) for question_id in hint_question_ids],
    }


def _valid_activity_state(state, activity, *, require_tracking):
    if not isinstance(state, dict) or state.get("activity_id") != str(activity.id):
        return None
    question_ids = state.get("question_ids")
    if not isinstance(question_ids, list) or len(question_ids) != ACTIVITY_QUESTION_COUNT:
        return None
    hint_question_ids = state.get("hint_question_ids", [])
    if not isinstance(hint_question_ids, list):
        return None
    if require_tracking and (
        not isinstance(state.get("tracked_session_id"), int)
        or not isinstance(state.get("starting_active_duration_seconds"), int)
    ):
        return None
    try:
        if require_tracking:
            datetime.fromisoformat(state["started_at"])
        parsed_question_ids = {uuid.UUID(question_id) for question_id in question_ids}
        parsed_hint_ids = {uuid.UUID(question_id) for question_id in hint_question_ids}
    except (KeyError, TypeError, ValueError):
        return None
    if not parsed_hint_ids.issubset(parsed_question_ids):
        return None
    return state


def get_activity_attempt(request, activity):
    """Return valid activity attempt state for the requested activity, if any."""
    return _valid_activity_state(
        request.session.get(ACTIVITY_ATTEMPT_SESSION_KEY),
        activity,
        require_tracking=True,
    )


def _get_activity_retake_state(request, activity):
    return _valid_activity_state(
        request.session.get(ACTIVITY_RETAKE_SESSION_KEY),
        activity,
        require_tracking=False,
    )


def activity_questions_for_attempt(activity, attempt):
    """Return all activity questions in the stored delivery order."""
    question_ids = [uuid.UUID(question_id) for question_id in attempt["question_ids"]]
    by_id = {
        question.id: question
        for question in ActivityQuestion.objects.filter(
            activity=activity,
            id__in=question_ids,
        )
    }
    try:
        questions = [by_id[question_id] for question_id in question_ids]
    except KeyError as error:
        raise ValueError("An activity question is no longer available.") from error
    if len(questions) != ACTIVITY_QUESTION_COUNT:
        raise ValueError("The activity question set is incomplete.")
    return questions


def start_activity_attempt(request, activity):
    """Create a resumable, ordered 30-question mixed-media activity attempt."""
    existing = get_activity_attempt(request, activity)
    if existing is not None:
        return existing

    retake = _get_activity_retake_state(request, activity)
    if retake is not None:
        questions = activity_questions_for_attempt(activity, retake)
        hint_question_ids = retake["hint_question_ids"]
        request.session.pop(ACTIVITY_RETAKE_SESSION_KEY, None)
    else:
        questions = list(
            ActivityQuestion.objects.filter(activity=activity).order_by("order_index")
        )
        hint_question_ids = ()
    if len(questions) != ACTIVITY_QUESTION_COUNT:
        raise ValueError(
            f"Activity {activity.order_index} needs {ACTIVITY_QUESTION_COUNT} questions."
        )

    tracked_session = _tracked_session_for_request(request)
    state = _serialize_activity_attempt(
        activity,
        questions,
        tracked_session,
        hint_question_ids=hint_question_ids,
    )
    request.session[ACTIVITY_ATTEMPT_SESSION_KEY] = state
    request.session.modified = True
    return state


def finish_activity_attempt(request, activity, *, action, wrong_question_ids):
    """Clear the completed activity and queue a hinted same-question retake."""
    attempt = get_activity_attempt(request, activity)
    request.session.pop(ACTIVITY_ATTEMPT_SESSION_KEY, None)
    request.session.pop(ACTIVITY_RETAKE_SESSION_KEY, None)
    if action == "retake" and attempt is not None:
        request.session[ACTIVITY_RETAKE_SESSION_KEY] = {
            "activity_id": str(activity.id),
            "question_ids": attempt["question_ids"],
            "hint_question_ids": [str(question_id) for question_id in wrong_question_ids],
        }
    request.session.modified = True


def activity_study_time_seconds(request, activity):
    """Return heartbeat-tracked active seconds since this activity began."""
    attempt = get_activity_attempt(request, activity)
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
