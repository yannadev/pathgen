"""Authorization and read-only monitoring coverage for teacher pages."""

from datetime import timedelta
from unittest.mock import patch

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


@override_settings(STORAGES=TEST_STORAGES)
class AdminManagementTests(TestCase):
    password = "TemporaryPass482!"

    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(
            email="admin@pathgen.test",
            password=cls.password,
            first_name="Marisol",
            last_name="Reyes",
            role=User.Role.ADMIN,
        )
        cls.teacher = User.objects.create_user(
            email="teacher@pathgen.test",
            password=cls.password,
            first_name="Paolo",
            last_name="Santos",
            role=User.Role.TEACHER,
        )
        cls.student = User.objects.create_user(
            email="student@pathgen.test",
            password=cls.password,
            first_name="Lira",
            last_name="Mendoza",
            role=User.Role.STUDENT,
        )
        cls.second_student = User.objects.create_user(
            email="second.student@pathgen.test",
            password=cls.password,
            first_name="Enzo",
            last_name="Navarro",
            role=User.Role.STUDENT,
        )
        cls.classroom = Classroom.objects.create(
            name="Grade 7 Mabini", teacher=cls.teacher
        )
        ClassStudent.objects.create(classroom=cls.classroom, student=cls.student)
        cls.lesson = Lesson.objects.create(
            slug="admin-test-lesson",
            title="Admin test lesson",
            order_index=1,
            content_jsonb=[],
        )

    def setUp(self):
        self.client.force_login(self.admin)

    def _audit_actions(self):
        from accounts.models import AuditLog

        return list(AuditLog.objects.values_list("action", flat=True))

    def test_dashboard_shows_system_stats_and_non_admins_are_forbidden(self):
        response = self.client.get(reverse("monitoring:admin_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Pathgen administration")
        self.assertContains(response, "Total students")
        self.client.force_login(self.student)
        self.assertEqual(
            self.client.get(reverse("monitoring:admin_dashboard")).status_code,
            403,
        )

    def test_create_edit_deactivate_and_reset_password_are_audited(self):
        create_response = self.client.post(
            reverse("monitoring:admin_create_user"),
            {
                "first_name": "Mika",
                "last_name": "Lopez",
                "email": "mika@pathgen.test",
                "role": User.Role.STUDENT,
                "temp_password": "TemporaryPass482!",
            },
        )
        self.assertRedirects(create_response, reverse("monitoring:user_management"))
        user = User.objects.get(email="mika@pathgen.test")
        self.assertTrue(user.password_must_change)
        self.assertIn("create_user", self._audit_actions())

        edit_response = self.client.post(
            reverse("monitoring:admin_edit_user", args=[user.id]),
            {
                "first_name": "Mika",
                "last_name": "Reyes",
                "email": user.email,
                "is_active": "true",
            },
        )
        self.assertRedirects(edit_response, reverse("monitoring:user_management"))
        user.refresh_from_db()
        self.assertEqual(user.last_name, "Reyes")
        self.assertIn("edit_user", self._audit_actions())

        reset_response = self.client.post(
            reverse("monitoring:admin_reset_password", args=[user.id])
        )
        self.assertRedirects(reset_response, reverse("monitoring:user_management"))
        user.refresh_from_db()
        self.assertTrue(user.password_must_change)
        self.assertFalse(user.check_password("TemporaryPass482!"))
        self.assertIn("reset_password", self._audit_actions())

        deactivate_response = self.client.post(
            reverse("monitoring:admin_deactivate_user", args=[user.id])
        )
        self.assertRedirects(deactivate_response, reverse("monitoring:user_management"))
        user.refresh_from_db()
        self.assertFalse(user.is_active)
        self.assertIsNotNone(user.deleted_at)
        self.assertIn("deactivate_user", self._audit_actions())

    def test_admin_cannot_create_another_admin(self):
        response = self.client.post(
            reverse("monitoring:admin_create_user"),
            {
                "first_name": "Unauthorized",
                "last_name": "Admin",
                "email": "unauthorized.admin@pathgen.test",
                "role": User.Role.ADMIN,
                "temp_password": "TemporaryPass482!",
            },
        )

        self.assertRedirects(response, reverse("monitoring:user_management"))
        self.assertFalse(User.objects.filter(email="unauthorized.admin@pathgen.test").exists())
        self.assertNotIn("create_user", self._audit_actions())

    def test_class_lifecycle_and_enrollment_actions_are_audited(self):
        create_response = self.client.post(
            reverse("monitoring:admin_create_class"),
            {"name": "Grade 7 Rizal", "teacher": self.teacher.id},
        )
        self.assertRedirects(create_response, reverse("monitoring:user_management"))
        classroom = Classroom.objects.get(name="Grade 7 Rizal")
        self.assertIn("create_class", self._audit_actions())

        edit_response = self.client.post(
            reverse("monitoring:admin_edit_class", args=[classroom.id]),
            {"name": "Grade 7 Rizal Updated", "teacher": self.teacher.id},
        )
        self.assertRedirects(
            edit_response,
            reverse("monitoring:admin_classroom_detail", args=[classroom.id]),
        )
        classroom.refresh_from_db()
        self.assertEqual(classroom.name, "Grade 7 Rizal Updated")
        self.assertIn("edit_class", self._audit_actions())

        add_response = self.client.post(
            reverse("monitoring:admin_add_student", args=[classroom.id]),
            {"student": self.second_student.id},
        )
        self.assertRedirects(
            add_response,
            reverse("monitoring:admin_classroom_detail", args=[classroom.id]),
        )
        self.assertTrue(
            ClassStudent.objects.filter(
                classroom=classroom, student=self.second_student
            ).exists()
        )
        self.assertIn("add_student", self._audit_actions())

        blocked_delete = self.client.post(
            reverse("monitoring:admin_delete_class", args=[classroom.id])
        )
        self.assertRedirects(
            blocked_delete,
            reverse("monitoring:admin_classroom_detail", args=[classroom.id]),
        )
        classroom.refresh_from_db()
        self.assertTrue(classroom.is_active)
        self.assertNotIn("delete_class", self._audit_actions())

        remove_response = self.client.post(
            reverse(
                "monitoring:admin_remove_student",
                args=[classroom.id, self.second_student.id],
            )
        )
        self.assertRedirects(
            remove_response,
            reverse("monitoring:admin_classroom_detail", args=[classroom.id]),
        )
        self.assertFalse(
            ClassStudent.objects.filter(
                classroom=classroom, student=self.second_student
            ).exists()
        )
        self.assertIn("remove_student", self._audit_actions())

        delete_response = self.client.post(
            reverse("monitoring:admin_delete_class", args=[classroom.id])
        )
        self.assertRedirects(delete_response, reverse("monitoring:user_management"))
        classroom.refresh_from_db()
        self.assertFalse(classroom.is_active)
        self.assertIsNotNone(classroom.deleted_at)
        self.assertIn("delete_class", self._audit_actions())

    def test_reset_pretest_preserves_history_and_allows_a_fresh_pretest(self):
        now = timezone.now()
        StudentProgress.objects.create(
            student=self.student,
            current_lesson=self.lesson,
            status=StudentProgress.Status.IN_PROGRESS,
            last_activity_at=now,
        )
        LessonProgress.objects.create(
            student=self.student,
            lesson=self.lesson,
            status=LessonProgress.Status.IN_PROGRESS,
        )
        BKTMastery.objects.create(student=self.student, lesson=self.lesson, p_known=0.5)
        historical_session = AssessmentSession.objects.create(
            student=self.student,
            type=AssessmentType.PRETEST,
            score=50,
            total_questions=1,
            time_limit_seconds=600,
            started_at=now - timedelta(minutes=10),
            completed_at=now - timedelta(minutes=5),
        )
        active_session = AssessmentSession.objects.create(
            student=self.student,
            type=AssessmentType.PRETEST,
            score=0,
            total_questions=1,
            time_limit_seconds=600,
            started_at=now - timedelta(minutes=1),
        )

        response = self.client.post(
            reverse("monitoring:admin_reset_pretest"),
            {"student_id": self.student.id},
        )

        self.assertRedirects(response, reverse("monitoring:admin_override"))
        self.assertTrue(AssessmentSession.objects.filter(pk=historical_session.id).exists())
        active_session.refresh_from_db()
        self.assertIsNotNone(active_session.completed_at)
        self.assertFalse(StudentProgress.objects.filter(student=self.student).exists())
        self.assertFalse(LessonProgress.objects.filter(student=self.student).exists())
        self.assertFalse(BKTMastery.objects.filter(student=self.student).exists())
        self.assertIn("reset_pretest", self._audit_actions())

        with patch("assessment.views.pretest_questions", return_value=[object()]), patch(
            "assessment.views.validate_pretest_bank"
        ):
            self.client.force_login(self.student)
            fresh_response = self.client.post(reverse("assessment:pretest_start"))
        self.assertEqual(fresh_response.status_code, 302)
        self.assertEqual(
            AssessmentSession.objects.filter(
                student=self.student,
                type=AssessmentType.PRETEST,
                completed_at__isnull=True,
            ).count(),
            1,
        )

    def test_force_posttest_and_extend_time_write_audit_rows(self):
        with patch("monitoring.admin_services.posttest_questions", return_value=[object()]), patch(
            "monitoring.admin_services.validate_posttest_bank"
        ):
            force_response = self.client.post(
                reverse("monitoring:admin_force_posttest"),
                {"student_id": self.student.id},
            )
        self.assertRedirects(force_response, reverse("monitoring:admin_override"))
        session = AssessmentSession.objects.get(
            student=self.student,
            type=AssessmentType.POSTTEST,
            completed_at__isnull=True,
        )
        self.assertTrue(session.admin_override)
        self.assertIn("force_posttest", self._audit_actions())

        extend_response = self.client.post(
            reverse("monitoring:admin_extend_time"),
            {"assessment_session": session.id, "minutes": 15},
        )
        self.assertRedirects(extend_response, reverse("monitoring:admin_override"))
        session.refresh_from_db()
        self.assertEqual(session.time_limit_seconds, 4500)
        self.assertIn("extend_time", self._audit_actions())

    def test_activity_log_shows_audited_admin_actions(self):
        self.client.post(
            reverse("monitoring:admin_create_class"),
            {"name": "Grade 7 Del Pilar", "teacher": self.teacher.id},
        )

        response = self.client.get(reverse("monitoring:activity_log"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "create_class")
        self.assertContains(response, self.admin.get_full_name())

    def test_non_admins_cannot_open_or_mutate_admin_features(self):
        self.client.force_login(self.teacher)

        for url in (
            reverse("monitoring:user_management"),
            reverse("monitoring:admin_classroom_detail", args=[self.classroom.id]),
            reverse("monitoring:admin_override"),
            reverse("monitoring:activity_log"),
        ):
            self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(
            self.client.post(
                reverse("monitoring:admin_deactivate_user", args=[self.student.id])
            ).status_code,
            403,
        )
