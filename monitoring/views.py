"""Role-protected monitoring entry views."""

from django.shortcuts import render

from core.decorators import admin_only, teacher_only


@teacher_only
def teacher_dashboard(request):
    return render(request, "monitoring/teacher/teacher_dashboard.html")


@admin_only
def admin_dashboard(request):
    return render(request, "monitoring/admin/admin_dashboard.html")
