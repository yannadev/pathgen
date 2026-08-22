from datetime import timedelta
from math import ceil

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from accounts.models import ClassStudent, User
from assessment.forms import AssessmentSubmissionForm
from assessment.models import AssessmentConfig, AssessmentSession, AssessmentType
from assessment.services import (
    AssessmentConfigurationError,
    complete_posttest,
    complete_pretest,
    posttest_questions,
    pretest_questions,
    validate_posttest_bank,
    validate_pretest_bank,
)
from core.decorators import student_only
from curriculum.models import Lesson
from progress.models import LessonProgress, StudentProgress


def _has_active_enrollment(student):
    return ClassStudent.objects.filter(
        student=student,
        classroom__is_active=True,
    ).exists()


def _pretest_time_limit():
    configured = (
        AssessmentConfig.objects.filter(type=AssessmentType.PRETEST)
        .values_list("time_limit_seconds", flat=True)
        .first()
    )
    return configured or settings.PATHGEN_PRETEST_TIME_LIMIT_SECONDS


def _posttest_time_limit():
    configured = (
        AssessmentConfig.objects.filter(type=AssessmentType.POSTTEST)
        .values_list("time_limit_seconds", flat=True)
        .first()
    )
    return configured or settings.PATHGEN_PRETEST_TIME_LIMIT_SECONDS


def _question_items(questions, form):
    return [
        {
            "number": number,
            "question": question,
            "field": form[form.field_name(question.id)],
        }
        for number, question in enumerate(questions, start=1)
    ]


def _render_pretest(request, session, form, questions, *, status=200):
    deadline = session.started_at + timedelta(seconds=session.time_limit_seconds)
    remaining_seconds = max(0, ceil((deadline - timezone.now()).total_seconds()))
    return render(
        request,
        "assessment/pretest.html",
        {
            "assessment_session": session,
            "question_items": _question_items(questions, form),
            "remaining_seconds": remaining_seconds,
        },
        status=status,
    )


def _render_posttest(request, session, form, questions, *, status=200):
    deadline = session.started_at + timedelta(seconds=session.time_limit_seconds)
    remaining_seconds = max(0, ceil((deadline - timezone.now()).total_seconds()))
    return render(
        request,
        "assessment/posttest.html",
        {
            "assessment_session": session,
            "question_items": _question_items(questions, form),
            "remaining_seconds": remaining_seconds,
        },
        status=status,
    )


def _posttest_is_unlocked(student):
    """A normal posttest requires every fixed-sequence lesson to be passed."""
    lesson_count = Lesson.objects.count()
    if lesson_count == 0:
        return False
    passed_count = LessonProgress.objects.filter(
        student=student,
        status=LessonProgress.Status.PASSED,
    ).count()
    return passed_count == lesson_count


def _posttest_access_or_response(request, session=None):
    if not _has_active_enrollment(request.user):
        return redirect("accounts:just_chill")
    if not AssessmentSession.objects.filter(
        student=request.user,
        type=AssessmentType.PRETEST,
        completed_at__isnull=False,
    ).exists():
        messages.info(request, "Complete the pretest before starting the posttest.")
        return redirect("progress:student_dashboard")
    if session is not None and session.admin_override:
        return None
    if not _posttest_is_unlocked(request.user):
        raise PermissionDenied("Complete all lessons before starting the posttest.")
    return None


