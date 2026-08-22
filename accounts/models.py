import uuid

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models
from django.db.models import Q
from django.utils import timezone


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("An email address is required.")

        user = self.model(email=self.normalize_email(email), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("role", User.Role.ADMIN)
        extra_fields.setdefault("is_active", True)

        if extra_fields["role"] != User.Role.ADMIN:
            raise ValueError("A superuser must have the admin role.")

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        TEACHER = "teacher", "Teacher"
        STUDENT = "student", "Student"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    password = models.CharField("password", max_length=255, db_column="password_hash")
    email = models.EmailField(max_length=255, unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    role = models.CharField(max_length=10, choices=Role.choices)
    password_must_change = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class Meta:
        db_table = "users"
        constraints = [
            models.CheckConstraint(
                condition=Q(role__in=["admin", "teacher", "student"]),
                name="users_role_valid",
            ),
            models.CheckConstraint(
                condition=(
                    Q(is_active=True, deleted_at__isnull=True)
                    | Q(is_active=False)
                ),
                name="users_active_not_deleted",
            ),
        ]

    @property
    def is_staff(self):
        return self.role == self.Role.ADMIN and self.is_active

    @property
    def is_superuser(self):
        return self.role == self.Role.ADMIN and self.is_active

    def has_perm(self, perm, obj=None):
        return self.is_superuser

    def has_module_perms(self, app_label):
        return self.is_superuser

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self):
        return self.first_name

    def soft_delete(self):
        self.is_active = False
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_active", "deleted_at", "updated_at"])

    def __str__(self):
        return self.email


class Classroom(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    teacher = models.ForeignKey(
        User,
        on_delete=models.RESTRICT,
        related_name="teaching_classes",
    )
    is_active = models.BooleanField(default=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "classes"
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(is_active=True, deleted_at__isnull=True)
                    | Q(is_active=False)
                ),
                name="classes_active_not_deleted",
            ),
        ]

    def clean(self):
        super().clean()
        if self.teacher_id and self.teacher.role != User.Role.TEACHER:
            from django.core.exceptions import ValidationError

            raise ValidationError({"teacher": "The assigned user must be a teacher."})

    def soft_delete(self):
        self.is_active = False
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_active", "deleted_at"])

    def __str__(self):
        return self.name


class ClassStudent(models.Model):
    pk = models.CompositePrimaryKey("classroom", "student")
    classroom = models.ForeignKey(
        Classroom,
        db_column="class_id",
        on_delete=models.RESTRICT,
        related_name="enrollments",
    )
    student = models.ForeignKey(
        User,
        on_delete=models.RESTRICT,
        related_name="class_enrollments",
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "class_students"

    def clean(self):
        super().clean()
        if self.student_id and self.student.role != User.Role.STUDENT:
            from django.core.exceptions import ValidationError

            raise ValidationError({"student": "The enrolled user must be a student."})

    def __str__(self):
        return f"{self.student} in {self.classroom}"


class UserSession(models.Model):
    session_id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(
        User,
        on_delete=models.RESTRICT,
        related_name="tracked_sessions",
    )
    login_at = models.DateTimeField()
    last_heartbeat_at = models.DateTimeField()
    logout_at = models.DateTimeField(null=True, blank=True)
    active_duration_seconds = models.IntegerField(default=0)

    class Meta:
        db_table = "user_sessions"
        constraints = [
            models.CheckConstraint(
                condition=Q(active_duration_seconds__gte=0),
                name="user_sessions_duration_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(logout_at__isnull=True) | Q(logout_at__gte=models.F("login_at")),
                name="user_sessions_logout_after_login",
            ),
            models.CheckConstraint(
                condition=Q(last_heartbeat_at__gte=models.F("login_at")),
                name="user_sessions_heartbeat_after_login",
            ),
        ]

    def __str__(self):
        return f"{self.user} @ {self.login_at:%Y-%m-%d %H:%M:%S}"


class AuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    admin = models.ForeignKey(
        User,
        on_delete=models.RESTRICT,
        related_name="audit_entries",
    )
    action = models.CharField(max_length=50)
    target_type = models.CharField(max_length=50)
    target_id = models.UUIDField()
    details_jsonb = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "audit_log"

    def clean(self):
        super().clean()
        if self.admin_id and self.admin.role != User.Role.ADMIN:
            from django.core.exceptions import ValidationError

            raise ValidationError({"admin": "Audit entries require an admin user."})

    def __str__(self):
        return f"{self.action}: {self.target_type} {self.target_id}"
