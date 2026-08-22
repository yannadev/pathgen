import uuid

from django.conf import settings
from django.db import models
from django.db.models import F, Q

from curriculum.models import AssessmentQuestion


class AssessmentType(models.TextChoices):
    PRETEST = "pretest", "Pretest"
    POSTTEST = "posttest", "Posttest"


class AssessmentConfig(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    type = models.CharField(max_length=10, choices=AssessmentType.choices, unique=True)
    time_limit_seconds = models.PositiveIntegerField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "assessment_config"
        constraints = [
            models.CheckConstraint(
                condition=Q(type__in=["pretest", "posttest"]),
                name="assessment_config_type_valid",
            ),
            models.CheckConstraint(
                condition=(
                    Q(time_limit_seconds__isnull=True)
                    | Q(time_limit_seconds__gt=0)
                ),
                name="assessment_config_time_positive",
            ),
        ]

    def __str__(self):
        return self.get_type_display()


class AssessmentSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.RESTRICT,
        related_name="assessment_sessions",
    )
    type = models.CharField(max_length=10, choices=AssessmentType.choices)
    score = models.DecimalField(max_digits=5, decimal_places=2)
    total_questions = models.PositiveIntegerField()
    time_limit_seconds = models.PositiveIntegerField()
    admin_override = models.BooleanField(default=False)
    started_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "assessment_sessions"
        constraints = [
            models.CheckConstraint(
                condition=Q(type__in=["pretest", "posttest"]),
                name="assessment_sessions_type_valid",
            ),
            models.CheckConstraint(
                condition=Q(score__gte=0) & Q(score__lte=100),
                name="assessment_sessions_score_0_100",
            ),
            models.CheckConstraint(
                condition=Q(total_questions__gt=0),
                name="assessment_sessions_questions_positive",
            ),
            models.CheckConstraint(
                condition=Q(time_limit_seconds__gt=0),
                name="assessment_sessions_time_positive",
            ),
            models.CheckConstraint(
                condition=(
                    Q(completed_at__isnull=True)
                    | Q(completed_at__gte=F("started_at"))
                ),
                name="assessment_sessions_completed_after_start",
            ),
        ]

    def __str__(self):
        return f"{self.student} - {self.get_type_display()}"


class AssessmentResponse(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assessment_session = models.ForeignKey(
        AssessmentSession,
        on_delete=models.RESTRICT,
        related_name="responses",
    )
    assessment_question = models.ForeignKey(
        AssessmentQuestion,
        on_delete=models.RESTRICT,
        related_name="responses",
    )
    selected_answer_index = models.PositiveSmallIntegerField()
    is_correct = models.BooleanField()

    class Meta:
        db_table = "assessment_responses"
        constraints = [
            models.CheckConstraint(
                condition=Q(selected_answer_index__range=(0, 3)),
                name="assessment_response_answer_index_0_3",
            ),
            models.UniqueConstraint(
                fields=["assessment_session", "assessment_question"],
                name="assessment_response_unique_question",
            ),
        ]

    def __str__(self):
        return f"{self.assessment_session_id}: {self.assessment_question_id}"