@require_POST
@student_only
@transaction.atomic
def pretest_start(request):
    if not _has_active_enrollment(request.user):
        return redirect("accounts:just_chill")

    # Lock the student row so rapid double-clicks cannot create two sessions.
    User.objects.select_for_update().get(pk=request.user.pk)
    completed = (
        AssessmentSession.objects.filter(
            student=request.user,
            type=AssessmentType.PRETEST,
            completed_at__isnull=False,
        )
        .order_by("-completed_at")
        .first()
    )
    # A reset removes StudentProgress while retaining the completed assessment
    # event. That missing state row deliberately permits a fresh pretest.
    if completed and StudentProgress.objects.filter(student=request.user).exists():
        return redirect("assessment:pretest_result", session_id=completed.id)

    active = AssessmentSession.objects.filter(
        student=request.user,
        type=AssessmentType.PRETEST,
        completed_at__isnull=True,
    ).first()
    if active:
        return redirect("assessment:pretest", session_id=active.id)

    questions = list(pretest_questions())
    try:
        validate_pretest_bank(questions)
    except AssessmentConfigurationError as error:
        messages.error(request, str(error))
        return redirect("progress:student_dashboard")

    session = AssessmentSession.objects.create(
        student=request.user,
        type=AssessmentType.PRETEST,
        score=0,
        total_questions=len(questions),
        time_limit_seconds=_pretest_time_limit(),
        started_at=timezone.now(),
    )
    return redirect("assessment:pretest", session_id=session.id)


@require_GET
@student_only
def pretest(request, session_id):
    session = get_object_or_404(
        AssessmentSession,
        pk=session_id,
        student=request.user,
        type=AssessmentType.PRETEST,
    )
    if session.completed_at is not None:
        return redirect("assessment:pretest_result", session_id=session.id)

    questions = list(pretest_questions())
    try:
        validate_pretest_bank(questions)
    except AssessmentConfigurationError as error:
        return render(
            request,
            "assessment/pretest_unavailable.html",
            {"setup_error": str(error)},
            status=503,
        )
    form = AssessmentSubmissionForm(questions)
    return _render_pretest(request, session, form, questions)


@require_POST
@student_only
def pretest_submit(request, session_id):
    session = get_object_or_404(
        AssessmentSession,
        pk=session_id,
        student=request.user,
        type=AssessmentType.PRETEST,
    )
    if session.completed_at is not None:
        return redirect("assessment:pretest_result", session_id=session.id)

    questions = list(pretest_questions())
    try:
        validate_pretest_bank(questions)
    except AssessmentConfigurationError as error:
        return render(
            request,
            "assessment/pretest_unavailable.html",
            {"setup_error": str(error)},
            status=503,
        )

    form = AssessmentSubmissionForm(questions, request.POST)
    if not form.is_valid():
        return _render_pretest(request, session, form, questions, status=400)

    answers = form.answers()
    deadline = session.started_at + timedelta(seconds=session.time_limit_seconds)
    # Allow only transport latency after expiry. A disabled client timer must
    # not provide unlimited assessment time.
    if timezone.now() > deadline + timedelta(seconds=10):
        answers = {}

    try:
        completed_session, _ = complete_pretest(session.id, answers)
    except AssessmentConfigurationError as error:
        return render(
            request,
            "assessment/pretest_unavailable.html",
            {"setup_error": str(error)},
            status=503,
        )
    return redirect("assessment:pretest_result", session_id=completed_session.id)


@require_GET
@student_only
def pretest_result(request, session_id):
    session = get_object_or_404(
        AssessmentSession.objects.prefetch_related("responses"),
        pk=session_id,
        student=request.user,
        type=AssessmentType.PRETEST,
        completed_at__isnull=False,
    )
    return render(
        request,
        "assessment/pretest_result.html",
        {
            "assessment_session": session,
            "correct_count": sum(
                response.is_correct for response in session.responses.all()
            ),
        },
    )


