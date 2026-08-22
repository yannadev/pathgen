"""Read-only monitoring views for teachers and administrators."""

from collections import defaultdict

from django.db.models import Count, Max, Sum
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET

from accounts.models import ClassStudent, Classroom, UserSession
from adaptive.models import ActivityQDecision, BKTMastery, ExerciseQDecision
from assessment.models import AssessmentSession, AssessmentType
from core.decorators import admin_only, teacher_only
from curriculum.models import Activity, Lesson
from practice.models import ActivitySession, ExerciseResponse, ExerciseSession
from progress.models import LessonProgress, StudentProgress


def _teacher_classrooms(teacher):
    """Return only active classrooms assigned to ``teacher``.

    This helper is intentionally used for every classroom and student lookup so
    object IDs from another teacher cannot expose monitoring data.
    """

    return Classroom.objects.filter(teacher=teacher, is_active=True)


def _student_progress(student):
    try:
        return student.progress
    except StudentProgress.DoesNotExist:
        return None


def _score_summary(student):
    completed_assessments = AssessmentSession.objects.filter(
        student=student,
        completed_at__isnull=False,
    )
    return {
        "pretest": completed_assessments.filter(type=AssessmentType.PRETEST)
        .order_by("-completed_at")
        .first(),
        "posttest": completed_assessments.filter(type=AssessmentType.POSTTEST)
        .order_by("-completed_at")
        .first(),
        "exercise": ExerciseSession.objects.filter(student=student)
        .order_by("-completed_at")
        .first(),
        "activity": ActivitySession.objects.filter(student=student)
        .order_by("-completed_at")
        .first(),
    }


def _decision_history(student):
    """Combine the two immutable decision tables for a chronological display."""

    decisions = []
    for decision in ExerciseQDecision.objects.filter(student=student).select_related(
        "lesson", "exercise_session"
    ):
        decisions.append({"decision": decision, "source": "Exercise"})
    for decision in ActivityQDecision.objects.filter(student=student).select_related(
        "lesson", "activity_session", "activity_session__activity"
    ):
        decisions.append({"decision": decision, "source": "Activity"})
    return sorted(decisions, key=lambda item: item["decision"].decided_at, reverse=True)


def _activity_media(question):
    """Normalize optional activity media for the read-only teacher preview."""

    media = question.media_jsonb
    if not isinstance(media, dict):
        return None
    media_type = media.get("type") or media.get("media_type")
    url = media.get("url") or media.get("src")
    if media_type == "image" or media.get("image_url"):
        return {
            "type": "image",
            "url": media.get("image_url") or url,
            "alt": media.get("alt") or "Activity illustration",
        }
    if media_type == "video" or media.get("video_url"):
        return {
            "type": "video",
            "url": media.get("video_url") or url,
            "caption": media.get("caption") or "Activity video",
        }
    return None


@require_GET
@teacher_only
def teacher_dashboard(request):
    classrooms = list(
        _teacher_classrooms(request.user)
        .annotate(student_count=Count("enrollments__student_id", distinct=True))
        .order_by("name")
    )
    return render(
        request,
        "monitoring/teacher/teacher_dashboard.html",
        {
            "classrooms": classrooms,
            "classroom_count": len(classrooms),
            "student_count": sum(classroom.student_count for classroom in classrooms),
        },
    )


@require_GET
@teacher_only
def teacher_classroom_list(request):
    classrooms = (
        _teacher_classrooms(request.user)
        .annotate(student_count=Count("enrollments__student_id", distinct=True))
        .order_by("name")
    )
    return render(
        request,
        "monitoring/teacher/teacher_classroom_list.html",
        {"classrooms": classrooms},
    )


@require_GET
@teacher_only
def classroom_detail(request, classroom_id):
    classroom = get_object_or_404(
        _teacher_classrooms(request.user).select_related("teacher"),
        pk=classroom_id,
    )
    enrollments = ClassStudent.objects.filter(classroom=classroom).select_related(
        "student", "student__progress", "student__progress__current_lesson"
    ).order_by("student__last_name", "student__first_name")
    student_rows = []
    for enrollment in enrollments:
        progress = _student_progress(enrollment.student)
        student_rows.append({"student": enrollment.student, "progress": progress})

    return render(
        request,
        "monitoring/shared/classroom_detail.html",
        {"classroom": classroom, "student_rows": student_rows},
    )


