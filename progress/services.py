"""Learning-path state and access helpers."""

from django.db import transaction
from django.utils import timezone

from accounts.models import ClassStudent
from assessment.models import AssessmentSession, AssessmentType
from curriculum.models import Lesson
from progress.models import LessonProgress, StudentProgress


def has_active_enrollment(student):
    return ClassStudent.objects.filter(
        student=student,
        classroom__is_active=True,
    ).exists()


def completed_pretest(student):
    return (
        AssessmentSession.objects.filter(
            student=student,
            type=AssessmentType.PRETEST,
            completed_at__isnull=False,
        )
        .order_by("-completed_at")
        .first()
    )


def student_progress(student):
    return StudentProgress.objects.filter(student=student).select_related(
        "current_lesson"
    ).first()


def lesson_is_available(student, lesson, progress=None):
    """Allow the current lesson and completed lessons for revision."""
    progress = progress or student_progress(student)
    if progress is None:
        return False
    if progress.current_lesson_id == lesson.id:
        return True
    return LessonProgress.objects.filter(
        student=student,
        lesson=lesson,
        status=LessonProgress.Status.PASSED,
    ).exists()


@transaction.atomic
def record_lesson_opened(student, lesson):
    """Mark a current lesson as started without changing completion state."""
    progress = StudentProgress.objects.select_for_update().get(student=student)
    if progress.current_lesson_id != lesson.id:
        return None

    now = timezone.now()
    lesson_progress, created = LessonProgress.objects.select_for_update().get_or_create(
        student=student,
        lesson=lesson,
        defaults={
            "status": LessonProgress.Status.IN_PROGRESS,
            "first_started_at": now,
            "last_activity_at": now,
        },
    )
    if not created and lesson_progress.status != LessonProgress.Status.PASSED:
        lesson_progress.last_activity_at = now
        lesson_progress.save(update_fields=["last_activity_at"])

    progress.last_activity_at = now
    progress.save(update_fields=["last_activity_at"])
    return lesson_progress
