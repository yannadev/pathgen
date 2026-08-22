"""Transactional, audited mutations reserved for system administrators."""

from secrets import token_urlsafe

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from accounts.models import AuditLog, ClassStudent, Classroom, User
from adaptive.models import BKTMastery
from assessment.models import AssessmentConfig, AssessmentSession, AssessmentType
from assessment.services import (
    AssessmentConfigurationError,
    posttest_questions,
    validate_posttest_bank,
)
from curriculum.models import Lesson
from progress.models import LessonProgress, StudentProgress


class AdminActionError(ValidationError):
    """A safe, user-facing failure for an otherwise authorized admin action."""


def _audit(admin, action, target, details=None):
    return AuditLog.objects.create(
        admin=admin,
        action=action,
        target_type=target._meta.db_table,
        target_id=target.pk,
        details_jsonb=details or None,
    )


@transaction.atomic
def create_user(admin, *, first_name, last_name, email, role, temp_password):
    if role not in (User.Role.TEACHER, User.Role.STUDENT):
        raise AdminActionError("Administrators can only create teacher or student accounts.")
    user = User.objects.create_user(
        email=email,
        password=temp_password,
        first_name=first_name,
        last_name=last_name,
        role=role,
        password_must_change=True,
    )
    _audit(admin, "create_user", user, {"role": role, "email": user.email})
    return user


@transaction.atomic
def edit_user(admin, user, *, first_name, last_name, email, is_active):
    if user.role == User.Role.ADMIN:
        raise AdminActionError("Administrator accounts cannot be managed from this page.")
    user.first_name = first_name
    user.last_name = last_name
    user.email = email
    user.is_active = is_active
    user.deleted_at = None if is_active else (user.deleted_at or timezone.now())
    user.save(
        update_fields=[
            "first_name",
            "last_name",
            "email",
            "is_active",
            "deleted_at",
            "updated_at",
        ]
    )
    _audit(admin, "edit_user", user, {"is_active": user.is_active, "email": user.email})
    return user


@transaction.atomic
def deactivate_user(admin, user):
    if user.role == User.Role.ADMIN:
        raise AdminActionError("Administrator accounts cannot be deactivated here.")
    was_active = user.is_active
    if was_active:
        user.soft_delete()
    _audit(admin, "deactivate_user", user, {"was_active": was_active})
    return user


@transaction.atomic
def reset_password(admin, user):
    if user.role == User.Role.ADMIN:
        raise AdminActionError("Administrator passwords cannot be reset here.")
    temporary_password = token_urlsafe(12)
    user.set_password(temporary_password)
    user.password_must_change = True
    user.save(update_fields=["password", "password_must_change", "updated_at"])
    _audit(admin, "reset_password", user)
    return temporary_password


@transaction.atomic
def create_class(admin, *, name, teacher):
    if teacher.role != User.Role.TEACHER or not teacher.is_active:
        raise AdminActionError("Choose an active teacher for this class.")
    classroom = Classroom.objects.create(name=name, teacher=teacher)
    _audit(admin, "create_class", classroom, {"teacher_id": str(teacher.id)})
    return classroom


@transaction.atomic
def edit_class(admin, classroom, *, name, teacher):
    if teacher.role != User.Role.TEACHER or not teacher.is_active:
        raise AdminActionError("Choose an active teacher for this class.")
    classroom.name = name
    classroom.teacher = teacher
    classroom.save(update_fields=["name", "teacher"])
    _audit(admin, "edit_class", classroom, {"teacher_id": str(teacher.id)})
    return classroom


@transaction.atomic
def add_student_to_class(admin, classroom, student):
    if not classroom.is_active:
        raise AdminActionError("Students cannot be added to an inactive class.")
    if student.role != User.Role.STUDENT or not student.is_active:
        raise AdminActionError("Choose an active student for this class.")
    enrollment, created = ClassStudent.objects.get_or_create(
        classroom=classroom,
        student=student,
    )
    if not created:
        raise AdminActionError("This student is already enrolled in the class.")
    _audit(
        admin,
        "add_student",
        classroom,
        {"student_id": str(student.id), "enrollment_created_at": enrollment.enrolled_at.isoformat()},
    )
    return enrollment


