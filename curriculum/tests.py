from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from curriculum.models import (
    Activity,
    ActivityQuestion,
    AssessmentQuestion,
    ExerciseQuestion,
    Lesson,
)


class CurriculumSeedCommandTests(TestCase):
    expected_counts = {
        "lessons": 4,
        "assessment_questions": 40,
        "exercise_questions": 60,
        "activities": 2,
        "activity_questions": 60,
    }

    def assert_seeded_counts(self):
        self.assertEqual(Lesson.objects.count(), self.expected_counts["lessons"])
        self.assertEqual(
            AssessmentQuestion.objects.count(),
            self.expected_counts["assessment_questions"],
        )
        self.assertEqual(
            ExerciseQuestion.objects.count(),
            self.expected_counts["exercise_questions"],
        )
        self.assertEqual(Activity.objects.count(), self.expected_counts["activities"])
        self.assertEqual(
            ActivityQuestion.objects.count(),
            self.expected_counts["activity_questions"],
        )

    def test_seed_content_loads_all_demo_content_and_is_idempotent(self):
        output = StringIO()
        call_command("seed_content", stdout=output)

        self.assert_seeded_counts()
        self.assertIn("Content seed complete", output.getvalue())

        lessons = list(Lesson.objects.order_by("order_index"))
        self.assertEqual(
            [lesson.prerequisite_lesson_id for lesson in lessons],
            [None, lessons[0].id, lessons[1].id, lessons[2].id],
        )
        self.assertEqual(
            ActivityQuestion.objects.filter(activity__order_index=1).count(),
            30,
        )
        self.assertEqual(
            ActivityQuestion.objects.filter(activity__order_index=2).count(),
            30,
        )
        self.assertTrue(
            all(
                len(question.options_jsonb) == 4
                for question in AssessmentQuestion.objects.all()
            )
        )

        original_ids = set(AssessmentQuestion.objects.values_list("id", flat=True))
        lesson = lessons[0]
        lesson.title = "Temporary title"
        lesson.save(update_fields=["title"])

        call_command("seed_content")

        self.assert_seeded_counts()
        self.assertEqual(
            set(AssessmentQuestion.objects.values_list("id", flat=True)),
            original_ids,
        )
        lesson.refresh_from_db()
        self.assertEqual(lesson.title, "Operations On Integers")

    def test_reset_content_requires_confirmation_and_clears_unreferenced_content(self):
        call_command("seed_content")

        with self.assertRaises(CommandError):
            call_command("reset_content")
        self.assert_seeded_counts()

        call_command("reset_content", "--yes")

        self.assertEqual(Lesson.objects.count(), 0)
        self.assertEqual(AssessmentQuestion.objects.count(), 0)
        self.assertEqual(ExerciseQuestion.objects.count(), 0)
        self.assertEqual(Activity.objects.count(), 0)
        self.assertEqual(ActivityQuestion.objects.count(), 0)
