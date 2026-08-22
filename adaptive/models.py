import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q

from curriculum.models import Lesson
from practice.models import ActivitySession, ExerciseSession


class QAction(models.TextChoices):
    ADVANCE = "advance", "Advance"
    REVIEW = "review", "Review"
    RETAKE = "retake", "Retake"


class BKTModelParameters(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    p_learn = models.DecimalField(max_digits=5, decimal_places=4)
    p_slip = models.DecimalField(max_digits=5, decimal_places=4)
    p_guess = models.DecimalField(max_digits=5, decimal_places=4)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "bkt_model_parameters"
        constraints = [
            models.CheckConstraint(
                condition=Q(p_learn__gte=0) & Q(p_learn__lte=1),
                name="bkt_parameters_learn_0_1",
            ),
            models.CheckConstraint(
                condition=Q(p_slip__gte=0) & Q(p_slip__lte=1),
                name="bkt_parameters_slip_0_1",
            ),
            models.CheckConstraint(
                condition=Q(p_guess__gte=0) & Q(p_guess__lte=1),
                name="bkt_parameters_guess_0_1",
            ),
        ]

    def __str__(self):
        return f"L={self.p_learn}, S={self.p_slip}, G={self.p_guess}"


class BKTMastery(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.RESTRICT,
        related_name="mastery_estimates",
    )
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.RESTRICT,
        related_name="mastery_estimates",
    )
    p_known = models.DecimalField(max_digits=5, decimal_places=4)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "bkt_mastery"
        constraints = [
            models.UniqueConstraint(
                fields=["student", "lesson"],
                name="bkt_mastery_unique_student_lesson",
            ),
            models.CheckConstraint(
                condition=Q(p_known__gte=0) & Q(p_known__lte=1),
                name="bkt_mastery_known_0_1",
            ),
        ]

    def __str__(self):
        return f"{self.student} - {self.lesson}: {self.p_known}"


class DecisionSnapshotMixin(models.Model):
    action = models.CharField(max_length=10, choices=QAction.choices)
    mastery_at_decision = models.DecimalField(max_digits=5, decimal_places=4)
    study_time_seconds = models.PositiveIntegerField()
    attempt_count = models.PositiveIntegerField()
    session_score = models.DecimalField(max_digits=5, decimal_places=2)
    hint_count = models.PositiveIntegerField()
    decided_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True


def decision_constraints(prefix):
    return [
        models.CheckConstraint(
            condition=Q(action__in=["advance", "review", "retake"]),
            name=f"{prefix}_action_valid",
        ),
        models.CheckConstraint(
            condition=(
                Q(mastery_at_decision__gte=0)
                & Q(mastery_at_decision__lte=1)
            ),
            name=f"{prefix}_mastery_0_1",
        ),
        models.CheckConstraint(
            condition=Q(study_time_seconds__gte=0),
            name=f"{prefix}_study_nonnegative",
        ),
        models.CheckConstraint(
            condition=Q(attempt_count__gt=0),
            name=f"{prefix}_attempt_positive",
        ),
        models.CheckConstraint(
            condition=Q(session_score__gte=0) & Q(session_score__lte=100),
            name=f"{prefix}_score_0_100",
        ),
        models.CheckConstraint(
            condition=Q(hint_count__gte=0),
            name=f"{prefix}_hints_nonnegative",
        ),
    ]


class ExerciseQDecision(DecisionSnapshotMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.RESTRICT,
        related_name="exercise_q_decisions",
    )
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.RESTRICT,
        related_name="exercise_q_decisions",
    )
    exercise_session = models.OneToOneField(
        ExerciseSession,
        on_delete=models.RESTRICT,
        related_name="q_decision",
    )

    class Meta:
        db_table = "exercise_q_decisions"
        constraints = decision_constraints("exercise_q")

    def __str__(self):
        return f"{self.student} - {self.lesson}: {self.get_action_display()}"


class ActivityQDecision(DecisionSnapshotMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.RESTRICT,
        related_name="activity_q_decisions",
    )
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.RESTRICT,
        related_name="activity_q_decisions",
    )
    activity_session = models.OneToOneField(
        ActivitySession,
        on_delete=models.RESTRICT,
        related_name="q_decision",
    )

    class Meta:
        db_table = "activity_q_decisions"
        constraints = decision_constraints("activity_q")

    def __str__(self):
        return f"{self.student} - {self.lesson}: {self.get_action_display()}"
