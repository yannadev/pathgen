"""Login, logout, password, and account-entry views."""

from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST, require_http_methods

from accounts.forms import LoginForm, PathgenPasswordChangeForm, ProfileForm
from accounts.utils import role_home_url, student_has_active_class
from core.decorators import admin_only, student_only, teacher_only
from core.session_tracking import end_tracked_session, start_tracked_session


@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        if request.user.password_must_change:
            return redirect("accounts:change_password")
        return redirect(role_home_url(request.user))

    form = LoginForm(request=request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        auth_login(request, user)
        start_tracked_session(request)
        if user.password_must_change:
            return redirect("accounts:change_password")
        return redirect(role_home_url(user))

    return render(request, "accounts/login.html", {"form": form})


@login_required
def home_redirect(request):
    if request.user.password_must_change:
        return redirect("accounts:change_password")
    return redirect(role_home_url(request.user))


@login_required
@require_http_methods(["GET", "POST"])
def change_password(request):
    form = PathgenPasswordChangeForm(
        request.user,
        data=request.POST or None,
    )
    if request.method == "POST" and form.is_valid():
        user = form.save()
        if user.password_must_change:
            user.password_must_change = False
            user.save(update_fields=["password_must_change", "updated_at"])
        update_session_auth_hash(request, user)
        messages.success(request, "Your password has been updated.")
        return redirect(role_home_url(user))

    return render(
        request,
        "accounts/change_password.html",
        {
            "form": form,
            "is_forced": request.user.password_must_change,
        },
    )


def _profile_page(request, *, template_name, page_title):
    profile_form = ProfileForm(request.POST or None, request.FILES or None, instance=request.user)
    password_form = PathgenPasswordChangeForm(request.user, data=request.POST or None)
    form_type = request.POST.get("form_type") if request.method == "POST" else None

    if request.method == "POST" and form_type == "profile" and profile_form.is_valid():
        profile_form.save()
        messages.success(request, "Your profile has been updated.")
        return redirect(request.resolver_match.view_name)

    if request.method == "POST" and form_type == "password" and password_form.is_valid():
        user = password_form.save()
        if user.password_must_change:
            user.password_must_change = False
            user.save(update_fields=["password_must_change", "updated_at"])
        update_session_auth_hash(request, user)
        messages.success(request, "Your password has been updated.")
        return redirect(request.resolver_match.view_name)

    return render(
        request,
        template_name,
        {
            "profile_form": profile_form,
            "password_form": password_form,
            "page_title": page_title,
        },
    )


@require_http_methods(["GET", "POST"])
@student_only
def student_profile(request):
    return _profile_page(
        request,
        template_name="accounts/student_profile.html",
        page_title="Student profile",
    )


@require_http_methods(["GET", "POST"])
@teacher_only
def teacher_profile(request):
    return _profile_page(
        request,
        template_name="accounts/teacher_profile.html",
        page_title="Teacher profile",
    )


@require_http_methods(["GET", "POST"])
@admin_only
def admin_profile(request):
    return _profile_page(
        request,
        template_name="accounts/admin_profile.html",
        page_title="Admin profile",
    )


@student_only
def just_chill(request):
    if student_has_active_class(request.user):
        return redirect("progress:student_dashboard")
    return render(request, "components/just_chill.html")


@login_required
@require_POST
def heartbeat(request):
    return JsonResponse({"ok": True})


@login_required
@require_POST
def logout_view(request):
    end_tracked_session(request)
    auth_logout(request)
    messages.success(request, "You have been logged out.")
    return redirect("accounts:login")
