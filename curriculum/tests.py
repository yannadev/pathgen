from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Classroom, ClassStudent, User
from assessment.models import AssessmentSession, AssessmentType
from curriculum.models import (
    Activity,
    ActivityQuestion,
    AssessmentQuestion,
    ExerciseQuestion,
    Lesson,
)
from progress.models import LessonProgress, StudentProgress


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


class StudentLessonPageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_content", stdout=StringIO())
        cls.teacher = User.objects.create_user(
            email="teacher.lesson@example.com",
            password="teacher-pass",
            first_name="Mara",
            last_name="Santos",
            role=User.Role.TEACHER,
        )
        cls.student = User.objects.create_user(
            email="student.lesson@example.com",
            password="student-pass",
            first_name="Lino",
            last_name="Reyes",
            role=User.Role.STUDENT,
        )
        cls.classroom = Classroom.objects.create(
            name="Grade 7 Mabini",
            teacher=cls.teacher,
        )
        ClassStudent.objects.create(classroom=cls.classroom, student=cls.student)
        cls.lessons = list(Lesson.objects.order_by("order_index"))

    def setUp(self):
        self.client.force_login(self.student)

    def _enable_path(self, current_lesson):
        now = timezone.now()
        AssessmentSession.objects.create(
            student=self.student,
            type=AssessmentType.PRETEST,
            score=0,
            total_questions=40,
            time_limit_seconds=3600,
            started_at=now,
            completed_at=now,
        )
        StudentProgress.objects.create(
            student=self.student,
            current_lesson=current_lesson,
            status=StudentProgress.Status.IN_PROGRESS,
            last_activity_at=now,
        )

    def test_current_lesson_renders_content_and_records_progress(self):
        lesson = self.lessons[0]
        self._enable_path(lesson)

        response = self.client.get(
            reverse("curriculum:lesson_page", kwargs={"slug": lesson.slug})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, lesson.content_jsonb[0]["text"])
        self.assertContains(response, "exercise-start-dialog")
        progress = LessonProgress.objects.get(student=self.student, lesson=lesson)
        self.assertEqual(progress.status, LessonProgress.Status.IN_PROGRESS)
        self.assertIsNotNone(progress.first_started_at)

    def test_completed_lesson_can_be_read_but_future_lesson_is_forbidden(self):
        self._enable_path(self.lessons[1])
        LessonProgress.objects.create(
            student=self.student,
            lesson=self.lessons[0],
            status=LessonProgress.Status.PASSED,
            first_started_at=timezone.now(),
            last_activity_at=timezone.now(),
        )

        completed_response = self.client.get(
            reverse("curriculum:lesson_page", kwargs={"slug": self.lessons[0].slug})
        )
        future_response = self.client.get(
            reverse("curriculum:lesson_page", kwargs={"slug": self.lessons[2].slug})
        )

        self.assertEqual(completed_response.status_code, 200)
        self.assertEqual(future_response.status_code, 403)

    def test_lesson_requires_completed_pretest(self):
        response = self.client.get(
            reverse("curriculum:lesson_page", kwargs={"slug": self.lessons[0].slug})
        )

        self.assertRedirects(response, reverse("progress:student_dashboard"))
