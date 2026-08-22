from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Classroom, ClassStudent, User
from assessment.models import AssessmentSession, AssessmentType
from curriculum.models import Activity, Lesson
from progress.models import LessonProgress, StudentProgress


class StudentLearningPathTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_content", stdout=StringIO())
        cls.teacher = User.objects.create_user(
            email="teacher.path@example.com",
            password="teacher-pass",
            first_name="Mara",
            last_name="Santos",
            role=User.Role.TEACHER,
        )
        cls.student = User.objects.create_user(
            email="student.path@example.com",
            password="student-pass",
            first_name="Lino",
            last_name="Reyes",
            role=User.Role.STUDENT,
        )
        cls.waiting_student = User.objects.create_user(
            email="waiting.path@example.com",
            password="waiting-pass",
            first_name="Nico",
            last_name="Garcia",
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

    def _complete_pretest_and_start_path(self, current_lesson=None):
        now = timezone.now()
        AssessmentSession.objects.create(
            student=self.student,
            type=AssessmentType.PRETEST,
            score=Decimal("50.00"),
            total_questions=40,
            time_limit_seconds=3600,
            started_at=now,
            completed_at=now,
        )
        return StudentProgress.objects.create(
            student=self.student,
            current_lesson=current_lesson or self.lessons[0],
            status=StudentProgress.Status.IN_PROGRESS,
            last_activity_at=now,
        )

    def test_dashboard_shows_progress_and_learning_path_link(self):
        self._complete_pretest_and_start_path()

        response = self.client.get(reverse("progress:student_dashboard"))

        self.assertContains(response, "0 of 4 lessons completed")
        self.assertContains(response, "Next: Operations On Integers")
        self.assertContains(response, reverse("progress:lesson_path"))

    def test_learning_path_marks_passed_current_and_locked_lessons(self):
        self._complete_pretest_and_start_path(self.lessons[1])
        LessonProgress.objects.create(
            student=self.student,
            lesson=self.lessons[0],
            status=LessonProgress.Status.PASSED,
            first_started_at=timezone.now(),
            last_activity_at=timezone.now(),
        )

        response = self.client.get(reverse("progress:lesson_path"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["state"] for item in response.context["path_items"]],
            ["passed", "current", "locked", "locked"],
        )
        self.assertContains(response, "follows this pair of lessons", html=False)
        self.assertContains(response, "Locked")

    def test_learning_path_reveals_activity_after_its_two_lessons(self):
        self._complete_pretest_and_start_path(self.lessons[1])
        now = timezone.now()
        for lesson in self.lessons[:2]:
            LessonProgress.objects.create(
                student=self.student,
                lesson=lesson,
                status=LessonProgress.Status.PASSED,
                first_started_at=now,
                last_activity_at=now,
            )

        response = self.client.get(reverse("progress:lesson_path"))
        activity = Activity.objects.get(order_index=1)

        self.assertEqual(response.status_code, 200)
        activity_item = response.context["path_items"][1]
        self.assertEqual(activity_item["activity"], activity)
        self.assertEqual(activity_item["activity_state"], "current")
        self.assertContains(response, "Start activity")

    def test_learning_path_requires_pretest_and_enrollment(self):
        response = self.client.get(reverse("progress:lesson_path"))
        self.assertRedirects(response, reverse("progress:student_dashboard"))

        self.client.force_login(self.waiting_student)
        response = self.client.get(reverse("progress:lesson_path"))
        self.assertRedirects(response, reverse("accounts:just_chill"))

    def test_non_student_cannot_open_learning_path(self):
        self.client.force_login(self.teacher)
        response = self.client.get(reverse("progress:lesson_path"))
        self.assertEqual(response.status_code, 403)
