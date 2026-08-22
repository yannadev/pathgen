# 04 — Pages

**29 page templates · All server-rendered Django templates**

---

## Auth (Shared)

### login.html

| | |
|---|---|
| **Path** | accounts/templates/accounts/login.html |
| **Who Sees** | Everyone (not logged in) |
| **Purpose** | Entry point — email + password form |
| **Shows** | Pathgen logo, login form |
| **Links To** | Role-specific dashboard after login |

---

### change_password.html

| | |
|---|---|
| **Path** | accounts/templates/accounts/change_password.html |
| **Who Sees** | Any user with password_must_change = TRUE |
| **Purpose** | Forced password change after admin reset |
| **Shows** | New password form |
| **Redirects** | Role-specific dashboard after change |

---

## Student Pages (14)

### student_profile.html

| | |
|---|---|
| **Path** | accounts/templates/accounts/student_profile.html |
| **Who Sees** | Student (own profile) |
| **Purpose** | View/edit own name, password, profile picture |
| **Shows** | Profile form |

---

### just_chill.html

| | |
|---|---|
| **Path** | templates/components/just_chill.html |
| **Who Sees** | Student (not yet assigned to class) |
| **Purpose** | "Please wait for the admin to add this account to your respective class." |
| **Shows** | Wait message, logout button |

---

### student_dashboard.html

| | |
|---|---|
| **Path** | progress/templates/progress/student_dashboard.html |
| **Who Sees** | Student (assigned to class) |
| **Purpose** | Overview of current progress |
| **Shows** | Class name, teacher name, current lesson, overall progress, last activity |
| **Links To** | Lesson path, pretest (if not taken) |

---

### pretest.html

| | |
|---|---|
| **Path** | assessment/templates/assessment/pretest.html |
| **Who Sees** | Student (pretest not yet taken) |
| **Purpose** | Baseline assessment delivery |
| **Shows** | MCQ questions, timer, submit button |
| **Modals** | pretest_start_confirm, pretest_submit_confirm, time_warning |

---

### pretest_result.html

| | |
|---|---|
| **Path** | assessment/templates/assessment/pretest_result.html |
| **Who Sees** | Student (after pretest submit) |
| **Purpose** | Shows baseline score |
| **Shows** | Score, BKT initialization note, "Start Learning" button |
| **Links To** | Lesson path |

---

### lesson_path.html

| | |
|---|---|
| **Path** | progress/templates/progress/lesson_path.html |
| **Who Sees** | Student |
| **Purpose** | Fixed lesson sequence with status per lesson |
| **Shows** | Lesson list with statuses, current position, activities after every 2 lessons |
| **Links To** | Lesson page, exercise, activity, posttest |

---

### lesson_page.html (Student)

| | |
|---|---|
| **Path** | curriculum/templates/curriculum/lesson_page.html |
| **Who Sees** | Student |
| **Purpose** | Read lesson content |
| **Shows** | Content blocks from content_jsonb (headings, text, examples, images) |
| **Links To** | Short exercise |

---

### short_exercise.html

| | |
|---|---|
| **Path** | practice/templates/practice/short_exercise.html |
| **Who Sees** | Student |
| **Purpose** | Text-only MCQ exercise for current lesson |
| **Shows** | MCQ questions, submit button |
| **Modals** | exercise_start_confirm, exercise_submit_confirm, hint_modal (on retake) |

---

### short_exercise_result.html

| | |
|---|---|
| **Path** | practice/templates/practice/short_exercise_result.html |
| **Who Sees** | Student (after exercise submit) |
| **Purpose** | Shows score + AI feedback + next action |
| **Shows** | Score, AI feedback text, next step (advance/review/retake) |
| **Links To** | Lesson path, next lesson, retry exercise |

---

### activity.html

| | |
|---|---|
| **Path** | practice/templates/practice/activity.html |
| **Who Sees** | Student |
| **Purpose** | Mixed-media activity covering 2 lessons |
| **Shows** | Text, image, and video questions with checkpoints |
| **Modals** | activity_start_confirm, activity_submit_confirm |

---

### activity_result.html

| | |
|---|---|
| **Path** | practice/templates/practice/activity_result.html |
| **Who Sees** | Student (after activity submit) |
| **Purpose** | Shows score + AI feedback + next action |
| **Shows** | Score, AI feedback, next step |
| **Links To** | Lesson path |

---

### posttest.html

| | |
|---|---|
| **Path** | assessment/templates/assessment/posttest.html |
| **Who Sees** | Student (all lessons completed or admin override) |
| **Purpose** | Final assessment delivery |
| **Shows** | MCQ questions (same bank as pretest), timer, submit |
| **Modals** | posttest_start_confirm, posttest_submit_confirm, time_warning |

---

### posttest_result.html

| | |
|---|---|
| **Path** | assessment/templates/assessment/posttest_result.html |
| **Who Sees** | Student (after posttest submit) |
| **Purpose** | Shows final score |
| **Shows** | Score, "View Completion" button |
| **Links To** | Completion page |

---

### completion.html

| | |
|---|---|
| **Path** | progress/templates/progress/completion.html |
| **Who Sees** | Student (after posttest) |
| **Purpose** | Shows learning gain |
| **Shows** | Pretest score, posttest score, learning gain |
| **Links To** | Dashboard |

---

## Teacher Pages (8)

### teacher_profile.html

| | |
|---|---|
| **Path** | accounts/templates/accounts/teacher_profile.html |
| **Who Sees** | Teacher (own profile) |
| **Purpose** | View/edit own name, password, profile picture |

