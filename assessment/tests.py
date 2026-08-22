from datetime import timedelta
from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import Classroom, ClassStudent, User
from adaptive.models import BKTMastery, BKTModelParameters
from assessment.forms import AssessmentSubmissionForm
from assessment.models import (
    AssessmentConfig,
    AssessmentResponse,
    AssessmentSession,
    AssessmentType,
)
from curriculum.models import AssessmentQuestion, Lesson
from progress.models import LessonProgress, StudentProgress


@override_settings(PATHGEN_PRETEST_TIME_LIMIT_SECONDS=3600)
class StudentPretestFlowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_content", stdout=StringIO())
        cls.teacher = User.objects.create_user(
            email="teacher.pretest@example.com",
            password="teacher-pass",
            first_name="Mara",
            last_name="Santos",
            role=User.Role.TEACHER,
        )
        cls.student = User.objects.create_user(
            email="student.pretest@example.com",
            password="student-pass",
            first_name="Lino",
            last_name="Reyes",
            role=User.Role.STUDENT,
        )
        cls.other_student = User.objects.create_user(
            email="other.pretest@example.com",
            password="other-pass",
            first_name="Tala",
            last_name="Cruz",
            role=User.Role.STUDENT,
        )
        cls.unenrolled_student = User.objects.create_user(
            email="waiting.pretest@example.com",
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
        ClassStudent.objects.create(
            classroom=cls.classroom,
            student=cls.other_student,
        )

    def setUp(self):
        BKTModelParameters.objects.create(
            p_learn=Decimal("0.2"),
            p_slip=Decimal("0.1"),
            p_guess=Decimal("0.25"),
        )
        self.client.force_login(self.student)

    def _start_pretest(self):
        response = self.client.post(reverse("assessment:pretest_start"))
        session = AssessmentSession.objects.get(student=self.student)
        return response, session

    @staticmethod
    def _answer_data(*, correct=True):
        data = {}
        for question in AssessmentQuestion.objects.all():
            selected = question.correct_answer_index if correct else (
                question.correct_answer_index + 1
            ) % 4
            data[AssessmentSubmissionForm.field_name(question.id)] = selected
        return data

    def test_dashboard_prompts_student_to_start_pretest(self):
        response = self.client.get(reverse("progress:student_dashboard"))

        self.assertContains(response, "Take your baseline pretest")
        self.assertContains(response, "pretest-start-dialog")
        self.assertContains(response, reverse("assessment:pretest_start"))

    def test_start_is_post_only_and_requires_active_enrollment(self):
        self.assertEqual(
            self.client.get(reverse("assessment:pretest_start")).status_code,
            405,
        )

        self.client.force_login(self.unenrolled_student)
        response = self.client.post(reverse("assessment:pretest_start"))
        self.assertRedirects(response, reverse("accounts:just_chill"))
        self.assertFalse(
            AssessmentSession.objects.filter(student=self.unenrolled_student).exists()
        )

    def test_start_creates_timed_session_from_assessment_config(self):
        AssessmentConfig.objects.create(
            type=AssessmentType.PRETEST,
            time_limit_seconds=2700,
        )

        response, session = self._start_pretest()

        self.assertRedirects(
            response,
            reverse("assessment:pretest", kwargs={"session_id": session.id}),
        )
        self.assertEqual(session.type, AssessmentType.PRETEST)
        self.assertEqual(session.score, Decimal("0"))
        self.assertEqual(session.total_questions, 40)
        self.assertEqual(session.time_limit_seconds, 2700)
        self.assertIsNone(session.completed_at)

    def test_missing_config_uses_default_time_limit(self):
        _, session = self._start_pretest()
        self.assertEqual(session.time_limit_seconds, 3600)

    def test_repeated_start_resumes_one_active_session(self):
        _, session = self._start_pretest()

        response = self.client.post(reverse("assessment:pretest_start"))

        self.assertEqual(AssessmentSession.objects.count(), 1)
        self.assertRedirects(
            response,
            reverse("assessment:pretest", kwargs={"session_id": session.id}),
        )

    def test_pretest_delivers_all_questions_without_answer_keys(self):
        _, session = self._start_pretest()

        response = self.client.get(
            reverse("assessment:pretest", kwargs={"session_id": session.id})
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["question_items"]), 40)
        self.assertContains(response, "data-assessment-timer")
        self.assertContains(response, "js/timer.js")
        self.assertNotContains(response, "correct_answer_index")

    def test_student_cannot_access_another_students_session(self):
        _, session = self._start_pretest()
        self.client.force_login(self.other_student)

        take_url = reverse("assessment:pretest", kwargs={"session_id": session.id})
        submit_url = reverse(
            "assessment:pretest_submit", kwargs={"session_id": session.id}
        )
        result_url = reverse(
            "assessment:pretest_result", kwargs={"session_id": session.id}
        )

        self.assertEqual(self.client.get(take_url).status_code, 404)
        self.assertEqual(self.client.post(submit_url).status_code, 404)
        self.assertEqual(self.client.get(result_url).status_code, 404)

    def test_non_student_cannot_start_pretest(self):
        self.client.force_login(self.teacher)
        response = self.client.post(reverse("assessment:pretest_start"))
        self.assertEqual(response.status_code, 403)

    def test_submit_grades_responses_and_initializes_learning_state(self):
        _, session = self._start_pretest()

        response = self.client.post(
            reverse("assessment:pretest_submit", kwargs={"session_id": session.id}),
            self._answer_data(correct=True),
        )

        session.refresh_from_db()
        self.assertRedirects(
            response,
            reverse("assessment:pretest_result", kwargs={"session_id": session.id}),
        )
        self.assertEqual(session.score, Decimal("100.00"))
        self.assertIsNotNone(session.completed_at)
        self.assertEqual(session.responses.count(), 40)
        self.assertEqual(session.responses.filter(is_correct=True).count(), 40)

        masteries = BKTMastery.objects.filter(student=self.student)
        self.assertEqual(masteries.count(), Lesson.objects.count())
        self.assertTrue(
            all(mastery.p_known == Decimal("0.7500") for mastery in masteries)
        )

        progress = StudentProgress.objects.get(student=self.student)
        self.assertEqual(progress.current_lesson, Lesson.objects.get(order_index=1))
        self.assertEqual(progress.status, StudentProgress.Status.IN_PROGRESS)
        self.assertEqual(progress.last_activity_at, session.completed_at)

    def test_unanswered_questions_count_as_incorrect(self):
        _, session = self._start_pretest()
        question = AssessmentQuestion.objects.order_by(
            "lesson__order_index", "id"
        ).first()

        response = self.client.post(
            reverse("assessment:pretest_submit", kwargs={"session_id": session.id}),
            {
                AssessmentSubmissionForm.field_name(question.id): (
                    question.correct_answer_index
                )
            },
        )

        self.assertEqual(response.status_code, 302)
        session.refresh_from_db()
        self.assertEqual(session.score, Decimal("2.50"))
        self.assertEqual(session.responses.count(), 1)
        self.assertEqual(BKTMastery.objects.filter(student=self.student).count(), 4)

    def test_invalid_answer_does_not_complete_session(self):
        _, session = self._start_pretest()
        question = AssessmentQuestion.objects.first()

        response = self.client.post(
            reverse("assessment:pretest_submit", kwargs={"session_id": session.id}),
            {AssessmentSubmissionForm.field_name(question.id): 9},
        )

        session.refresh_from_db()
        self.assertEqual(response.status_code, 400)
        self.assertIsNone(session.completed_at)
        self.assertFalse(AssessmentResponse.objects.exists())
        self.assertFalse(BKTMastery.objects.exists())
        self.assertFalse(StudentProgress.objects.exists())

    def test_server_rejects_answers_submitted_after_time_limit(self):
        _, session = self._start_pretest()
        AssessmentSession.objects.filter(pk=session.id).update(
            started_at=timezone.now() - timedelta(seconds=session.time_limit_seconds + 11)
        )

        response = self.client.post(
            reverse("assessment:pretest_submit", kwargs={"session_id": session.id}),
            self._answer_data(correct=True),
        )

        self.assertEqual(response.status_code, 302)
        session.refresh_from_db()
        self.assertEqual(session.score, Decimal("0.00"))
        self.assertEqual(session.responses.count(), 0)
        self.assertEqual(BKTMastery.objects.filter(student=self.student).count(), 4)

    def test_missing_bkt_parameters_rolls_back_submission(self):
        _, session = self._start_pretest()
        BKTModelParameters.objects.all().delete()

        response = self.client.post(
            reverse("assessment:pretest_submit", kwargs={"session_id": session.id}),
            self._answer_data(correct=True),
        )

        session.refresh_from_db()
        self.assertEqual(response.status_code, 503)
        self.assertContains(response, "Run seed_bkt_parameters", status_code=503)
        self.assertIsNone(session.completed_at)
        self.assertFalse(AssessmentResponse.objects.exists())
        self.assertFalse(BKTMastery.objects.exists())
        self.assertFalse(StudentProgress.objects.exists())

    def test_repeated_submit_is_idempotent(self):
        _, session = self._start_pretest()
        submit_url = reverse(
            "assessment:pretest_submit", kwargs={"session_id": session.id}
        )
        answers = self._answer_data(correct=True)
        self.client.post(submit_url, answers)

        response = self.client.post(submit_url, answers)

        self.assertRedirects(
            response,
            reverse("assessment:pretest_result", kwargs={"session_id": session.id}),
        )
        self.assertEqual(AssessmentResponse.objects.count(), 40)
        self.assertEqual(BKTMastery.objects.count(), 4)
        self.assertEqual(StudentProgress.objects.count(), 1)

    def test_result_is_available_only_after_completion(self):
        _, session = self._start_pretest()
        result_url = reverse(
            "assessment:pretest_result", kwargs={"session_id": session.id}
        )
        self.assertEqual(self.client.get(result_url).status_code, 404)

        self.client.post(
            reverse("assessment:pretest_submit", kwargs={"session_id": session.id}),
            self._answer_data(correct=True),
        )
        response = self.client.get(result_url)
        self.assertContains(response, "100")
        self.assertContains(response, "Start learning")

    def test_completed_student_cannot_start_second_pretest(self):
        _, session = self._start_pretest()
        self.client.post(
            reverse("assessment:pretest_submit", kwargs={"session_id": session.id}),
            self._answer_data(correct=True),
        )

        response = self.client.post(reverse("assessment:pretest_start"))

        self.assertEqual(AssessmentSession.objects.count(), 1)
        self.assertRedirects(
            response,
            reverse("assessment:pretest_result", kwargs={"session_id": session.id}),
        )


