"""Deliberately remove development/demo curriculum content."""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models.deletion import RestrictedError

from curriculum.models import (
    Activity,
    ActivityQuestion,
    AssessmentQuestion,
    ExerciseQuestion,
    Lesson,
)


class Command(BaseCommand):
    help = "Delete seeded curriculum content. Blocked when research data references it."

    def add_arguments(self, parser):
        parser.add_argument(
            "--yes",
            action="store_true",
            help="Confirm deletion of curriculum content.",
        )

    def handle(self, *args, **options):
        if not options["yes"]:
            raise CommandError(
                "Refusing to delete content without --yes. "
                "Run: python manage.py reset_content --yes"
            )

        try:
            with transaction.atomic():
                deleted = {
                    "activity_questions": ActivityQuestion.objects.all().delete()[0],
                    "exercise_questions": ExerciseQuestion.objects.all().delete()[0],
                    "assessment_questions": AssessmentQuestion.objects.all().delete()[0],
                    "activities": Activity.objects.all().delete()[0],
                    "lessons": Lesson.objects.all().delete()[0],
                }
        except RestrictedError as error:
            raise CommandError(
                "Content cannot be reset because research or progress data still references it."
            ) from error

        summary = ", ".join(f"{name}: {count}" for name, count in deleted.items())
        self.stdout.write(self.style.SUCCESS(f"Content reset complete. {summary}"))
