from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.http import HttpResponse
from django.test import RequestFactory, TestCase

from accounts.models import Classroom, User
from core.decorators import role_required, teacher_own_class


class RoleDecoratorTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.teacher = User.objects.create_user(
            email="flora@pathgen.test",
            password="StrongPass984!",
            first_name="Flora",
            last_name="Dela Cruz",
            role=User.Role.TEACHER,
        )
        cls.other_teacher = User.objects.create_user(
            email="ramon@pathgen.test",
            password="StrongPass984!",
            first_name="Ramon",
            last_name="Velasco",
            role=User.Role.TEACHER,
        )
        cls.classroom = Classroom.objects.create(
            name="Grade 7 Jacinto",
            teacher=cls.teacher,
        )
        cls.other_classroom = Classroom.objects.create(
            name="Grade 7 Luna",
            teacher=cls.other_teacher,
        )

    def setUp(self):
        self.factory = RequestFactory()

    def test_role_required_redirects_anonymous_requests(self):
        request = self.factory.get("/protected/")
        request.user = AnonymousUser()
        protected_view = role_required(User.Role.ADMIN)(
            lambda request: HttpResponse("ok")
        )

        response = protected_view(request)

        self.assertEqual(response.status_code, 302)
        self.assertIn("next=/protected/", response.url)

    def test_teacher_own_class_allows_only_the_assigned_teacher(self):
        request = self.factory.get("/classroom/")
        request.user = self.teacher
        protected_view = teacher_own_class(lambda request, pk: HttpResponse("ok"))

        response = protected_view(request, pk=self.classroom.pk)

        self.assertEqual(response.status_code, 200)
        with self.assertRaises(PermissionDenied):
            protected_view(request, pk=self.other_classroom.pk)

    def test_teacher_own_class_requires_a_route_lookup(self):
        request = self.factory.get("/classroom/")
        request.user = self.teacher
        protected_view = teacher_own_class(lambda request: HttpResponse("ok"))

        with self.assertRaises(ImproperlyConfigured):
            protected_view(request)
