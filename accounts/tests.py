from datetime import timedelta

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import Classroom, ClassStudent, User, UserSession
from core.session_tracking import SESSION_TOUCH_KEY


TEST_STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}


@override_settings(STORAGES=TEST_STORAGES)
class AuthenticationFlowTests(TestCase):
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
        cls.waiting_student = User.objects.create_user(
            email="waiting@pathgen.test",
            password=cls.password,
            first_name="Enzo",
            last_name="Navarro",
            role=User.Role.STUDENT,
        )
        cls.classroom = Classroom.objects.create(
            name="Grade 7 Mabini",
            teacher=cls.teacher,
        )
        ClassStudent.objects.create(
            classroom=cls.classroom,
            student=cls.student,
        )

    def login(self, user):
        return self.client.post(
            reverse("accounts:login"),
            {"username": user.email, "password": self.password},
        )

    def test_login_page_is_the_public_entry_point(self):
        response = self.client.get(reverse("accounts:login"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/login.html")

    def test_login_redirects_each_role_to_its_entry_page(self):
        cases = [
            (self.admin, "monitoring:admin_dashboard"),
            (self.teacher, "monitoring:teacher_dashboard"),
            (self.student, "progress:student_dashboard"),
            (self.waiting_student, "accounts:just_chill"),
        ]

        for user, route_name in cases:
            with self.subTest(role=user.role, email=user.email):
                response = self.login(user)
                self.assertRedirects(
                    response,
                    reverse(route_name),
                    fetch_redirect_response=False,
                )
                self.client.post(reverse("accounts:logout"))

    def test_role_entry_pages_render_their_distinct_shells(self):
        cases = [
            (self.admin, "monitoring:admin_dashboard", "admin_base.html"),
            (self.teacher, "monitoring:teacher_dashboard", "teacher_base.html"),
            (self.student, "progress:student_dashboard", "student_base.html"),
            (self.waiting_student, "accounts:just_chill", "student_base.html"),
        ]

        for user, route_name, base_template in cases:
            with self.subTest(role=user.role, route=route_name):
                self.client.force_login(user)
                response = self.client.get(reverse(route_name))
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, base_template)

    def test_inactive_account_gets_documented_error(self):
        self.waiting_student.is_active = False
        self.waiting_student.deleted_at = timezone.now()
        self.waiting_student.save(
            update_fields=["is_active", "deleted_at", "updated_at"]
        )

        response = self.login(self.waiting_student)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Account is deactivated. Contact admin.")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_forced_password_change_blocks_other_pages_and_clears_flag(self):
        self.admin.password_must_change = True
        self.admin.save(update_fields=["password_must_change", "updated_at"])

        login_response = self.login(self.admin)
        self.assertRedirects(
            login_response,
            reverse("accounts:change_password"),
            fetch_redirect_response=False,
        )

        blocked_response = self.client.get(reverse("monitoring:admin_dashboard"))
        self.assertRedirects(
            blocked_response,
            reverse("accounts:change_password"),
            fetch_redirect_response=False,
        )

        changed_response = self.client.post(
            reverse("accounts:change_password"),
            {
                "old_password": self.password,
                "new_password1": "NewSecurePass569!",
                "new_password2": "NewSecurePass569!",
            },
        )
        self.assertRedirects(
            changed_response,
            reverse("monitoring:admin_dashboard"),
            fetch_redirect_response=False,
        )
        self.admin.refresh_from_db()
        self.assertFalse(self.admin.password_must_change)
        self.assertIn("_auth_user_id", self.client.session)

    def test_role_protected_dashboards_reject_the_wrong_role(self):
        self.client.force_login(self.student)
        self.assertEqual(
            self.client.get(reverse("monitoring:teacher_dashboard")).status_code,
            403,
        )
        self.assertEqual(
            self.client.get(reverse("monitoring:admin_dashboard")).status_code,
            403,
        )
        self.client.force_login(self.teacher)
        self.assertEqual(
            self.client.get(reverse("progress:student_dashboard")).status_code,
            403,
        )

    def test_just_chill_is_student_only_and_rechecks_enrollment(self):
        self.client.force_login(self.teacher)
        self.assertEqual(
            self.client.get(reverse("accounts:just_chill")).status_code,
            403,
        )

        self.client.force_login(self.student)
        response = self.client.get(reverse("accounts:just_chill"))
        self.assertRedirects(
            response,
            reverse("progress:student_dashboard"),
            fetch_redirect_response=False,
        )

    def test_logout_is_post_only_and_closes_the_tracked_session(self):
        self.login(self.teacher)
        tracked_session = UserSession.objects.get(user=self.teacher)

        self.assertEqual(
            self.client.get(reverse("accounts:logout")).status_code,
            405,
        )
        response = self.client.post(reverse("accounts:logout"))

        self.assertRedirects(
            response,
            reverse("accounts:login"),
            fetch_redirect_response=False,
        )
        tracked_session.refresh_from_db()
        self.assertIsNotNone(tracked_session.logout_at)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_heartbeat_increments_active_time_and_caps_stale_tabs(self):
        self.login(self.student)
        tracked_session = UserSession.objects.get(user=self.student)
        old_time = timezone.now() - timedelta(minutes=10)
        tracked_session.login_at = old_time
        tracked_session.last_heartbeat_at = old_time
        tracked_session.active_duration_seconds = 0
        tracked_session.save(
            update_fields=[
                "login_at",
                "last_heartbeat_at",
                "active_duration_seconds",
            ]
        )
        browser_session = self.client.session
        browser_session[SESSION_TOUCH_KEY] = old_time.timestamp()
        browser_session.save()

        response = self.client.post(reverse("accounts:heartbeat"))

        self.assertEqual(response.status_code, 200)
        tracked_session.refresh_from_db()
        self.assertEqual(tracked_session.active_duration_seconds, 120)
        self.assertGreater(tracked_session.last_heartbeat_at, old_time)

    def test_anonymous_heartbeat_redirects_to_login(self):
        response = self.client.post(reverse("accounts:heartbeat"))

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse("accounts:login")))
