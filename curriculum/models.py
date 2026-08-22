import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.db.models.lookups import Exact

from core.db_expressions import JsonArrayLength
from core.validators import validate_four_options


def four_options_constraint(name):
    return models.CheckConstraint(
        condition=Exact(JsonArrayLength("options_jsonb"), 4),
        name=name,
    )


class Lesson(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(max_length=100, unique=True)
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    order_index = models.PositiveIntegerField(unique=True)
    prerequisite_lesson = models.ForeignKey(
        "self",
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        related_name="dependent_lessons",
    )
    content_jsonb = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "lessons"
        constraints = [
            models.CheckConstraint(
                condition=Q(order_index__gte=1),
                name="lessons_order_positive",
            ),
            models.CheckConstraint(
                condition=~Q(id=F("prerequisite_lesson")),
                name="lessons_not_self_prerequisite",
            ),
        ]

    def clean(self):
        super().clean()
        if self.prerequisite_lesson_id:
            if self.prerequisite_lesson_id == self.id:
                raise ValidationError(
                    {"prerequisite_lesson": "A lesson cannot require itself."}
                )
            if self.prerequisite_lesson.order_index >= self.order_index:
                raise ValidationError(
                    {
                        "prerequisite_lesson": (
                            "The prerequisite must appear earlier in the lesson sequence."
                        )
                    }
                )

    def __str__(self):
        return f"{self.order_index}. {self.title}"


class AssessmentQuestion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.RESTRICT,
        related_name="assessment_questions",
    )
    question_text = models.TextField()
    options_jsonb = models.JSONField(validators=[validate_four_options])
    correct_answer_index = models.PositiveSmallIntegerField()
    has_image = models.BooleanField(default=False)
    image_url = models.URLField(max_length=500, null=True, blank=True)

    class Meta:
        db_table = "assessment_questions"
        constraints = [
            four_options_constraint("assessment_options_exactly_four"),
            models.CheckConstraint(
                condition=Q(correct_answer_index__range=(0, 3)),
                name="assessment_answer_index_0_3",
            ),
            models.CheckConstraint(
                condition=Q(has_image=False) | Q(image_url__isnull=False),
                name="assessment_image_url_when_needed",
            ),
        ]

    def __str__(self):
        return self.question_text[:80]


class ExerciseQuestion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.RESTRICT,
        related_name="exercise_questions",
    )
    question_text = models.TextField()
    options_jsonb = models.JSONField(validators=[validate_four_options])
    correct_answer_index = models.PositiveSmallIntegerField()
    hint_text = models.TextField()

    class Meta:
        db_table = "exercise_questions"
        constraints = [
            four_options_constraint("exercise_options_exactly_four"),
            models.CheckConstraint(
                condition=Q(correct_answer_index__range=(0, 3)),
                name="exercise_answer_index_0_3",
            ),
        ]

    def __str__(self):
        return self.question_text[:80]


class Activity(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    order_index = models.PositiveIntegerField(unique=True)
    lesson_1 = models.ForeignKey(
        Lesson,
        on_delete=models.RESTRICT,
        related_name="activities_as_first_lesson",
    )
    lesson_2 = models.ForeignKey(
        Lesson,
        on_delete=models.RESTRICT,
        related_name="activities_as_second_lesson",
    )

    class Meta:
        db_table = "activities"
        constraints = [
            models.CheckConstraint(
                condition=Q(order_index__gte=1),
                name="activities_order_positive",
            ),
            models.CheckConstraint(
                condition=~Q(lesson_1=F("lesson_2")),
                name="activities_lessons_distinct",
            ),
        ]

    def clean(self):
        super().clean()
        if self.lesson_1_id and self.lesson_2_id:
            if self.lesson_1_id == self.lesson_2_id:
                raise ValidationError("An activity must cover two distinct lessons.")
            if self.lesson_2.order_index != self.lesson_1.order_index + 1:
                raise ValidationError(
                    "An activity must cover two consecutive lessons in sequence order."
                )

    def __str__(self):
        return self.title


class ActivityQuestion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    activity = models.ForeignKey(
        Activity,
        on_delete=models.RESTRICT,
        related_name="questions",
    )
    question_text = models.TextField()
    options_jsonb = models.JSONField(validators=[validate_four_options])
    correct_answer_index = models.PositiveSmallIntegerField()
    media_jsonb = models.JSONField(null=True, blank=True)
    order_index = models.PositiveIntegerField()
    hint_text = models.TextField()

    class Meta:
        db_table = "activity_questions"
        constraints = [
            four_options_constraint("activity_options_exactly_four"),
            models.CheckConstraint(
                condition=Q(correct_answer_index__range=(0, 3)),
                name="activity_answer_index_0_3",
            ),
            models.CheckConstraint(
                condition=Q(order_index__gte=1),
                name="activity_questions_order_positive",
            ),
            models.UniqueConstraint(
                fields=["activity", "order_index"],
                name="activity_questions_unique_order",
            ),
        ]

    def __str__(self):
        return self.question_text[:80]