---

### teacher_dashboard.html

| | |
|---|---|
| **Path** | monitoring/templates/monitoring/teacher/teacher_dashboard.html |
| **Who Sees** | Teacher |
| **Purpose** | Overview of assigned classes |
| **Shows** | Class list summary, student counts |
| **Links To** | Classroom list |

---

### teacher_classroom_list.html

| | |
|---|---|
| **Path** | monitoring/templates/monitoring/teacher/teacher_classroom_list.html |
| **Who Sees** | Teacher |
| **Purpose** | All assigned classes |
| **Shows** | Class cards with names and student counts |
| **Links To** | Classroom detail |

---

### classroom_detail.html (Shared)

| | |
|---|---|
| **Path** | monitoring/templates/monitoring/shared/classroom_detail.html |
| **Who Sees** | Teacher (own class), Admin (any class) |
| **Purpose** | Students in a class |
| **Shows** | Student list with names and status |
| **Links To** | Student detail |
| **Modals** | student_quick_view |

---

### student_detail.html (Shared)

| | |
|---|---|
| **Path** | monitoring/templates/monitoring/shared/student_detail.html |
| **Who Sees** | Teacher (own class), Admin (any student) |
| **Purpose** | 10 monitoring metrics for one student |
| **Shows** | Student info, current lesson, overall progress, assessment results, BKT mastery, Q-learning decisions, attempts, study time, hint usage, last activity |

---

### content_page.html (Shared)

| | |
|---|---|
| **Path** | monitoring/templates/monitoring/shared/content_page.html |
| **Who Sees** | Teacher, Admin |
| **Purpose** | Browse all lessons, exercises, activities |
| **Shows** | Content list with titles and descriptions |
| **Links To** | Lesson page, activity page |
| **Modals** | content_preview |

---

### lesson_page.html (Shared)

| | |
|---|---|
| **Path** | monitoring/templates/monitoring/shared/lesson_page.html |
| **Who Sees** | Teacher, Admin |
| **Purpose** | View lesson as student sees it (read-only) |
| **Shows** | Lesson content with answers/hints visible |

---

### activity_page.html (Shared)

| | |
|---|---|
| **Path** | monitoring/templates/monitoring/shared/activity_page.html |
| **Who Sees** | Teacher, Admin |
| **Purpose** | View activity as student sees it (read-only) |
| **Shows** | Activity questions with answers/hints visible |

---

## Admin Pages (10)

### admin_profile.html

| | |
|---|---|
| **Path** | accounts/templates/accounts/admin_profile.html |
| **Who Sees** | Admin (own profile) |
| **Purpose** | View/edit own name, password, profile picture |

---

### admin_dashboard.html

| | |
|---|---|
| **Path** | monitoring/templates/monitoring/admin/admin_dashboard.html |
| **Who Sees** | Admin |
| **Purpose** | System-wide stats |
| **Shows** | Total students, total teachers, total classes, active students, completion rate, pretest summary, posttest summary, average learning gain, recent activity |

---

### user_management.html

| | |
|---|---|
| **Path** | monitoring/templates/monitoring/admin/user_management.html |
| **Who Sees** | Admin |
| **Purpose** | Create/edit/deactivate accounts, manage classes |
| **Shows** | User list with roles, status, actions |
| **Modals** | create_user, edit_user, deactivate_user_confirm, reset_password_confirm, create_class |

---

### admin_override.html

| | |
|---|---|
| **Path** | monitoring/templates/monitoring/admin/admin_override.html |
| **Who Sees** | Admin |
| **Purpose** | Special actions for specific students |
| **Shows** | Student selector, override options |
| **Modals** | reset_pretest_confirm, force_posttest_confirm, extend_time |

---

### activity_log.html

| | |
|---|---|
| **Path** | monitoring/templates/monitoring/admin/activity_log.html |
| **Who Sees** | Admin |
| **Purpose** | Full audit trail |
| **Shows** | Table of all admin actions |
| **Modals** | audit_detail |

---

### classroom_detail.html (Shared)

| | |
|---|---|
| **Path** | monitoring/templates/monitoring/shared/classroom_detail.html |
| **Who Sees** | Admin (any class) |
| **Purpose** | Manage class — students, teacher |
| **Shows** | Student list with add/remove actions |
| **Modals** | add_student_to_class, remove_student_from_class, edit_class, delete_class_confirm |

---

### student_detail.html (Shared)

| | |
|---|---|
| **Path** | monitoring/templates/monitoring/shared/student_detail.html |
| **Who Sees** | Admin (any student) |
| **Purpose** | 10 monitoring metrics (view-only) |

---

### content_page.html (Shared)

| | |
|---|---|
| **Path** | monitoring/templates/monitoring/shared/content_page.html |
| **Who Sees** | Admin |
| **Purpose** | Browse all content (read-only) |

---

### lesson_page.html (Shared)

| | |
|---|---|
| **Path** | monitoring/templates/monitoring/shared/lesson_page.html |
| **Who Sees** | Admin |
| **Purpose** | View lesson (read-only) |

---

### activity_page.html (Shared)

| | |
|---|---|
| **Path** | monitoring/templates/monitoring/shared/activity_page.html |
| **Who Sees** | Admin |
| **Purpose** | View activity (read-only) |

---

## Summary

| Role                                | Pages  |
| ----------------------------------- | ------ |
| Auth (shared)                       | 2      |
| Student                             | 14     |
| Teacher                             | 8      |
| Admin                               | 10     |
| Shared (counted in teacher + admin) | 5      |
| **Unique templates**                | **29** |