@require_GET
@teacher_only
def student_detail(request, student_id):
    enrollment = (
        ClassStudent.objects.filter(
            classroom__teacher=request.user,
            classroom__is_active=True,
            student_id=student_id,
        )
        .select_related("classroom", "student", "student__progress__current_lesson")
        .order_by("classroom__name")
        .first()
    )
    if enrollment is None:
        raise Http404("Student is not enrolled in one of your active classrooms.")

    student = enrollment.student
    progress = _student_progress(student)
    lessons = list(Lesson.objects.order_by("order_index"))
    completed_lessons = LessonProgress.objects.filter(
        student=student,
        status=LessonProgress.Status.PASSED,
    ).count()
    exercise_attempts = ExerciseSession.objects.filter(student=student)
    activity_attempts = ActivitySession.objects.filter(student=student)
    exercise_count = exercise_attempts.count()
    activity_count = activity_attempts.count()
    study_time_seconds = (
        exercise_attempts.aggregate(total=Sum("study_time_seconds"))["total"] or 0
    ) + (activity_attempts.aggregate(total=Sum("study_time_seconds"))["total"] or 0)
    attempt_count = exercise_count + activity_count

    exercise_counts = {
        row["lesson_id"]: row["count"]
        for row in exercise_attempts.values("lesson_id").annotate(count=Count("id"))
    }
    activity_counts = defaultdict(int)
    activity_attempt_counts = activity_attempts.values("activity_id").annotate(
        count=Count("id")
    )
    activities_by_id = Activity.objects.in_bulk(
        row["activity_id"] for row in activity_attempt_counts
    )
    for row in activity_attempt_counts:
        activity = activities_by_id[row["activity_id"]]
        activity_counts[activity.lesson_1_id] += row["count"]
        activity_counts[activity.lesson_2_id] += row["count"]
    attempt_rows = [
        {
            "lesson": lesson,
            "exercise_count": exercise_counts.get(lesson.id, 0),
            "activity_count": activity_counts.get(lesson.id, 0),
        }
        for lesson in lessons
    ]

    activity_dates = [
        exercise_attempts.aggregate(last=Max("completed_at"))["last"],
        activity_attempts.aggregate(last=Max("completed_at"))["last"],
        UserSession.objects.filter(user=student).aggregate(last=Max("last_heartbeat_at"))["last"],
        progress.last_activity_at if progress else None,
    ]
    latest_session_activity = max(
        (value for value in activity_dates if value is not None), default=None
    )
    mastery_estimates = BKTMastery.objects.filter(student=student).select_related(
        "lesson"
    ).order_by("lesson__order_index")
    mastery_rows = [
        {"mastery": mastery, "percentage": float(mastery.p_known) * 100}
        for mastery in mastery_estimates
    ]

    return render(
        request,
        "monitoring/shared/student_detail.html",
        {
            "enrollment": enrollment,
            "student": student,
            "progress": progress,
            "total_lessons": len(lessons),
            "completed_lessons": completed_lessons,
            "completion_percentage": (
                (completed_lessons / len(lessons) * 100) if lessons else 0
            ),
            "scores": _score_summary(student),
            "mastery_rows": mastery_rows,
            "decision_history": _decision_history(student),
            "attempt_rows": attempt_rows,
            "exercise_count": exercise_count,
            "activity_count": activity_count,
            "study_time_seconds": study_time_seconds,
            "average_study_time_seconds": (
                round(study_time_seconds / attempt_count) if attempt_count else 0
            ),
            "hint_count": ExerciseResponse.objects.filter(
                exercise_session__student=student,
                hint_used=True,
            ).count(),
            "last_activity_at": latest_session_activity,
        },
    )


@require_GET
@teacher_only
def content_page(request):
    lessons = Lesson.objects.prefetch_related("exercise_questions").order_by("order_index")
    activities = Activity.objects.select_related("lesson_1", "lesson_2").prefetch_related(
        "questions"
    ).order_by("order_index")
    return render(
        request,
        "monitoring/shared/content_page.html",
        {"lessons": lessons, "activities": activities},
    )


@require_GET
@teacher_only
def lesson_page(request, slug):
    lesson = get_object_or_404(
        Lesson.objects.prefetch_related("exercise_questions"), slug=slug
    )
    question_rows = [
        {
            "question": question,
            "correct_answer": question.options_jsonb[question.correct_answer_index],
        }
        for question in lesson.exercise_questions.all()
    ]
    return render(
        request,
        "monitoring/shared/lesson_page.html",
        {"lesson": lesson, "question_rows": question_rows},
    )


@require_GET
@teacher_only
def activity_page(request, activity_id):
    activity = get_object_or_404(
        Activity.objects.select_related("lesson_1", "lesson_2").prefetch_related("questions"),
        pk=activity_id,
    )
    question_rows = [
        {
            "question": question,
            "correct_answer": question.options_jsonb[question.correct_answer_index],
            "media": _activity_media(question),
        }
        for question in activity.questions.all().order_by("order_index")
    ]
    return render(
        request,
        "monitoring/shared/activity_page.html",
        {"activity": activity, "question_rows": question_rows},
    )


@admin_only
def admin_dashboard(request):
    return render(request, "monitoring/admin/admin_dashboard.html")