@override_settings(PATHGEN_PRETEST_TIME_LIMIT_SECONDS=3600)
class StudentPosttestFlowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_content", stdout=StringIO())
        cls.teacher = User.objects.create_user(
            email="teacher.posttest@example.com",
            password="teacher-pass",
            first_name="Mara",
            last_name="Santos",
            role=User.Role.TEACHER,
        )
        cls.student = User.objects.create_user(
            email="student.posttest@example.com",
            password="student-pass",
            first_name="Lino",
            last_name="Reyes",
            role=User.Role.STUDENT,
        )
        cls.other_student = User.objects.create_user(
            email="other.posttest@example.com",
            password="other-pass",
            first_name="Tala",
            last_name="Cruz",
            role=User.Role.STUDENT,
        )
        classroom = Classroom.objects.create(
            name="Grade 7 Posttest",
            teacher=cls.teacher,
        )
        ClassStudent.objects.create(classroom=classroom, student=cls.student)
        ClassStudent.objects.create(classroom=classroom, student=cls.other_student)
        cls.lessons = list(Lesson.objects.order_by("order_index"))

    def setUp(self):
        self.client.force_login(self.student)
        now = timezone.now()
        AssessmentSession.objects.create(
            student=self.student,
            type=AssessmentType.PRETEST,
            score=Decimal("40.00"),
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

    def _unlock_posttest(self):
        now = timezone.now()
        for lesson in self.lessons:
            LessonProgress.objects.create(
                student=self.student,
                lesson=lesson,
                status=LessonProgress.Status.PASSED,
                first_started_at=now,
                last_activity_at=now,
            )
        StudentProgress.objects.filter(student=self.student).update(
            current_lesson=None,
            status=StudentProgress.Status.COMPLETED,
        )

    @staticmethod
    def _answer_data(*, correct=True):
        return {
            AssessmentSubmissionForm.field_name(question.id): (
                question.correct_answer_index
                if correct
                else (question.correct_answer_index + 1) % 4
            )
            for question in AssessmentQuestion.objects.all()
        }

    def test_posttest_requires_all_lessons_without_an_override(self):
        response = self.client.post(reverse("assessment:posttest_start"))

        self.assertEqual(response.status_code, 403)
        self.assertFalse(
            AssessmentSession.objects.filter(
                student=self.student,
                type=AssessmentType.POSTTEST,
            ).exists()
        )

    def test_posttest_reuses_bank_grades_responses_and_shows_learning_gain(self):
        self._unlock_posttest()
        mastery = BKTMastery.objects.create(
            student=self.student,
            lesson=self.lessons[0],
            p_known=Decimal("0.5000"),
        )
        AssessmentConfig.objects.create(
            type=AssessmentType.POSTTEST,
            time_limit_seconds=5400,
        )

        response = self.client.post(reverse("assessment:posttest_start"))
        session = AssessmentSession.objects.get(
            student=self.student,
            type=AssessmentType.POSTTEST,
        )
        self.assertRedirects(
            response,
            reverse("assessment:posttest", kwargs={"session_id": session.id}),
        )
        self.assertEqual(session.total_questions, 40)
        self.assertEqual(session.time_limit_seconds, 5400)

        delivery = self.client.get(
            reverse("assessment:posttest", kwargs={"session_id": session.id})
        )
        self.assertContains(delivery, "data-assessment-timer")
        self.assertContains(delivery, "js/timer.js")
        self.assertEqual(len(delivery.context["question_items"]), 40)

        response = self.client.post(
            reverse("assessment:posttest_submit", kwargs={"session_id": session.id}),
            self._answer_data(correct=True),
        )
        self.assertRedirects(
            response,
            reverse("assessment:posttest_result", kwargs={"session_id": session.id}),
        )
        session.refresh_from_db()
        self.assertEqual(session.score, Decimal("100.00"))
        self.assertEqual(session.responses.count(), 40)
        self.assertEqual(
            set(session.responses.values_list("assessment_question_id", flat=True)),
            set(AssessmentQuestion.objects.values_list("id", flat=True)),
        )
        self.assertEqual(
            StudentProgress.objects.get(student=self.student).status,
            StudentProgress.Status.POSTTEST_TAKEN,
        )
        mastery.refresh_from_db()
        self.assertEqual(mastery.p_known, Decimal("0.5000"))

        result = self.client.get(
            reverse("assessment:posttest_result", kwargs={"session_id": session.id})
        )
        self.assertContains(result, "100")
        self.assertContains(result, "View completion")
        completion = self.client.get(reverse("assessment:completion"))
        self.assertContains(completion, "Pretest score")
        self.assertContains(completion, "Posttest score")
        self.assertContains(completion, "+60")

        self.client.force_login(self.other_student)
        self.assertEqual(
            self.client.get(
                reverse("assessment:posttest_result", kwargs={"session_id": session.id})
            ).status_code,
            404,
        )

    def test_completed_posttest_cannot_be_started_again(self):
        self._unlock_posttest()
        self.client.post(reverse("assessment:posttest_start"))
        session = AssessmentSession.objects.get(
            student=self.student,
            type=AssessmentType.POSTTEST,
        )
        self.client.post(
            reverse("assessment:posttest_submit", kwargs={"session_id": session.id}),
            self._answer_data(correct=False),
        )

        response = self.client.post(reverse("assessment:posttest_start"))

        self.assertEqual(
            AssessmentSession.objects.filter(
                student=self.student,
                type=AssessmentType.POSTTEST,
            ).count(),
            1,
        )
        self.assertRedirects(
            response,
            reverse("assessment:posttest_result", kwargs={"session_id": session.id}),
        )

    def test_admin_override_session_bypasses_lesson_completion_gate(self):
        now = timezone.now()
        session = AssessmentSession.objects.create(
            student=self.student,
            type=AssessmentType.POSTTEST,
            score=0,
            total_questions=40,
            time_limit_seconds=3600,
            admin_override=True,
            started_at=now,
        )

        response = self.client.get(
            reverse("assessment:posttest", kwargs={"session_id": session.id})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Posttest")
