"""Transactional assessment completion services."""

from collections import Counter
from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ImproperlyConfigured
from django.db import transaction
from django.utils import timezone

from adaptive.bkt import init_mastery
from adaptive.models import BKTMastery, BKTModelParameters
from assessment.models import AssessmentResponse, AssessmentSession, AssessmentType
from curriculum.models import AssessmentQuestion, Lesson
from progress.models import StudentProgress


PRETEST_QUESTION_COUNT = 40


class AssessmentConfigurationError(ImproperlyConfigured):
    """Raised when required assessment or adaptive configuration is invalid."""


def pretest_questions():
    return AssessmentQuestion.objects.select_related("lesson").order_by(
        "lesson__order_index", "id"
    )


def validate_pretest_bank(questions):
    if len(questions) != PRETEST_QUESTION_COUNT:
        raise AssessmentConfigurationError(
            f"The pretest requires exactly {PRETEST_QUESTION_COUNT} questions; "
            f"found {len(questions)}."
        )


def _bkt_parameters():
    try:
        return BKTModelParameters.objects.get()
    except BKTModelParameters.DoesNotExist as error:
        raise AssessmentConfigurationError(
            "BKT parameters are missing. Run seed_bkt_parameters."
        ) from error
    except BKTModelParameters.MultipleObjectsReturned as error:
        raise AssessmentConfigurationError(
            "More than one global BKT parameter row exists."
        ) from error


@transaction.atomic
def complete_pretest(session_id, answers, *, completed_at=None):
    """Grade and persist a pretest exactly once.

    Returns ``(session, completed_now)``. A repeated submission returns the
    already-completed session without changing responses, mastery, or progress.
    """
    session = AssessmentSession.objects.select_for_update().get(pk=session_id)
    if session.type != AssessmentType.PRETEST:
        raise ValueError("complete_pretest requires a pretest session")
    if session.completed_at is not None:
        return session, False

    questions = list(pretest_questions())
    validate_pretest_bank(questions)
    if session.total_questions != len(questions):
        raise AssessmentConfigurationError(
            "The pretest bank changed after this assessment session started."
        )

    question_ids = {question.id for question in questions}
    if not set(answers).issubset(question_ids):
        raise ValueError("answers contain a question outside the pretest bank")

    parameters = _bkt_parameters()
    correct_by_lesson = Counter()
    responses = []
    correct_count = 0
    for question in questions:
        selected_index = answers.get(question.id)
        if selected_index is None:
            continue
        if selected_index not in range(4):
            raise ValueError("selected answer indexes must be from 0 to 3")
        is_correct = selected_index == question.correct_answer_index
        correct_count += int(is_correct)
        correct_by_lesson[question.lesson_id] += int(is_correct)
        responses.append(
            AssessmentResponse(
                assessment_session=session,
                assessment_question=question,
                selected_answer_index=selected_index,
                is_correct=is_correct,
            )
        )

    AssessmentResponse.objects.bulk_create(responses)

    total = len(questions)
    score = (Decimal(correct_count * 100) / Decimal(total)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    finished_at = completed_at or timezone.now()
    session.score = score
    session.completed_at = max(finished_at, session.started_at)
    session.save(update_fields=["score", "completed_at"])

    question_totals = Counter(question.lesson_id for question in questions)
    lessons = list(Lesson.objects.order_by("order_index"))
    for lesson in lessons:
        mastery = init_mastery(
            correct_by_lesson[lesson.id],
            question_totals[lesson.id],
            float(parameters.p_guess),
        )
        BKTMastery.objects.update_or_create(
            student=session.student,
            lesson=lesson,
            defaults={"p_known": Decimal(f"{mastery:.4f}")},
        )

    first_lesson = lessons[0] if lessons else None
    StudentProgress.objects.update_or_create(
        student=session.student,
        defaults={
            "current_lesson": first_lesson,
            "status": StudentProgress.Status.IN_PROGRESS,
            "last_activity_at": session.completed_at,
        },
    )
    return session, True
