from datetime import timedelta
from decimal import Decimal
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from adaptive.models import (
    ActivityQDecision,
    BKTMastery,
    BKTModelParameters,
    ExerciseQDecision,
)
from adaptive.orchestrator import (
    process_activity_completion,
    process_exercise_completion,
)
from curriculum.models import Activity, ActivityQuestion, ExerciseQuestion, Lesson
from practice.models import (
    ActivityResponse,
    ActivitySession,
    ExerciseResponse,
    ExerciseSession,
)
from progress.models import LessonProgress, StudentProgress


class SeedBKTParametersCommandTests(TestCase):
    def test_command_creates_expected_parameters_and_is_idempotent(self):
        output = StringIO()

        call_command("seed_bkt_parameters", stdout=output)
        call_command("seed_bkt_parameters", stdout=output)

        self.assertEqual(BKTModelParameters.objects.count(), 1)
        parameters = BKTModelParameters.objects.get()
        self.assertEqual(parameters.p_learn, Decimal("0.2000"))
        self.assertEqual(parameters.p_slip, Decimal("0.1000"))
        self.assertEqual(parameters.p_guess, Decimal("0.2500"))


class ExerciseOrchestratorTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_content", stdout=StringIO())
        cls.student = User.objects.create_user(
            email="orchestrator.student@example.com",
            password="student-pass",
            first_name="Lino",
            last_name="Reyes",
            role=User.Role.STUDENT,
        )
        cls.lessons = list(Lesson.objects.order_by("order_index"))
        cls.questions = list(
            ExerciseQuestion.objects.filter(lesson=cls.lessons[0]).order_by("id")[:2]
        )

    def setUp(self):
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
        now = timezone.now()
        StudentProgress.objects.create(
            student=self.student,
            current_lesson=self.lessons[0],
            status=StudentProgress.Status.IN_PROGRESS,
            last_activity_at=now,
        )
        LessonProgress.objects.create(
            student=self.student,
            lesson=self.lessons[0],
            status=LessonProgress.Status.IN_PROGRESS,
            first_started_at=now,
            last_activity_at=now,
        )

    def _answers(self, *, correct):
        return {
            question.id: (
                question.correct_answer_index
                if correct
                else (question.correct_answer_index + 1) % 4
            )
            for question in self.questions
        }

    def _complete(self, *, correct, study_time=30, started_at=None, hint_ids=()):
        return process_exercise_completion(
            student=self.student,
            lesson=self.lessons[0],
            questions=self.questions,
            answers=self._answers(correct=correct),
            study_time_seconds=study_time,
            started_at=started_at or timezone.now(),
            hint_used_question_ids=hint_ids,
        )

    def test_advance_writes_frozen_decision_and_unlocks_next_lesson(self):
        result = self._complete(correct=True, study_time=45)

        self.assertEqual(result.session.score, Decimal("100.00"))
        self.assertEqual(result.correct_count, 2)
        self.assertEqual(result.session.responses.count(), 2)
        self.assertEqual(result.decision.action, "advance")
        self.assertEqual(result.decision.attempt_count, 1)
        self.assertEqual(result.decision.study_time_seconds, 45)
        self.assertEqual(result.decision.session_score, Decimal("100.00"))
        self.assertEqual(result.decision.hint_count, 0)
        self.assertGreater(result.decision.mastery_at_decision, Decimal("0.7000"))

        lesson_progress = LessonProgress.objects.get(
            student=self.student,
            lesson=self.lessons[0],
        )
        student_progress = StudentProgress.objects.get(student=self.student)
        self.assertEqual(lesson_progress.status, LessonProgress.Status.PASSED)
        self.assertEqual(student_progress.current_lesson, self.lessons[1])

    def test_retake_keeps_current_lesson_available(self):
        result = self._complete(correct=False)

        self.assertEqual(result.decision.action, "retake")
        self.assertEqual(len(result.wrong_question_ids), 2)
        self.assertEqual(
            LessonProgress.objects.get(
                student=self.student,
                lesson=self.lessons[0],
            ).status,
            LessonProgress.Status.IN_PROGRESS,
        )
        self.assertEqual(
            StudentProgress.objects.get(student=self.student).current_lesson,
            self.lessons[0],
        )

    def test_advance_from_activity_terminal_lesson_waits_for_activity(self):
        last_lesson = self.lessons[-1]
        questions = list(
            ExerciseQuestion.objects.filter(lesson=last_lesson).order_by("id")[:2]
        )
        StudentProgress.objects.filter(student=self.student).update(
            current_lesson=last_lesson
        )
        BKTMastery.objects.create(
            student=self.student,
            lesson=last_lesson,
            p_known=Decimal("0.5000"),
        )

        result = process_exercise_completion(
            student=self.student,
            lesson=last_lesson,
            questions=questions,
            answers={
                question.id: question.correct_answer_index for question in questions
            },
            study_time_seconds=30,
            started_at=timezone.now(),
        )

        progress = StudentProgress.objects.get(student=self.student)
        self.assertEqual(result.decision.action, "advance")
        self.assertEqual(progress.current_lesson, last_lesson)
        self.assertEqual(progress.status, StudentProgress.Status.IN_PROGRESS)
        self.assertEqual(
            LessonProgress.objects.get(student=self.student, lesson=last_lesson).status,
            LessonProgress.Status.PASSED,
        )

    def test_third_attempt_reviews_and_snapshots_cumulative_metrics(self):
        for index, study_time in enumerate((10, 20), start=1):
            started_at = timezone.now() - timedelta(minutes=10 - index)
            prior_session = ExerciseSession.objects.create(
                student=self.student,
                lesson=self.lessons[0],
                score=Decimal("0.00"),
                total_questions=1,
                study_time_seconds=study_time,
                started_at=started_at,
                completed_at=started_at,
            )
            ExerciseResponse.objects.create(
                exercise_session=prior_session,
                exercise_question=self.questions[index - 1],
                selected_answer_index=(
                    self.questions[index - 1].correct_answer_index + 1
                )
                % 4,
                is_correct=False,
                hint_used=True,
            )

        result = self._complete(
            correct=False,
            study_time=30,
            hint_ids=(self.questions[0].id,),
        )

        self.assertEqual(result.decision.action, "review")
        self.assertEqual(result.decision.attempt_count, 3)
        self.assertEqual(result.decision.study_time_seconds, 60)
        self.assertEqual(result.decision.hint_count, 3)
        self.assertEqual(
            LessonProgress.objects.get(
                student=self.student,
                lesson=self.lessons[0],
            ).status,
            LessonProgress.Status.NEEDS_REVIEW,
        )

    def test_bkt_failure_uses_prior_and_still_writes_decision(self):
        BKTModelParameters.objects.all().delete()

        with self.assertLogs("adaptive.orchestrator", level="WARNING"):
            result = self._complete(correct=True)

        self.assertEqual(result.decision.mastery_at_decision, Decimal("0.5000"))
        self.assertEqual(result.decision.action, "retake")
        self.assertEqual(
            BKTMastery.objects.get(
                student=self.student,
                lesson=self.lessons[0],
            ).p_known,
            Decimal("0.5000"),
        )

    @patch("adaptive.orchestrator.load_q_table", side_effect=OSError("missing"))
    def test_q_failure_uses_rule_based_fallback(self, _mock_load):
        with self.assertLogs("adaptive.orchestrator", level="WARNING"):
            result = self._complete(correct=True)

        self.assertEqual(result.decision.action, "advance")

    def test_same_started_at_is_idempotent(self):
        started_at = timezone.now()
        first = self._complete(correct=False, started_at=started_at)
        second = self._complete(correct=False, started_at=started_at)

        self.assertTrue(first.completed_now)
        self.assertFalse(second.completed_now)
        self.assertEqual(first.session.id, second.session.id)
        self.assertEqual(ExerciseSession.objects.count(), 1)
        self.assertEqual(ExerciseQDecision.objects.count(), 1)

    def test_invalid_grading_input_writes_nothing(self):
        with self.assertRaisesMessage(ValueError, "Every delivered"):
            process_exercise_completion(
                student=self.student,
                lesson=self.lessons[0],
                questions=self.questions,
                answers={self.questions[0].id: 0},
                study_time_seconds=10,
                started_at=timezone.now(),
            )

        self.assertFalse(ExerciseSession.objects.exists())
        self.assertFalse(ExerciseQDecision.objects.exists())


class ActivityOrchestratorTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_content", stdout=StringIO())
        cls.student = User.objects.create_user(
            email="activity.orchestrator@example.com",
            password="student-pass",
            first_name="Ari",
            last_name="Santos",
            role=User.Role.STUDENT,
        )
        cls.activity = Activity.objects.select_related("lesson_1", "lesson_2").get(
            order_index=2
        )
        cls.questions = list(
            ActivityQuestion.objects.filter(activity=cls.activity).order_by("id")[:2]
        )

    def setUp(self):
        BKTModelParameters.objects.create(
            p_learn=Decimal("0.2000"),
            p_slip=Decimal("0.1000"),
            p_guess=Decimal("0.2500"),
        )
        now = timezone.now()
        StudentProgress.objects.create(
            student=self.student,
            current_lesson=self.activity.lesson_2,
            status=StudentProgress.Status.IN_PROGRESS,
            last_activity_at=now,
        )
        for lesson in (self.activity.lesson_1, self.activity.lesson_2):
            BKTMastery.objects.create(
                student=self.student,
                lesson=lesson,
                p_known=Decimal("0.5000"),
            )
            LessonProgress.objects.create(
                student=self.student,
                lesson=lesson,
                status=LessonProgress.Status.PASSED,
                first_started_at=now,
                last_activity_at=now,
            )

    def _complete(self, *, correct, started_at=None):
        return process_activity_completion(
            student=self.student,
            activity=self.activity,
            questions=self.questions,
            answers={
                question.id: (
                    question.correct_answer_index
                    if correct
                    else (question.correct_answer_index + 1) % 4
                )
                for question in self.questions
            },
            study_time_seconds=75,
            started_at=started_at or timezone.now(),
        )

    def test_completion_writes_responses_updates_both_masteries_and_finishes_path(self):
        result = self._complete(correct=True)

        self.assertEqual(result.session.score, Decimal("100.00"))
        self.assertEqual(result.session.responses.count(), 2)
        self.assertEqual(result.decision.action, "advance")
        self.assertEqual(result.decision.lesson, self.activity.lesson_2)
        self.assertEqual(result.decision.attempt_count, 1)
        self.assertEqual(result.decision.study_time_seconds, 75)
        self.assertEqual(ActivityResponse.objects.count(), 2)
        for lesson in (self.activity.lesson_1, self.activity.lesson_2):
            self.assertGreater(
                BKTMastery.objects.get(student=self.student, lesson=lesson).p_known,
                Decimal("0.7000"),
            )

        progress = StudentProgress.objects.get(student=self.student)
        self.assertIsNone(progress.current_lesson)
        self.assertEqual(progress.status, StudentProgress.Status.COMPLETED)

    def test_same_started_at_is_idempotent(self):
        started_at = timezone.now()
        first = self._complete(correct=False, started_at=started_at)
        second = self._complete(correct=False, started_at=started_at)

        self.assertTrue(first.completed_now)
        self.assertFalse(second.completed_now)
        self.assertEqual(first.session.id, second.session.id)
        self.assertEqual(ActivitySession.objects.count(), 1)
        self.assertEqual(ActivityQDecision.objects.count(), 1)
