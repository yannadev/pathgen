# 07 — Authentication

---

## Overview

Auth is handled by Django's built-in session authentication. No JWT, no DRF, no tokens. Users log in with email + password, Django maintains the session.

---

## Login Flow

```
User visits /
  → If logged in → redirect to role dashboard
  → If not logged in → login.html
  → Enter email + password
  → Django authenticates
  → Check is_active
    ├── FALSE → "Account is deactivated. Contact admin."
    └── TRUE → Check password_must_change
              ├── TRUE → change_password.html
              └── FALSE → Role-based redirect
```

---

## Role-Based Redirect

| Role | Redirect To |
|---|---|
| admin | admin_dashboard.html |
| teacher | teacher_dashboard.html |
| student | Check class → dashboard or just_chill |

---

## Student Class Check

```
Student logs in
  → Query class_students WHERE student_id = user.id
  → Exists?
    ├── YES → student_dashboard.html
    └── NO → just_chill.html
```

---

## Password Rules

### Admin Creates Account

1. Admin fills create_user modal
2. System generates temp password
3. `password_must_change = TRUE`
4. User logs in with temp password
5. Forced to change password
6. After change: `password_must_change = FALSE`

### Admin Resets Password

1. Admin clicks "Reset Password"
2. Confirm modal
3. Password set to temp default
4. `password_must_change = TRUE`
5. User must change on next login

### Changing After Reset Is Optional

- The system forces the password change page
- User can choose to set same temp password (but UI encourages new one)

---

## Role Permissions

### Decorators

```python
# core/decorators.py

def admin_only(view):
    """Only admin role can access"""
    
def teacher_only(view):
    """Only teacher role can access"""

def student_only(view):
    """Only student role can access"""

def teacher_own_class(view):
    """Teacher can only access own class data"""
```

---

## Permission Matrix

| Action | Admin | Teacher | Student |
|---|---|---|---|
| Create accounts | ✅ | ❌ | ❌ |
| Edit own profile | ✅ | ✅ | ✅ |
| Edit own name/password | ✅ | ✅ | ✅ |
| View own class | — | ✅ | — |
| View all classes | ✅ | ❌ | ❌ |
| View all students | ✅ | ❌ | ❌ |
| View own class students | — | ✅ | — |
| View own progress | — | — | ✅ |
| View content (read-only) | ✅ | ✅ | ❌ |
| View lesson as learner | ❌ | ❌ | ✅ |
| Edit content | ❌ | ❌ | ❌ |
| Override (reset/force/extend) | ✅ | ❌ | ❌ |
| View audit log | ✅ | ❌ | ❌ |
| Deactivate accounts | ✅ | ❌ | ❌ |
| Delete class | ✅ (if empty) | ❌ | ❌ |

---

## Soft Delete

### Users

- Admin deactivates → `is_active = FALSE`
- `deleted_at` set to current time
- User cannot log in
- Data preserved (progress, sessions, responses)
- Admin can still view their records

### Classes

- Admin deletes class → `is_active = FALSE`
- `deleted_at` set to current time
- Only allowed if no active students enrolled
- Historical enrollment preserved in class_students

---

## Audit Logging

Every admin action writes to audit_log:

| Action | Written When |
|---|---|
| create_user | Admin creates account |
| edit_user | Admin edits account |
| deactivate_user | Admin deactivates account |
| reset_password | Admin resets password |
| create_class | Admin creates class |
| edit_class | Admin edits class |
| delete_class | Admin deletes class |
| add_student | Admin adds student to class |
| remove_student | Admin removes student from class |
| reset_pretest | Admin resets pretest |
| force_posttest | Admin forces posttest |
| extend_time | Admin extends test time |

---

## Session Tracking

### Heartbeat Flow

```
User logs in
  → user_sessions row created (login_at, last_heartbeat_at)
  → heartbeat.js pings every 30-60s
  → last_heartbeat_at updated
  → active_duration_seconds incremented
  → User logs out or closes tab
  → logout_at set (or NULL if timeout)
```

---

## Key Rules

1. **No account creation by users** — admin only
2. **No role changes by users** — admin only
3. **Soft delete, never hard delete** — research data preserved
4. **Every admin action logged** — audit trail
5. **Teacher scoped to own class** — cannot view others
6. **Student scoped to own data** — cannot view others
7. **Content read-only** — no user can edit content