# 05 — Modals

**26 modal templates · All in templates/components/modals/**

---

## What Is a Modal

A popup overlay that appears on top of the current page. Asks for confirmation or input, then closes and returns to the same page.

---

## Shared Modals (1)

### logout_confirm.html

| | |
|---|---|
| **Target** | All roles |
| **Trigger** | Clicking "Logout" in sidebar profile dropdown |
| **Purpose** | "Are you sure you want to logout?" |
| **Content** | Confirm button, Cancel button |

---

## Student Modals (10)

### pretest_start_confirm.html

| | |
|---|---|
| **Target** | Student |
| **Trigger** | Clicking "Start Pretest" |
| **Purpose** | "You are about to start the pretest. The timer will begin immediately. You cannot pause." |
| **Content** | Instructions, Confirm, Cancel |

---

### pretest_submit_confirm.html

| | |
|---|---|
| **Target** | Student |
| **Trigger** | Clicking "Submit" on pretest |
| **Purpose** | "Submit pretest? You cannot change answers after submitting." |
| **Content** | Confirm, Cancel |

---

### exercise_start_confirm.html

| | |
|---|---|
| **Target** | Student |
| **Trigger** | Clicking "Start Exercise" for a lesson |
| **Purpose** | "Start short exercise for Lesson X?" |
| **Content** | Exercise info, Confirm, Cancel |

---

### exercise_submit_confirm.html

| | |
|---|---|
| **Target** | Student |
| **Trigger** | Clicking "Submit" on short exercise |
| **Purpose** | "Submit exercise? You cannot change answers after." |
| **Content** | Confirm, Cancel |

---

### activity_start_confirm.html

| | |
|---|---|
| **Target** | Student |
| **Trigger** | Clicking "Start Activity" |
| **Purpose** | "Start activity for Lessons X & Y? Includes video questions." |
| **Content** | Activity info, Confirm, Cancel |

---

### activity_submit_confirm.html

| | |
|---|---|
| **Target** | Student |
| **Trigger** | Clicking "Submit" on activity |
| **Purpose** | "Submit activity? You cannot change answers after." |
| **Content** | Confirm, Cancel |

---

### posttest_start_confirm.html

| | |
|---|---|
| **Target** | Student |
| **Trigger** | Clicking "Start Posttest" |
| **Purpose** | "You are about to start the posttest. The timer will begin immediately." |
| **Content** | Instructions, Confirm, Cancel |

---

### posttest_submit_confirm.html

| | |
|---|---|
| **Target** | Student |
| **Trigger** | Clicking "Submit" on posttest |
| **Purpose** | "Submit posttest? You cannot change answers after." |
| **Content** | Confirm, Cancel |

---

### hint_modal.html

| | |
|---|---|
| **Target** | Student |
| **Trigger** | Clicking "Show Hint" on a question during retake |
| **Purpose** | Shows hint text for that specific question |
| **Content** | Hint text, Close button |
| **Note** | Only appears for questions previously answered wrong |

---

### time_warning.html

| | |
|---|---|
| **Target** | Student |
| **Trigger** | Timer hits 5 minutes remaining (or 1 minute) |
| **Purpose** | "5 minutes remaining!" visual warning |
| **Content** | Time remaining, Continue button |

---

## Teacher + Admin Modals (2)

### student_quick_view.html

| | |
|---|---|
| **Target** | Teacher, Admin |
| **Trigger** | Clicking a student's name in classroom detail |
| **Purpose** | Quick popup with key metrics without leaving page |
| **Content** | Student info, current lesson, overall progress, last activity, "View Full Detail" link |

---

### content_preview.html

| | |
|---|---|
| **Target** | Teacher, Admin |
| **Trigger** | Clicking "Preview" on a lesson/activity in content list |
| **Purpose** | Quick popup showing metadata before opening full page |
| **Content** | Title, description, order, "Open Full Page" link |

---

## Admin Modals (13)

### create_user.html

| | |
|---|---|
| **Target** | Admin |
| **Trigger** | Clicking "Create User" on User Management |
| **Purpose** | Form to create teacher or student account |
| **Content** | Name, email, role, temp password, Submit, Cancel |

---

### edit_user.html

| | |
|---|---|
| **Target** | Admin |
| **Trigger** | Clicking "Edit" on a user row |
| **Purpose** | Form to edit user details |
| **Content** | Name, email, active status, Save, Cancel |

---

### deactivate_user_confirm.html

| | |
|---|---|
| **Target** | Admin |
| **Trigger** | Clicking "Deactivate" on a user row |
| **Purpose** | "Deactivate this account? User will lose access. Research data is preserved." |
| **Content** | Warning, Confirm, Cancel |

---

### reset_password_confirm.html

| | |
|---|---|
| **Target** | Admin |
| **Trigger** | Clicking "Reset Password" on a user row |
| **Purpose** | "Reset password to temporary default? User will be forced to change it on next login." |
| **Content** | Confirm, Cancel |

---

### create_class.html

| | |
|---|---|
| **Target** | Admin |
| **Trigger** | Clicking "Create Class" |
| **Purpose** | Form to create a class and assign teacher |
| **Content** | Class name, teacher dropdown, Submit, Cancel |

---

### edit_class.html

| | |
|---|---|
| **Target** | Admin |
| **Trigger** | Clicking "Edit" on a class |
| **Purpose** | Form to edit class name or reassign teacher |
| **Content** | Class name, teacher dropdown, Save, Cancel |

---

### add_student_to_class.html

| | |
|---|---|
| **Target** | Admin |
| **Trigger** | Clicking "Add Student" in classroom detail |
| **Purpose** | Form to select a student and add to class |
| **Content** | Student dropdown, Submit, Cancel |

---

### remove_student_from_class.html

| | |
|---|---|
| **Target** | Admin |
| **Trigger** | Clicking "Remove" on a student in classroom detail |
| **Purpose** | "Remove this student from the class?" |
| **Content** | Confirm, Cancel |

---

### delete_class_confirm.html

| | |
|---|---|
| **Target** | Admin |
| **Trigger** | Clicking "Delete Class" on classroom detail |
| **Purpose** | "Delete this class? Only possible if no active students are enrolled." |
| **Content** | Warning, Confirm, Cancel |

---

### reset_pretest_confirm.html

| | |
|---|---|
| **Target** | Admin |
| **Trigger** | Clicking "Reset Pretest" on Admin Override page |
| **Purpose** | "Reset pretest for this student? All progress will be wiped. Student will restart." |
| **Content** | Strong warning, Confirm, Cancel |

---

### force_posttest_confirm.html

| | |
|---|---|
| **Target** | Admin |
| **Trigger** | Clicking "Force Posttest" on Admin Override page |
| **Purpose** | "Grant early posttest access to this student? They have not completed all lessons." |
| **Content** | Warning, Confirm, Cancel |

---

### extend_time.html

| | |
|---|---|
| **Target** | Admin |
| **Trigger** | Clicking "Extend Time" on Admin Override page |
| **Purpose** | Form to add extra minutes to an active pretest/posttest session |
| **Content** | Number input (minutes), Submit, Cancel |

---

### audit_detail.html

| | |
|---|---|
| **Target** | Admin |
| **Trigger** | Clicking a row in Activity Log |
| **Purpose** | Shows full details of one audit entry |
| **Content** | Full audit row data, Close button |

---

## Summary

| Role            | Modals |
| --------------- | ------ |
| All roles       | 1      |
| Student         | 10     |
| Teacher + Admin | 2      |
| Admin only      | 13     |
| **Total**       | **26** |