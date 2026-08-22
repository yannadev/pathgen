"""Admin-only forms for controlled account, class, and override actions."""

from django import forms

from accounts.forms import INPUT_CLASSES
from accounts.models import User
from assessment.models import AssessmentSession


class AdminCreateUserForm(forms.Form):
    first_name = forms.CharField(max_length=100)
    last_name = forms.CharField(max_length=100)
    email = forms.EmailField()
    role = forms.ChoiceField(
        choices=[(User.Role.TEACHER, "Teacher"), (User.Role.STUDENT, "Student")]
    )
    temp_password = forms.CharField(min_length=8, widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = INPUT_CLASSES

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email


class AdminEditUserForm(forms.Form):
    first_name = forms.CharField(max_length=100)
    last_name = forms.CharField(max_length=100)
    email = forms.EmailField()
    is_active = forms.BooleanField(required=False)

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        for field in self.fields.values():
            field.widget.attrs["class"] = INPUT_CLASSES

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        users = User.objects.filter(email__iexact=email)
        if self.user is not None:
            users = users.exclude(pk=self.user.pk)
        if users.exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email


class AdminClassForm(forms.Form):
    name = forms.CharField(max_length=100)
    teacher = forms.ModelChoiceField(queryset=User.objects.none())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["teacher"].queryset = User.objects.filter(
            role=User.Role.TEACHER,
            is_active=True,
        ).order_by("last_name", "first_name")
        for field in self.fields.values():
            field.widget.attrs["class"] = INPUT_CLASSES


class AdminEnrollmentForm(forms.Form):
    student = forms.ModelChoiceField(queryset=User.objects.none())

    def __init__(self, *args, classroom=None, **kwargs):
        super().__init__(*args, **kwargs)
        enrolled_ids = classroom.enrollments.values_list("student_id", flat=True) if classroom else []
        self.fields["student"].queryset = User.objects.filter(
            role=User.Role.STUDENT,
            is_active=True,
        ).exclude(pk__in=enrolled_ids).order_by("last_name", "first_name")
        self.fields["student"].widget.attrs["class"] = INPUT_CLASSES


class AdminExtendTimeForm(forms.Form):
    assessment_session = forms.ModelChoiceField(queryset=AssessmentSession.objects.none())
    minutes = forms.IntegerField(min_value=1, max_value=1440)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assessment_session"].queryset = AssessmentSession.objects.filter(
            completed_at__isnull=True
        ).select_related("student").order_by("started_at")
        for field in self.fields.values():
            field.widget.attrs["class"] = INPUT_CLASSES
