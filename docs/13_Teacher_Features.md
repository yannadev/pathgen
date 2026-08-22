# 13 — Teacher Features

---

## Overview

Teacher is the classroom monitor. View-only access to own class students' progress and all content. Cannot edit anything.

---

## Dashboard

### teacher_dashboard.html

| Element | Purpose |
|---|---|
| Assigned classes summary | Quick overview of own classes |
| Student counts per class | Quick engagement check |
| Link to classrooms | Navigate to class list |

---

## Classroom Monitoring

### teacher_classroom_list.html

- Shows ALL classes assigned to this teacher
- Each class card shows: name, student count
- Click class → classroom_detail.html

### classroom_detail.html (Shared)

- Shows students enrolled in this class
- Each student row: name, status, current lesson
- Click student → student_quick_view modal

**Scope:** Only classes where `classes.teacher_id = teacher.id`

---

## Student Detail

### student_detail.html (Shared)

Shows 10 monitoring metrics:

| # | Metric | What It Shows |
|---|---|---|
| 1 | Student information | Name, ID, class, account status |
| 2 | Current lesson | Lesson student is currently on |
| 3 | Overall progress | e.g., "7 of 10 lessons completed — 70%" |
| 4 | Assessment results | Pretest, exercise, activity, posttest scores |
| 5 | BKT mastery estimates | Per-lesson mastery probability |
| 6 | Q-learning decisions | Advance, Review, or Retake history |
| 7 | Number of attempts | Attempts per exercise/activity |
| 8 | Study time summary | Total time + average per lesson |
| 9 | Hint usage | How often hints were used |
| 10 | Last activity | Most recent activity or login |

**All view-only. Teacher cannot edit any of these.**

---

## Content View

### content_page.html (Shared)

- Browse all lessons, exercises, activities
- Click "Preview" → content_preview modal
- Click "Open Full Page" → full content view

### lesson_page.html (Shared)

- View lesson as student sees it
- Read-only
- Answers/hints visible for review

### activity_page.html (Shared)

- View activity as student sees it
- Read-only
- Answers/hints visible for review

---

## Key Restrictions

| Teacher CANNOT | Reason |
|---|---|
| Edit content | Content is fixed |
| Edit student records | View-only role |
| Edit scores | Protects research data |
| Edit BKT or Q-learning | Protects adaptive integrity |
| View other teachers' classes | Scope: own class only |
| Create or delete accounts | Admin only |
| Create or delete classes | Admin only |
| Grant overrides | Admin only |

---

## Scope Enforcement

### Own Class Only

```python
# Teacher views classroom_detail
classes.objects.filter(
    teacher_id=request.user.id
)
```

### Own Class Students Only

```python
# Teacher views student_detail
class_students.objects.filter(
    class_id__teacher_id=request.user.id
)
```

**Database-level enforcement:** Queries always filter by `teacher_id = current user`.

---

## Permission Matrix (Teacher)

| Action                        | Allowed            |
| ----------------------------- | ------------------ |
| View own classes              | ✅                  |
| View own class students       | ✅                  |
| View student progress         | ✅ (own class only) |
| View content                  | ✅                  |
| View answers/hints in content | ✅                  |
| Edit own profile              | ✅                  |
| Edit content                  | ❌                  |
| Edit student records          | ❌                  |
| View other classes            | ❌                  |
| Create accounts               | ❌                  |
| Override anything             | ❌                  |