@transaction.atomic
def remove_student_from_class(admin, classroom, student):
    deleted_count, _ = ClassStudent.objects.filter(
        classroom=classroom,
        student=student,
    ).delete()
    if not deleted_count:
        raise AdminActionError("This student is not enrolled in the class.")
    _audit(admin, "remove_student", classroom, {"student_id": str(student.id)})


@transaction.atomic
def delete_class(admin, classroom):
    if ClassStudent.objects.filter(classroom=classroom, student__is_active=True).exists():
        raise AdminActionError("Remove or deactivate active students before deleting this class.")
    if classroom.is_active:
        classroom.soft_delete()
    _audit(admin, "delete_class", classroom)
    return classroom


@transaction.atomic
def reset_pretest(admin, student):
    if student.role != User.Role.STUDENT:
        raise AdminActionError("Pretest resets are available only for student accounts.")
    # These are current-state tables. Historical sessions, responses, and
    # decisions remain intact for research analysis.
    reset_at = timezone.now()
    closed_active_sessions = AssessmentSession.objects.filter(
        student=student,
        type=AssessmentType.PRETEST,
        completed_at__isnull=True,
    ).update(score=0, completed_at=reset_at)
    deleted_progress, _ = StudentProgress.objects.filter(student=student).delete()
    deleted_lessons, _ = LessonProgress.objects.filter(student=student).delete()
    deleted_masteries, _ = BKTMastery.objects.filter(student=student).delete()
    _audit(
        admin,
        "reset_pretest",
        student,
        {
            "student_progress_deleted": deleted_progress,
            "lesson_progress_deleted": deleted_lessons,
            "bkt_mastery_deleted": deleted_masteries,
            "active_pretest_sessions_closed": closed_active_sessions,
        },
    )


def _posttest_time_limit():
    configured = (
        AssessmentConfig.objects.filter(type=AssessmentType.POSTTEST)
        .values_list("time_limit_seconds", flat=True)
        .first()
    )
    return configured or settings.PATHGEN_PRETEST_TIME_LIMIT_SECONDS


@transaction.atomic
def force_posttest(admin, student):
    if student.role != User.Role.STUDENT:
        raise AdminActionError("Posttest overrides are available only for student accounts.")
    questions = list(posttest_questions())
    try:
        validate_posttest_bank(questions)
    except AssessmentConfigurationError as error:
        raise AdminActionError(str(error)) from error
    active_session = (
        AssessmentSession.objects.select_for_update()
        .filter(
            student=student,
            type=AssessmentType.POSTTEST,
            completed_at__isnull=True,
        )
        .order_by("started_at")
        .first()
    )
    if active_session is None:
        active_session = AssessmentSession.objects.create(
            student=student,
            type=AssessmentType.POSTTEST,
            score=0,
            total_questions=len(questions),
            time_limit_seconds=_posttest_time_limit(),
            admin_override=True,
            started_at=timezone.now(),
        )
    elif not active_session.admin_override:
        active_session.admin_override = True
        active_session.save(update_fields=["admin_override"])
    _audit(admin, "force_posttest", active_session, {"student_id": str(student.id)})
    return active_session


@transaction.atomic
def extend_time(admin, assessment_session, *, minutes):
    if assessment_session.completed_at is not None:
        raise AdminActionError("Only active assessment sessions can be extended.")
    if minutes <= 0:
        raise AdminActionError("Extension minutes must be greater than zero.")
    seconds_added = minutes * 60
    assessment_session.time_limit_seconds += seconds_added
    assessment_session.save(update_fields=["time_limit_seconds"])
    _audit(
        admin,
        "extend_time",
        assessment_session,
        {"minutes_added": minutes, "time_limit_seconds": assessment_session.time_limit_seconds},
    )
    return assessment_session
