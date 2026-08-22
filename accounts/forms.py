"""Authentication forms for Pathgen's email-based user model."""

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.core.exceptions import ValidationError


INPUT_CLASSES = (
    "form-control min-h-11 w-full rounded-xl border border-slate-300 bg-white "
    "px-3.5 py-2.5 text-sm text-slate-950 shadow-sm outline-none transition "
    "placeholder:text-slate-400 focus:border-cyan-500 focus:ring-4 "
    "focus:ring-cyan-500/15 dark:border-slate-700 dark:bg-slate-900 "
    "dark:text-slate-50 dark:placeholder:text-slate-500"
)


class LoginForm(AuthenticationForm):
    """Authenticate with email and surface the documented inactive state."""

    error_messages = {
        **AuthenticationForm.error_messages,
        "inactive": "Account is deactivated. Contact admin.",
    }

    def __init__(self, request=None, *args, **kwargs):
        super().__init__(request=request, *args, **kwargs)
        self.fields["username"].label = "Email"
        self.fields["username"].widget = forms.EmailInput(
            attrs={
                "autocomplete": "email",
                "autofocus": True,
                "class": INPUT_CLASSES,
                "placeholder": "you@example.com",
            }
        )
        self.fields["password"].widget.attrs.update(
            {
                "autocomplete": "current-password",
                "class": INPUT_CLASSES,
                "placeholder": "Enter your password",
            }
        )

    def clean(self):
        email = self.data.get("username", "").strip()
        if email:
            user_model = get_user_model()
            if user_model._default_manager.filter(
                email__iexact=email,
                is_active=False,
            ).exists():
                raise ValidationError(
                    self.error_messages["inactive"],
                    code="inactive",
                )
        return super().clean()


class PathgenPasswordChangeForm(PasswordChangeForm):
    """Password change form with shared accessible widget styling."""

    def __init__(self, user, *args, **kwargs):
        super().__init__(user, *args, **kwargs)
        autocomplete = {
            "old_password": "current-password",
            "new_password1": "new-password",
            "new_password2": "new-password",
        }
        for name, field in self.fields.items():
            field.widget.attrs.update(
                {
                    "autocomplete": autocomplete[name],
                    "class": INPUT_CLASSES,
                }
            )


class ProfileForm(forms.ModelForm):
    """Own-profile fields; role, email, and research state stay immutable."""

    class Meta:
        model = get_user_model()
        fields = ("first_name", "last_name", "profile_picture")
        widgets = {
            "first_name": forms.TextInput(attrs={"autocomplete": "given-name"}),
            "last_name": forms.TextInput(attrs={"autocomplete": "family-name"}),
            "profile_picture": forms.ClearableFileInput(
                attrs={"accept": "image/*", "autocomplete": "off"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = INPUT_CLASSES

    def clean_profile_picture(self):
        picture = self.cleaned_data.get("profile_picture")
        if picture and not picture.content_type.startswith("image/"):
            raise forms.ValidationError("Upload an image file.")
        return picture
