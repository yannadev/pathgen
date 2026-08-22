from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Classroom, ClassStudent, User, UserSession
from assessment.models import AssessmentSession, AssessmentType
from core.session_tracking import SESSION_RECORD_KEY
from curriculum.models import ExerciseQuestion, Lesson
from practice.models import ExerciseSession
from practice.session_state import (
    EXERCISE_ATTEMPT_SESSION_KEY,
    exercise_study_time_seconds,
)
from progress.models import LessonProgress, StudentProgress


class ShortExerciseFlowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_content", stdout=StringIO())
        cls.teacher = User.objects.create_user(
            email="teacher.exercise@example.com",
            password="teacher-pass",
            first_name="Mara",
            last_name="Santos",
            role=User.Role.TEACHER,
        )
        cls.student = User.objects.create_user(
            email="student.exercise@example.com",
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
        StudentProgress.objects.create(
            student=self.student,
            current_lesson=self.lessons[0],
            status=StudentProgress.Status.IN_PROGRESS,
            last_activity_at=now,
        )

    @property
    def lesson(self):
        return self.lessons[0]

    def _start_url(self, lesson=None):
        return reverse(
            "practice:exercise_start",
            kwargs={"lesson_slug": (lesson or self.lesson).slug},
        )

    def _exercise_url(self, lesson=None):
        return reverse(
            "practice:short_exercise",
            kwargs={"lesson_slug": (lesson or self.lesson).slug},
        )

    def test_start_selects_fifteen_questions_and_marks_lesson_in_progress(self):
        response = self.client.post(self._start_url())

        self.assertRedirects(response, self._exercise_url())
        attempt = self.client.session[EXERCISE_ATTEMPT_SESSION_KEY]
        self.assertEqual(len(attempt["question_ids"]), 15)
        self.assertEqual(len(set(attempt["question_ids"])), 15)
        self.assertEqual(
            ExerciseQuestion.objects.filter(id__in=attempt["question_ids"]).count(), 15
        )
        self.assertFalse(ExerciseSession.objects.exists())
        progress = LessonProgress.objects.get(student=self.student, lesson=self.lesson)
        self.assertEqual(progress.status, LessonProgress.Status.IN_PROGRESS)

    def test_delivery_uses_saved_order_and_does_not_expose_answers_or_hints(self):
        self.client.post(self._start_url())
        attempt = self.client.session[EXERCISE_ATTEMPT_SESSION_KEY]

        response = self.client.get(self._exercise_url())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["attempt_id"], attempt["attempt_id"])
        self.assertEqual(len(response.context["question_items"]), 15)
        self.assertNotContains(response, "correct_answer_index")
        self.assertNotContains(response, "Hint:")

    def test_repeated_start_resumes_same_attempt_and_direct_delivery_redirects(self):
        response = self.client.get(self._exercise_url())
        self.assertRedirects(
            response,
            reverse("curriculum:lesson_page", kwargs={"slug": self.lesson.slug}),
        )

        self.client.post(self._start_url())
        first_attempt = self.client.session[EXERCISE_ATTEMPT_SESSION_KEY]
        response = self.client.post(self._start_url())
        second_attempt = self.client.session[EXERCISE_ATTEMPT_SESSION_KEY]

        self.assertRedirects(response, self._exercise_url())
        self.assertEqual(first_attempt["attempt_id"], second_attempt["attempt_id"])
        self.assertEqual(first_attempt["question_ids"], second_attempt["question_ids"])

    def test_exercise_is_post_only_and_future_lesson_is_forbidden(self):
        self.assertEqual(self.client.get(self._start_url()).status_code, 405)
        response = self.client.post(self._start_url(self.lessons[1]))
        self.assertEqual(response.status_code, 403)

    def test_study_time_is_calculated_from_heartbeat_baseline(self):
        self.client.post(self._start_url())
        attempt = self.client.session[EXERCISE_ATTEMPT_SESSION_KEY]
        tracked_session = UserSession.objects.get(pk=attempt["tracked_session_id"])
        tracked_session.active_duration_seconds = (
            attempt["starting_active_duration_seconds"] + 75
        )
        tracked_session.save(update_fields=["active_duration_seconds"])

        request = RequestFactory().get("/")
        request.user = self.student
        request.session = self.client.session

        self.assertEqual(exercise_study_time_seconds(request, self.lesson), 75)
        self.assertEqual(request.session[SESSION_RECORD_KEY], tracked_session.session_id)
