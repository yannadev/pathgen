import uuid

from django.conf import settings
from django.db import models
from django.db.models import F, Q

from curriculum.models import Activity, ActivityQuestion, ExerciseQuestion, Lesson


class ExerciseSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.RESTRICT,
        related_name="exercise_sessions",
    )
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.RESTRICT,
        related_name="exercise_sessions",
    )
    score = models.DecimalField(max_digits=5, decimal_places=2)
    total_questions = models.PositiveIntegerField()
    study_time_seconds = models.PositiveIntegerField()
    ai_feedback = models.TextField(null=True, blank=True)
    started_at = models.DateTimeField()
    completed_at = models.DateTimeField()

    class Meta:
        db_table = "exercise_sessions"
        constraints = [
            models.CheckConstraint(
                condition=Q(score__gte=0) & Q(score__lte=100),
                name="exercise_sessions_score_0_100",
            ),
            models.CheckConstraint(
                condition=Q(total_questions__gt=0),
                name="exercise_sessions_questions_positive",
            ),
            models.CheckConstraint(
                condition=Q(study_time_seconds__gte=0),
                name="exercise_sessions_study_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(completed_at__gte=F("started_at")),
                name="exercise_sessions_completed_after_start",
            ),
        ]

    def __str__(self):
        return f"{self.student} - {self.lesson} ({self.score}%)"


class ExerciseResponse(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    exercise_session = models.ForeignKey(
        ExerciseSession,
        on_delete=models.RESTRICT,
        related_name="responses",
    )
    exercise_question = models.ForeignKey(
        ExerciseQuestion,
        on_delete=models.RESTRICT,
        related_name="responses",
    )
    selected_answer_index = models.PositiveSmallIntegerField()
    is_correct = models.BooleanField()
    hint_used = models.BooleanField(default=False)

    class Meta:
        db_table = "exercise_responses"
        constraints = [
            models.CheckConstraint(
                condition=Q(selected_answer_index__range=(0, 3)),
                name="exercise_response_answer_index_0_3",
            ),
            models.UniqueConstraint(
                fields=["exercise_session", "exercise_question"],
                name="exercise_response_unique_question",
            ),
        ]

    def __str__(self):
        return f"{self.exercise_session_id}: {self.exercise_question_id}"


class ActivitySession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.RESTRICT,
        related_name="activity_sessions",
    )
    activity = models.ForeignKey(
        Activity,
        on_delete=models.RESTRICT,
        related_name="sessions",
    )
    score = models.DecimalField(max_digits=5, decimal_places=2)
    total_questions = models.PositiveIntegerField()
    study_time_seconds = models.PositiveIntegerField()
    ai_feedback = models.TextField(null=True, blank=True)
    started_at = models.DateTimeField()
    completed_at = models.DateTimeField()

    class Meta:
        db_table = "activity_sessions"
        constraints = [
            models.CheckConstraint(
                condition=Q(score__gte=0) & Q(score__lte=100),
                name="activity_sessions_score_0_100",
            ),
            models.CheckConstraint(
                condition=Q(total_questions__gt=0),
                name="activity_sessions_questions_positive",
            ),
            models.CheckConstraint(
                condition=Q(study_time_seconds__gte=0),
                name="activity_sessions_study_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(completed_at__gte=F("started_at")),
                name="activity_sessions_completed_after_start",
            ),
        ]

    def __str__(self):
        return f"{self.student} - {self.activity} ({self.score}%)"


class ActivityResponse(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    activity_session = models.ForeignKey(
        ActivitySession,
        on_delete=models.RESTRICT,
        related_name="responses",
    )
    activity_question = models.ForeignKey(
        ActivityQuestion,
        on_delete=models.RESTRICT,
        related_name="responses",
    )
    selected_answer_index = models.PositiveSmallIntegerField()
    is_correct = models.BooleanField()
    video_checkpoint_reached = models.BooleanField(null=True, blank=True)

    class Meta:
        db_table = "activity_responses"
        constraints = [
            models.CheckConstraint(
                condition=Q(selected_answer_index__range=(0, 3)),
                name="activity_response_answer_index_0_3",
            ),
            models.UniqueConstraint(
                fields=["activity_session", "activity_question"],
                name="activity_response_unique_question",
            ),
        ]

    def __str__(self):
        return f"{self.activity_session_id}: {self.activity_question_id}"
