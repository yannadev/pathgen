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


def posttest_questions():
    """Return the exact same bank and ordering used by the pretest."""
    return pretest_questions()


def validate_assessment_bank(questions, *, assessment_name):
    if len(questions) != PRETEST_QUESTION_COUNT:
        raise AssessmentConfigurationError(
            f"The {assessment_name} requires exactly {PRETEST_QUESTION_COUNT} questions; "
            f"found {len(questions)}."
        )


def validate_pretest_bank(questions):
    """Backwards-compatible pretest-specific validation entry point."""
    validate_assessment_bank(questions, assessment_name="pretest")


def validate_posttest_bank(questions):
    validate_assessment_bank(questions, assessment_name="posttest")


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


def _complete_assessment(
    session_id,
    answers,
    *,
    assessment_type,
    assessment_name,
    initialize_bkt,
    completed_at=None,
):
    """Grade a session exactly once against the shared assessment bank.

    The pretest path initializes mastery and starts learning. The posttest path
    only persists its research outcome and marks progress as posttest_taken.
    """
    session = AssessmentSession.objects.select_for_update().get(pk=session_id)
    if session.type != assessment_type:
        raise ValueError(f"Assessment session is not a {assessment_name}")
    if session.completed_at is not None:
        return session, False

    questions = list(pretest_questions())
    validate_assessment_bank(questions, assessment_name=assessment_name)
    if session.total_questions != len(questions):
        raise AssessmentConfigurationError(
            f"The {assessment_name} bank changed after this assessment session started."
        )

    question_ids = {question.id for question in questions}
    if not set(answers).issubset(question_ids):
        raise ValueError(f"answers contain a question outside the {assessment_name} bank")

    parameters = _bkt_parameters() if initialize_bkt else None
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

    if initialize_bkt:
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
    else:
        StudentProgress.objects.filter(student=session.student).update(
            status=StudentProgress.Status.POSTTEST_TAKEN,
            last_activity_at=session.completed_at,
        )
    return session, True


@transaction.atomic
def complete_pretest(session_id, answers, *, completed_at=None):
    """Grade and persist a pretest, including initial BKT and path state."""
    return _complete_assessment(
        session_id,
        answers,
        assessment_type=AssessmentType.PRETEST,
        assessment_name="pretest",
        initialize_bkt=True,
        completed_at=completed_at,
    )


@transaction.atomic
def complete_posttest(session_id, answers, *, completed_at=None):
    """Grade and persist a posttest without changing BKT estimates."""
    return _complete_assessment(
        session_id,
        answers,
        assessment_type=AssessmentType.POSTTEST,
        assessment_name="posttest",
        initialize_bkt=False,
        completed_at=completed_at,
    )
