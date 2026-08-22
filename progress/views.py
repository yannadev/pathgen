"""Student dashboard and fixed learning-path views."""

from django.contrib import messages
from django.shortcuts import redirect, render

from accounts.models import ClassStudent
from assessment.models import AssessmentSession, AssessmentType
from curriculum.models import Activity, Lesson
from progress.models import LessonProgress
from progress.services import (
    completed_pretest,
    has_active_enrollment,
    student_progress,
)
from core.decorators import student_only


@student_only
def student_dashboard(request):
    enrollment = ClassStudent.objects.select_related("classroom", "classroom__teacher").filter(
        student=request.user,
        classroom__is_active=True,
    ).first()
    if enrollment is None:
        return redirect("accounts:just_chill")
    progress = student_progress(request.user)
    pretest_sessions = AssessmentSession.objects.filter(
        student=request.user,
        type=AssessmentType.PRETEST,
    )
    completed_pretest_session = pretest_sessions.filter(
        completed_at__isnull=False
    ).order_by("-completed_at").first()
    if progress is None:
        completed_pretest_session = None
    active_pretest = pretest_sessions.filter(completed_at__isnull=True).first()
    total_lessons = Lesson.objects.count()
    completed_lessons = 0
    if progress is not None:
        completed_lessons = LessonProgress.objects.filter(
            student=request.user,
            status=LessonProgress.Status.PASSED,
        ).count()
    return render(
        request,
        "progress/student_dashboard.html",
        {
            "classroom": enrollment.classroom,
            "completed_pretest": completed_pretest_session,
            "active_pretest": active_pretest,
            "student_progress": progress,
            "total_lessons": total_lessons,
            "completed_lessons": completed_lessons,
        },
    )


@student_only
def lesson_path(request):
    if not has_active_enrollment(request.user):
        return redirect("accounts:just_chill")

    pretest = completed_pretest(request.user)
    progress = student_progress(request.user)
    if pretest is None or progress is None:
        messages.info(request, "Complete the pretest before opening your learning path.")
        return redirect("progress:student_dashboard")

    lessons = list(Lesson.objects.order_by("order_index"))
    lesson_progress_by_id = {
        entry.lesson_id: entry
        for entry in LessonProgress.objects.filter(student=request.user)
    }
    activities_by_second_lesson = {
        activity.lesson_2_id: activity
        for activity in Activity.objects.select_related("lesson_1", "lesson_2")
    }
    path_items = []
    for lesson in lessons:
        entry = lesson_progress_by_id.get(lesson.id)
        if entry and entry.status == LessonProgress.Status.PASSED:
            state = "passed"
        elif progress.current_lesson_id == lesson.id:
            state = "needs_review" if entry and entry.status == LessonProgress.Status.NEEDS_REVIEW else "current"
        else:
            state = "locked"
        activity = activities_by_second_lesson.get(lesson.id)
        activity_state = None
        if activity is not None:
            first_status = lesson_progress_by_id.get(activity.lesson_1_id)
            second_status = lesson_progress_by_id.get(activity.lesson_2_id)
            both_passed = (
                first_status is not None
                and first_status.status == LessonProgress.Status.PASSED
                and second_status is not None
                and second_status.status == LessonProgress.Status.PASSED
            )
            moved_beyond_pair = (
                progress.status
                in (progress.Status.COMPLETED, progress.Status.POSTTEST_TAKEN)
                or (
                    progress.current_lesson is not None
                    and progress.current_lesson.order_index > activity.lesson_2.order_index
                )
            )
            if moved_beyond_pair:
                activity_state = "passed"
            elif (
                both_passed
                and progress.current_lesson_id == activity.lesson_2_id
            ):
                activity_state = "current"
            elif any(
                entry is not None
                and entry.status == LessonProgress.Status.NEEDS_REVIEW
                for entry in (first_status, second_status)
            ):
                activity_state = "needs_review"
            else:
                activity_state = "locked"
        path_items.append(
            {
                "lesson": lesson,
                "state": state,
                "activity": activity,
                "activity_state": activity_state,
            }
        )

    completed_count = sum(item["state"] == "passed" for item in path_items)
    completed_posttest = (
        AssessmentSession.objects.filter(
            student=request.user,
            type=AssessmentType.POSTTEST,
            completed_at__isnull=False,
        )
        .order_by("-completed_at")
        .first()
    )
    active_posttest = (
        AssessmentSession.objects.filter(
            student=request.user,
            type=AssessmentType.POSTTEST,
            completed_at__isnull=True,
        )
        .order_by("started_at")
        .first()
    )
    return render(
        request,
        "progress/lesson_path.html",
        {
            "path_items": path_items,
            "completed_count": completed_count,
            "total_lessons": len(path_items),
            "all_lessons_completed": bool(path_items) and completed_count == len(path_items),
            "completed_posttest": completed_posttest,
            "active_posttest": active_posttest,
        },
    )