@require_POST
@student_only
@transaction.atomic
def posttest_start(request):
    if not _has_active_enrollment(request.user):
        return redirect("accounts:just_chill")

    User.objects.select_for_update().get(pk=request.user.pk)
    completed = (
        AssessmentSession.objects.filter(
            student=request.user,
            type=AssessmentType.POSTTEST,
            completed_at__isnull=False,
        )
        .order_by("-completed_at")
        .first()
    )
    if completed:
        return redirect("assessment:posttest_result", session_id=completed.id)

    active = AssessmentSession.objects.filter(
        student=request.user,
        type=AssessmentType.POSTTEST,
        completed_at__isnull=True,
    ).first()
    blocked_response = _posttest_access_or_response(request, active)
    if blocked_response is not None:
        return blocked_response
    if active:
        return redirect("assessment:posttest", session_id=active.id)

    questions = list(posttest_questions())
    try:
        validate_posttest_bank(questions)
    except AssessmentConfigurationError as error:
        messages.error(request, str(error))
        return redirect("progress:lesson_path")

    session = AssessmentSession.objects.create(
        student=request.user,
        type=AssessmentType.POSTTEST,
        score=0,
        total_questions=len(questions),
        time_limit_seconds=_posttest_time_limit(),
        started_at=timezone.now(),
    )
    return redirect("assessment:posttest", session_id=session.id)


@require_GET
@student_only
def posttest(request, session_id):
    session = get_object_or_404(
        AssessmentSession,
        pk=session_id,
        student=request.user,
        type=AssessmentType.POSTTEST,
    )
    if session.completed_at is not None:
        return redirect("assessment:posttest_result", session_id=session.id)
    blocked_response = _posttest_access_or_response(request, session)
    if blocked_response is not None:
        return blocked_response

    questions = list(posttest_questions())
    try:
        validate_posttest_bank(questions)
    except AssessmentConfigurationError as error:
        return render(
            request,
            "assessment/posttest_unavailable.html",
            {"setup_error": str(error)},
            status=503,
        )
    return _render_posttest(
        request,
        session,
        AssessmentSubmissionForm(questions),
        questions,
    )


@require_POST
@student_only
def posttest_submit(request, session_id):
    session = get_object_or_404(
        AssessmentSession,
        pk=session_id,
        student=request.user,
        type=AssessmentType.POSTTEST,
    )
    if session.completed_at is not None:
        return redirect("assessment:posttest_result", session_id=session.id)
    blocked_response = _posttest_access_or_response(request, session)
    if blocked_response is not None:
        return blocked_response

    questions = list(posttest_questions())
    try:
        validate_posttest_bank(questions)
    except AssessmentConfigurationError as error:
        return render(
            request,
            "assessment/posttest_unavailable.html",
            {"setup_error": str(error)},
            status=503,
        )
    form = AssessmentSubmissionForm(questions, request.POST)
    if not form.is_valid():
        return _render_posttest(request, session, form, questions, status=400)

    answers = form.answers()
    deadline = session.started_at + timedelta(seconds=session.time_limit_seconds)
    if timezone.now() > deadline + timedelta(seconds=10):
        answers = {}

    try:
        completed_session, _ = complete_posttest(session.id, answers)
    except AssessmentConfigurationError as error:
        return render(
            request,
            "assessment/posttest_unavailable.html",
            {"setup_error": str(error)},
            status=503,
        )
    return redirect("assessment:posttest_result", session_id=completed_session.id)


@require_GET
@student_only
def posttest_result(request, session_id):
    session = get_object_or_404(
        AssessmentSession.objects.prefetch_related("responses"),
        pk=session_id,
        student=request.user,
        type=AssessmentType.POSTTEST,
        completed_at__isnull=False,
    )
    return render(
        request,
        "assessment/posttest_result.html",
        {
            "assessment_session": session,
            "correct_count": sum(
                response.is_correct for response in session.responses.all()
            ),
        },
    )


@require_GET
@student_only
def completion(request):
    pretest_session = get_object_or_404(
        AssessmentSession.objects.filter(
            student=request.user,
            type=AssessmentType.PRETEST,
            completed_at__isnull=False,
        ).order_by("-completed_at")
    )
    posttest_session = get_object_or_404(
        AssessmentSession.objects.filter(
            student=request.user,
            type=AssessmentType.POSTTEST,
            completed_at__isnull=False,
        ).order_by("-completed_at")
    )
    return render(
        request,
        "assessment/completion.html",
        {
            "pretest_session": pretest_session,
            "posttest_session": posttest_session,
            "learning_gain": posttest_session.score - pretest_session.score,
        },
    )
