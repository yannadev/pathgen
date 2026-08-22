from datetime import timedelta
from math import ceil

from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from accounts.models import ClassStudent, User
from assessment.forms import AssessmentSubmissionForm
from assessment.models import AssessmentConfig, AssessmentSession, AssessmentType
from assessment.services import (
    AssessmentConfigurationError,
    complete_pretest,
    pretest_questions,
    validate_pretest_bank,
)
from core.decorators import student_only


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
    if completed:
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
