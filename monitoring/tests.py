"""Authorization and read-only monitoring coverage for teacher pages."""

from datetime import timedelta

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import ClassStudent, Classroom, User, UserSession
from adaptive.models import ActivityQDecision, BKTMastery, ExerciseQDecision, QAction
from assessment.models import AssessmentSession, AssessmentType
from curriculum.models import Activity, ActivityQuestion, ExerciseQuestion, Lesson
from practice.models import ActivityResponse, ActivitySession, ExerciseResponse, ExerciseSession
from progress.models import LessonProgress, StudentProgress


TEST_STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
    },
}


@override_settings(STORAGES=TEST_STORAGES)
class TeacherMonitoringTests(TestCase):
    password = "TemporaryPass482!"

    @classmethod
    def setUpTestData(cls):
        cls.teacher = User.objects.create_user(
            email="teacher@pathgen.test",
            password=cls.password,
            first_name="Paolo",
            last_name="Santos",
            role=User.Role.TEACHER,
        )
        cls.other_teacher = User.objects.create_user(
            email="other.teacher@pathgen.test",
            password=cls.password,
            first_name="Rina",
            last_name="Cruz",
            role=User.Role.TEACHER,
        )
        cls.student = User.objects.create_user(
            email="student@pathgen.test",
            password=cls.password,
            first_name="Lira",
            last_name="Mendoza",
            role=User.Role.STUDENT,
        )
        cls.other_student = User.objects.create_user(
            email="other.student@pathgen.test",
            password=cls.password,
            first_name="Enzo",
            last_name="Navarro",
            role=User.Role.STUDENT,
        )
        cls.classroom = Classroom.objects.create(
            name="Grade 7 Mabini", teacher=cls.teacher
        )
        cls.other_classroom = Classroom.objects.create(
            name="Grade 7 Bonifacio", teacher=cls.other_teacher
        )
        ClassStudent.objects.create(classroom=cls.classroom, student=cls.student)
        ClassStudent.objects.create(
            classroom=cls.other_classroom, student=cls.other_student
        )

        cls.lesson_one = Lesson.objects.create(
            slug="number-sense",
            title="Number sense",
            order_index=1,
            content_jsonb=[{"type": "paragraph", "text": "Read the number line."}],
        )
        cls.lesson_two = Lesson.objects.create(
            slug="operations",
            title="Operations",
            order_index=2,
            prerequisite_lesson=cls.lesson_one,
            content_jsonb=[{"type": "heading", "text": "Practice operations."}],
        )
        cls.exercise_question = ExerciseQuestion.objects.create(
            lesson=cls.lesson_one,
            question_text="What comes after 4?",
            options_jsonb=["3", "4", "5", "6"],
            correct_answer_index=2,
            hint_text="Count one more than four.",
        )
        cls.activity = Activity.objects.create(
            title="Number operations review",
            description="Connect the first two lessons.",
            order_index=1,
            lesson_1=cls.lesson_one,
            lesson_2=cls.lesson_two,
        )
        cls.activity_question = ActivityQuestion.objects.create(
            activity=cls.activity,
            question_text="Which answer is five?",
            options_jsonb=["2", "3", "4", "5"],
            correct_answer_index=3,
            order_index=1,
            hint_text="Look for the last option.",
        )
        now = timezone.now()
        StudentProgress.objects.create(
            student=cls.student,
            current_lesson=cls.lesson_two,
            status=StudentProgress.Status.IN_PROGRESS,
            last_activity_at=now,
        )
        LessonProgress.objects.create(
            student=cls.student,
            lesson=cls.lesson_one,
            status=LessonProgress.Status.PASSED,
            first_started_at=now - timedelta(minutes=15),
            last_activity_at=now,
        )
        AssessmentSession.objects.create(
            student=cls.student,
            type=AssessmentType.PRETEST,
            score=45,
            total_questions=40,
            time_limit_seconds=1800,
            started_at=now - timedelta(minutes=30),
            completed_at=now - timedelta(minutes=20),
        )
        AssessmentSession.objects.create(
            student=cls.student,
            type=AssessmentType.POSTTEST,
            score=85,
            total_questions=40,
            time_limit_seconds=1800,
            started_at=now - timedelta(minutes=10),
            completed_at=now - timedelta(minutes=5),
        )
        cls.exercise_session = ExerciseSession.objects.create(
            student=cls.student,
            lesson=cls.lesson_one,
            score=80,
            total_questions=1,
            study_time_seconds=120,
            started_at=now - timedelta(minutes=19),
            completed_at=now - timedelta(minutes=17),
        )
        ExerciseResponse.objects.create(
            exercise_session=cls.exercise_session,
            exercise_question=cls.exercise_question,
            selected_answer_index=1,
            is_correct=False,
            hint_used=True,
        )
        cls.activity_session = ActivitySession.objects.create(
            student=cls.student,
            activity=cls.activity,
            score=90,
            total_questions=1,
            study_time_seconds=240,
            started_at=now - timedelta(minutes=16),
            completed_at=now - timedelta(minutes=12),
        )
        ActivityResponse.objects.create(
            activity_session=cls.activity_session,
            activity_question=cls.activity_question,
            selected_answer_index=3,
            is_correct=True,
        )
        BKTMastery.objects.create(
            student=cls.student, lesson=cls.lesson_one, p_known=0.72
        )
        ExerciseQDecision.objects.create(
            student=cls.student,
            lesson=cls.lesson_one,
            exercise_session=cls.exercise_session,
            action=QAction.ADVANCE,
            mastery_at_decision=0.72,
            study_time_seconds=120,
            attempt_count=1,
            session_score=80,
            hint_count=1,
        )
        ActivityQDecision.objects.create(
            student=cls.student,
            lesson=cls.lesson_two,
            activity_session=cls.activity_session,
            action=QAction.REVIEW,
            mastery_at_decision=0.65,
            study_time_seconds=240,
            attempt_count=1,
            session_score=90,
            hint_count=0,
        )
        UserSession.objects.create(
            user=cls.student,
            login_at=now - timedelta(minutes=30),
            last_heartbeat_at=now,
            logout_at=now,
            active_duration_seconds=600,
        )

    def test_dashboard_and_classroom_list_only_show_own_classes(self):
        self.client.force_login(self.teacher)

        dashboard = self.client.get(reverse("monitoring:teacher_dashboard"))
        classroom_list = self.client.get(reverse("monitoring:teacher_classroom_list"))

        for response in (dashboard, classroom_list):
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, self.classroom.name)
            self.assertNotContains(response, self.other_classroom.name)
        self.assertContains(dashboard, "1 student")

    def test_classroom_detail_is_scoped_to_the_signed_in_teacher(self):
        self.client.force_login(self.teacher)

        response = self.client.get(
            reverse("monitoring:classroom_detail", args=[self.classroom.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "monitoring/shared/classroom_detail.html")
        self.assertContains(response, self.student.get_full_name())
        self.assertContains(response, "In progress")
        self.assertContains(response, self.lesson_two.title)
        self.assertEqual(
            self.client.get(
                reverse("monitoring:classroom_detail", args=[self.other_classroom.id])
            ).status_code,
            404,
        )

    def test_student_detail_shows_all_monitoring_metrics_and_is_scoped(self):
        self.client.force_login(self.teacher)

        response = self.client.get(
            reverse("monitoring:student_detail", args=[self.student.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "monitoring/shared/student_detail.html")
        for heading in (
            "Student information",
            "Current lesson",
            "Overall progress",
            "Assessment results",
            "BKT mastery estimates",
            "Q-learning decisions",
            "Number of attempts",
            "Study time summary",
            "Hint usage",
            "Last activity",
        ):
            self.assertContains(response, heading)
        self.assertContains(response, "45%")
        self.assertContains(response, "85%")
        self.assertContains(response, "360 seconds recorded")
        self.assertContains(response, "72%")
        self.assertEqual(
            self.client.get(
                reverse("monitoring:student_detail", args=[self.other_student.id])
            ).status_code,
            404,
        )

    def test_content_views_are_read_only_and_expose_answers_and_hints(self):
        self.client.force_login(self.teacher)

        content = self.client.get(reverse("monitoring:content_page"))
        lesson = self.client.get(
            reverse("monitoring:teacher_lesson_page", args=[self.lesson_one.slug])
        )
        activity = self.client.get(
            reverse("monitoring:teacher_activity_page", args=[self.activity.id])
        )

        self.assertContains(content, self.lesson_one.title)
        self.assertContains(content, self.activity.title)
        self.assertContains(lesson, "Answer:")
        self.assertContains(lesson, self.exercise_question.hint_text)
        self.assertContains(activity, "Answer:")
        self.assertContains(activity, self.activity_question.hint_text)
        self.assertEqual(
            self.client.post(
                reverse("monitoring:teacher_lesson_page", args=[self.lesson_one.slug])
            ).status_code,
            405,
        )

    def test_non_teachers_cannot_open_teacher_monitoring_pages(self):
        self.client.force_login(self.student)

        for url in (
            reverse("monitoring:teacher_dashboard"),
            reverse("monitoring:teacher_classroom_list"),
            reverse("monitoring:classroom_detail", args=[self.classroom.id]),
            reverse("monitoring:student_detail", args=[self.student.id]),
            reverse("monitoring:content_page"),
        ):
            self.assertEqual(self.client.get(url).status_code, 403)
