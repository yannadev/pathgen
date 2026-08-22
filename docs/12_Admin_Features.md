# 12 — Admin Features

---

## Overview

Admin is the system operator. Full account management, class management, overrides, and monitoring. Cannot edit content or adaptive decisions.

---

## Dashboard

### admin_dashboard.html

| Metric | Purpose |
|---|---|
| Total students | Quick system overview |
| Total teachers | Staff count |
| Total classes | Class count |
| Active students | Engagement tracking |
| Completion rate | Overall progress |
| Pretest summary | Baseline performance |
| Posttest summary | Final performance |
| Average learning gain | Improvement measurement |
| Recent activity | System participation |

---

## Account Management

### Create User

- Admin fills create_user modal
- Fields: first_name, last_name, email, role (teacher/student), temp password
- System creates account with `password_must_change = TRUE`
- Writes audit_log row

### Edit User

- Admin clicks "Edit" on user row
- edit_user modal
- Fields: first_name, last_name, email, is_active
- Writes audit_log row

### Deactivate User

- Admin clicks "Deactivate" on user row
- deactivate_user_confirm modal
- Sets `is_active = FALSE`, `deleted_at = NOW()`
- User cannot log in
- Data preserved
- Writes audit_log row

### Reset Password

- Admin clicks "Reset Password" on user row
- reset_password_confirm modal
- Password set to temp default
- `password_must_change = TRUE`
- Writes audit_log row

### Admin Cannot Create Other Admins

- Role dropdown in create_user only shows: teacher, student
- No admin option

---

## Class Management

### Create Class

- Admin clicks "Create Class"
- create_class modal
- Fields: class name, teacher dropdown
- Writes audit_log row

### Edit Class

- Admin clicks "Edit" on class
- edit_class modal
- Fields: class name, teacher
- Writes audit_log row

### Add Student to Class

- Admin clicks "Add Student" in classroom detail
- add_student_to_class modal
- Student dropdown
- Writes class_students row
- Writes audit_log row

### Remove Student from Class

- Admin clicks "Remove" on student
- remove_student_from_class modal
- Confirm removal
- Deletes class_students row (or soft-deletes)
- Writes audit_log row

### Delete Class

- Admin clicks "Delete Class"
- delete_class_confirm modal
- Guard: only if no active students enrolled
- Sets `is_active = FALSE`, `deleted_at = NOW()`
- Writes audit_log row

---

## Overrides

### Reset Pretest

- Admin goes to admin_override.html
- Selects student
- Clicks "Reset Pretest"
- reset_pretest_confirm modal with strong warning
- Effect:
  - Deletes student_progress row
  - Deletes lesson_progress rows
  - Deletes bkt_mastery rows
  - Student restarts from pretest
- Writes audit_log row

### Force Posttest

- Admin goes to admin_override.html
- Selects student
- Clicks "Force Posttest"
- force_posttest_confirm modal with warning
- Effect:
  - Creates assessment_session with type='posttest'
  - Sets admin_override = TRUE
  - Student can take posttest without completing all lessons
- Writes audit_log row

### Extend Time

- Admin goes to admin_override.html
- Selects active test session
- Clicks "Extend Time"
- extend_time modal
- Input: minutes to add
- Effect:
  - Updates assessment_sessions.time_limit_seconds
  - Timer extends for that session
- Writes audit_log row

---

## Content View

Admin can view all content — read-only:

- content_page.html — browse lessons, exercises, activities
- lesson_page.html — view lesson with answers/hints visible
- activity_page.html — view activity with answers/hints visible

**Cannot edit any content.**

---

## Student Progress Monitoring

Admin can view ALL students' progress. Same 10 metrics as teacher:

1. Student information
2. Current lesson
3. Overall progress
4. Assessment results
5. BKT mastery estimates
6. Q-learning decisions
7. Number of attempts
8. Study time summary
9. Hint usage
10. Last activity

**Cannot edit any of these. View-only.**

---

## Activity Log

### activity_log.html

Shows all admin actions:

| Column | Content |
|---|---|
| Admin | Who performed the action |
| Action | What was done |
| Target | What was affected |
| Details | JSON context |
| Timestamp | When it happened |

### audit_detail modal

Clicking a row shows full details.

---

## Key Restrictions

| Admin CANNOT | Reason |
|---|---|
| Edit content | Content is seeded, fixed |
| Edit BKT estimates | Protects adaptive integrity |
| Edit Q-learning decisions | Protects adaptive integrity |
| Manually change scores | Protects research data reliability |
| Create other admins | Separation of duties |
| Hard delete anything | Research data preserved |

---

## Audit Log Actions Summary

| Action          | Written When               |
| --------------- | -------------------------- |
| create_user     | Account created            |
| edit_user       | Account edited             |
| deactivate_user | Account deactivated        |
| reset_password  | Password reset             |
| create_class    | Class created              |
| edit_class      | Class edited               |
| delete_class    | Class deleted              |
| add_student     | Student added to class     |
| remove_student  | Student removed from class |
| reset_pretest   | Pretest reset              |
| force_posttest  | Early posttest granted     |
| extend_time     | Time extended              |