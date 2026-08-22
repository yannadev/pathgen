from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Classroom, ClassStudent, User, UserSession
from adaptive.models import (
    BKTMastery,
    BKTModelParameters,
    ExerciseQDecision,
)
from assessment.models import AssessmentSession, AssessmentType
from core.session_tracking import SESSION_RECORD_KEY
from curriculum.models import Activity, ActivityQuestion, ExerciseQuestion, Lesson
from practice.models import ActivitySession, ExerciseSession
from practice.session_state import (
    ACTIVITY_ATTEMPT_SESSION_KEY,
    EXERCISE_ATTEMPT_SESSION_KEY,
    activity_study_time_seconds,
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
        cls.other_student = User.objects.create_user(
            email="other.exercise@example.com",
            password="student-pass",
            first_name="Tala",
            last_name="Cruz",
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
        BKTModelParameters.objects.create(
            p_learn=Decimal("0.2000"),
            p_slip=Decimal("0.1000"),
            p_guess=Decimal("0.2500"),
        )
        BKTMastery.objects.create(
            student=self.student,
            lesson=self.lessons[0],
            p_known=Decimal("0.5000"),
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

    def _submit_url(self, lesson=None):
        return reverse(
            "practice:exercise_submit",
            kwargs={"lesson_slug": (lesson or self.lesson).slug},
        )

    def _answer_data(self, *, correct):
        attempt = self.client.session[EXERCISE_ATTEMPT_SESSION_KEY]
        questions = ExerciseQuestion.objects.in_bulk(attempt["question_ids"])
        return {
            f"question_{question_id}": (
                questions[question_id].correct_answer_index
                if correct
                else (questions[question_id].correct_answer_index + 1) % 4
            )
            for question_id in questions
        }

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

    def test_submit_runs_adaptive_pipeline_and_renders_owned_result(self):
        self.client.post(self._start_url())

        response = self.client.post(self._submit_url(), self._answer_data(correct=True))

        session = ExerciseSession.objects.get(student=self.student)
        self.assertRedirects(
            response,
            reverse("practice:exercise_result", kwargs={"session_id": session.id}),
        )
        self.assertEqual(session.responses.count(), 15)
        self.assertEqual(session.score, Decimal("100.00"))
        self.assertEqual(session.q_decision.action, "advance")
        self.assertNotIn(EXERCISE_ATTEMPT_SESSION_KEY, self.client.session)

        result_response = self.client.get(
            reverse("practice:exercise_result", kwargs={"session_id": session.id})
        )
        self.assertContains(result_response, "100%")
        self.assertContains(result_response, "Continue to next lesson")

        self.client.force_login(self.other_student)
        forbidden_response = self.client.get(
            reverse("practice:exercise_result", kwargs={"session_id": session.id})
        )
        self.assertEqual(forbidden_response.status_code, 404)

    def test_incomplete_submission_returns_form_errors_without_writes(self):
        self.client.post(self._start_url())
        response = self.client.post(self._submit_url(), {})

        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            "Choose one answer before submitting.",
            status_code=400,
        )
        self.assertFalse(ExerciseSession.objects.exists())
        self.assertFalse(ExerciseQDecision.objects.exists())
        self.assertIn(EXERCISE_ATTEMPT_SESSION_KEY, self.client.session)

    def test_retake_reuses_questions_exposes_wrong_hints_and_tracks_usage(self):
        self.client.post(self._start_url())
        first_attempt = self.client.session[EXERCISE_ATTEMPT_SESSION_KEY]
        response = self.client.post(self._submit_url(), self._answer_data(correct=False))
        first_session = ExerciseSession.objects.get(student=self.student)

        self.assertEqual(first_session.q_decision.action, "retake")
        self.assertRedirects(
            response,
            reverse(
                "practice:exercise_result",
                kwargs={"session_id": first_session.id},
            ),
        )
        result_response = self.client.get(
            reverse(
                "practice:exercise_result",
                kwargs={"session_id": first_session.id},
            )
        )
        self.assertContains(result_response, "Retry exercise with hints")

        self.client.post(self._start_url())
        second_attempt = self.client.session[EXERCISE_ATTEMPT_SESSION_KEY]
        self.assertEqual(first_attempt["question_ids"], second_attempt["question_ids"])
        exercise_response = self.client.get(self._exercise_url())
        self.assertContains(exercise_response, "data-hint-trigger", count=15)

        answer_data = self._answer_data(correct=True)
        hinted_question_id = second_attempt["question_ids"][0]
        answer_data[f"hint_used_{hinted_question_id}"] = "1"
        self.client.post(self._submit_url(), answer_data)

        latest_decision = ExerciseQDecision.objects.order_by("-decided_at").first()
        self.assertEqual(latest_decision.attempt_count, 2)
        self.assertEqual(latest_decision.hint_count, 1)
        self.assertEqual(latest_decision.action, "advance")


class ActivityFlowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_content", stdout=StringIO())
        cls.teacher = User.objects.create_user(
            email="teacher.activity@example.com",
            password="teacher-pass",
            first_name="Mara",
            last_name="Santos",
            role=User.Role.TEACHER,
        )
        cls.student = User.objects.create_user(
            email="student.activity@example.com",
            password="student-pass",
            first_name="Lino",
            last_name="Reyes",
            role=User.Role.STUDENT,
        )
        cls.other_student = User.objects.create_user(
            email="other.activity@example.com",
            password="student-pass",
            first_name="Tala",
            last_name="Cruz",
            role=User.Role.STUDENT,
        )
        classroom = Classroom.objects.create(name="Grade 7 Activity", teacher=cls.teacher)
        ClassStudent.objects.create(classroom=classroom, student=cls.student)
        ClassStudent.objects.create(classroom=classroom, student=cls.other_student)
        cls.activity = Activity.objects.select_related("lesson_1", "lesson_2").get(
            order_index=1
        )

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
            current_lesson=self.activity.lesson_2,
            status=StudentProgress.Status.IN_PROGRESS,
            last_activity_at=now,
        )
        BKTModelParameters.objects.create(
            p_learn=Decimal("0.2000"),
            p_slip=Decimal("0.1000"),
            p_guess=Decimal("0.2500"),
        )
        for lesson in (self.activity.lesson_1, self.activity.lesson_2):
            LessonProgress.objects.create(
                student=self.student,
                lesson=lesson,
                status=LessonProgress.Status.PASSED,
                first_started_at=now,
                last_activity_at=now,
            )
            BKTMastery.objects.create(
                student=self.student,
                lesson=lesson,
                p_known=Decimal("0.5000"),
            )

    def _start_url(self):
        return reverse("practice:activity_start", kwargs={"activity_id": self.activity.id})

    def _activity_url(self):
        return reverse("practice:activity", kwargs={"activity_id": self.activity.id})

    def _submit_url(self):
        return reverse("practice:activity_submit", kwargs={"activity_id": self.activity.id})

    def _answer_data(self, *, correct):
        attempt = self.client.session[ACTIVITY_ATTEMPT_SESSION_KEY]
        questions = ActivityQuestion.objects.in_bulk(attempt["question_ids"])
        return {
            f"activity_question_{question_id}": (
                questions[question_id].correct_answer_index
                if correct
                else (questions[question_id].correct_answer_index + 1) % 4
            )
            for question_id in questions
        }

    def test_start_delivers_all_thirty_questions_and_submission_runs_pipeline(self):
        response = self.client.post(self._start_url())

        self.assertRedirects(response, self._activity_url())
        attempt = self.client.session[ACTIVITY_ATTEMPT_SESSION_KEY]
        self.assertEqual(len(attempt["question_ids"]), 30)
        delivery = self.client.get(self._activity_url())
        self.assertEqual(delivery.status_code, 200)
        self.assertEqual(len(delivery.context["question_items"]), 30)
        self.assertNotContains(delivery, "correct_answer_index")

        response = self.client.post(self._submit_url(), self._answer_data(correct=True))
        session = ActivitySession.objects.get(student=self.student)
        self.assertRedirects(
            response,
            reverse("practice:activity_result", kwargs={"session_id": session.id}),
        )
        self.assertEqual(session.responses.count(), 30)
        self.assertEqual(session.q_decision.action, "advance")
        self.assertNotIn(ACTIVITY_ATTEMPT_SESSION_KEY, self.client.session)

        result = self.client.get(
            reverse("practice:activity_result", kwargs={"session_id": session.id})
        )
        self.assertContains(result, "100%")
        self.assertContains(result, "Continue to next lesson")
        self.client.force_login(self.other_student)
        self.assertEqual(
            self.client.get(
                reverse("practice:activity_result", kwargs={"session_id": session.id})
            ).status_code,
            404,
        )

    def test_video_checkpoint_is_required_before_submission(self):
        question = ActivityQuestion.objects.filter(activity=self.activity).order_by(
            "order_index"
        ).first()
        question.media_jsonb = {
            "type": "video",
            "url": "https://example.test/checkpoint.mp4",
            "checkpoint_seconds": 12,
        }
        question.save(update_fields=["media_jsonb"])
        self.client.post(self._start_url())

        response = self.client.post(self._submit_url(), self._answer_data(correct=True))

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Reach each video checkpoint", status_code=400)
        self.assertFalse(ActivitySession.objects.exists())

        response = self.client.post(
            self._submit_url(),
            {
                **self._answer_data(correct=True),
                f"video_checkpoint_{question.id}": "1",
            },
        )
        self.assertEqual(response.status_code, 302)
        response_row = ActivitySession.objects.get(student=self.student).responses.get(
            activity_question=question
        )
        self.assertTrue(response_row.video_checkpoint_reached)

    def test_activity_requires_the_pair_and_study_time_uses_heartbeat_baseline(self):
        LessonProgress.objects.filter(
            student=self.student,
            lesson=self.activity.lesson_1,
        ).update(status=LessonProgress.Status.IN_PROGRESS)
        self.assertEqual(self.client.post(self._start_url()).status_code, 403)

        LessonProgress.objects.filter(
            student=self.student,
            lesson=self.activity.lesson_1,
        ).update(status=LessonProgress.Status.PASSED)
        self.client.post(self._start_url())
        attempt = self.client.session[ACTIVITY_ATTEMPT_SESSION_KEY]
        tracked_session = UserSession.objects.get(pk=attempt["tracked_session_id"])
        tracked_session.active_duration_seconds = (
            attempt["starting_active_duration_seconds"] + 90
        )
        tracked_session.save(update_fields=["active_duration_seconds"])

        request = RequestFactory().get("/")
        request.user = self.student
        request.session = self.client.session
        self.assertEqual(activity_study_time_seconds(request, self.activity), 90)
