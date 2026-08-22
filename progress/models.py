import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q

from curriculum.models import Lesson


class StudentProgress(models.Model):
    class Status(models.TextChoices):
        NOT_STARTED = "not_started", "Not started"
        IN_PROGRESS = "in_progress", "In progress"
        COMPLETED = "completed", "Completed"
        POSTTEST_TAKEN = "posttest_taken", "Posttest taken"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.RESTRICT,
        related_name="progress",
    )
    current_lesson = models.ForeignKey(
        Lesson,
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        related_name="current_students",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NOT_STARTED,
    )
    last_activity_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "student_progress"
        constraints = [
            models.CheckConstraint(
                condition=Q(
                    status__in=[
                        "not_started",
                        "in_progress",
                        "completed",
                        "posttest_taken",
                    ]
                ),
                name="student_progress_status_valid",
            ),
        ]

    def __str__(self):
        return f"{self.student}: {self.get_status_display()}"


class LessonProgress(models.Model):
    class Status(models.TextChoices):
        NOT_STARTED = "not_started", "Not started"
        IN_PROGRESS = "in_progress", "In progress"
        PASSED = "passed", "Passed"
        NEEDS_REVIEW = "needs_review", "Needs review"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.RESTRICT,
        related_name="lesson_progress_entries",
    )
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.RESTRICT,
        related_name="student_progress_entries",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NOT_STARTED,
    )
    first_started_at = models.DateTimeField(null=True, blank=True)
    last_activity_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "lesson_progress"
        constraints = [
            models.UniqueConstraint(
                fields=["student", "lesson"],
                name="lesson_progress_unique_student_lesson",
            ),
            models.CheckConstraint(
                condition=Q(
                    status__in=[
                        "not_started",
                        "in_progress",
                        "passed",
                        "needs_review",
                    ]
                ),
                name="lesson_progress_status_valid",
            ),
            models.CheckConstraint(
                condition=(
                    Q(first_started_at__isnull=True)
                    | Q(last_activity_at__isnull=True)
                    | Q(last_activity_at__gte=models.F("first_started_at"))
                ),
                name="lesson_progress_activity_after_start",
            ),
        ]

    def __str__(self):
        return f"{self.student} - {self.lesson}: {self.get_status_display()}"
