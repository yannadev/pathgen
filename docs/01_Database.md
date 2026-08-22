# 01 — Database Design

**PostgreSQL 13+ · 23 tables · UUID PKs · All FKs ON DELETE RESTRICT**

---

## Design Principles

| Principle | Where Applied |
|---|---|
| Soft delete | `users.is_active` + `deleted_at`, `classes.is_active` + `deleted_at` |
| Append-only logs | `audit_log`, `*_q_decisions`, all response tables |
| State vs Event separation | `*_progress` (state) vs `*_sessions`/`*_responses` (events) |
| Frozen snapshots | `is_correct`, `mastery_at_decision`, `session_score` |
| CHECK constraints | Score ranges, answer indexes, probability bounds |
| UNIQUE constraints | Prevent duplicates |
| FK RESTRICT | Research data preserved |
| JSONB flexibility | Lesson content, MCQ options, media metadata |

---

## Group 1: Auth & Organization (5 tables)

### users

| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK, default gen_random_uuid() |
| email | VARCHAR(255) | NOT NULL, UNIQUE |
| password_hash | VARCHAR(255) | NOT NULL |
| first_name | VARCHAR(100) | NOT NULL |
| last_name | VARCHAR(100) | NOT NULL |
| role | user_role ENUM | 'admin', 'teacher', 'student' |
| password_must_change | BOOLEAN | NOT NULL, default FALSE |
| is_active | BOOLEAN | NOT NULL, default TRUE |
| deleted_at | TIMESTAMPTZ | NULL |
| created_at | TIMESTAMPTZ | NOT NULL, default NOW() |
| updated_at | TIMESTAMPTZ | NOT NULL, default NOW() |

**Purpose:** Single table for all roles. Soft delete preserves research data. `password_must_change` enforces temp-password flow.

---

### classes

| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| name | VARCHAR(100) | NOT NULL |
| teacher_id | UUID | FK → users.id, NOT NULL |
| is_active | BOOLEAN | NOT NULL, default TRUE |
| deleted_at | TIMESTAMPTZ | NULL |
| created_at | TIMESTAMPTZ | NOT NULL, default NOW() |

**Purpose:** One teacher can have many classes. Soft delete protects enrollment history.

---

### class_students

| Column | Type | Constraints |
|---|---|---|
| class_id | UUID | FK → classes.id, PK |
| student_id | UUID | FK → users.id, PK |
| enrolled_at | TIMESTAMPTZ | NOT NULL, default NOW() |

**Purpose:** Composite PK prevents duplicate enrollment. Many-to-many join.

---

### user_sessions

| Column | Type | Constraints |
|---|---|---|
| session_id | BIGINT | PK, IDENTITY |
| user_id | UUID | FK → users.id, NOT NULL |
| login_at | TIMESTAMPTZ | NOT NULL |
| last_heartbeat_at | TIMESTAMPTZ | NOT NULL |
| logout_at | TIMESTAMPTZ | NULL (NULL = timeout) |
| active_duration_seconds | INT | NOT NULL, default 0, CHECK ≥ 0 |

**Purpose:** Raw study-time source of truth. Heartbeat pings every 30-60s.

---

### audit_log

| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| admin_id | UUID | FK → users.id, NOT NULL |
| action | VARCHAR(50) | NOT NULL |
| target_type | VARCHAR(50) | NOT NULL |
| target_id | UUID | NOT NULL |
| details_jsonb | JSONB | NULL |
| created_at | TIMESTAMPTZ | NOT NULL, default NOW() |

**Purpose:** Append-only. Every admin action recorded. VARCHAR for extensibility.

---

## Group 2: Content (5 tables)

### lessons

| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| slug | VARCHAR(100) | NOT NULL, UNIQUE |
| title | VARCHAR(255) | NOT NULL |
| description | TEXT | NULL |
| order_index | INT | NOT NULL, UNIQUE |
| prerequisite_lesson_id | UUID | FK → lessons.id, NULL |
| content_jsonb | JSONB | NOT NULL |
| created_at | TIMESTAMPTZ | NOT NULL, default NOW() |

**Purpose:** `slug` enables idempotent seeds. UNIQUE `order_index` enforces fixed sequence. Self-FK enforces prerequisite chain.

---

### assessment_questions

| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| lesson_id | UUID | FK → lessons.id, NOT NULL |
| question_text | TEXT | NOT NULL |
| options_jsonb | JSONB | NOT NULL, CHECK array length = 4 |
| correct_answer_index | INT | NOT NULL, CHECK 0-3 |
| has_image | BOOLEAN | NOT NULL, default FALSE |
| image_url | VARCHAR(500) | NULL |

**Purpose:** Shared bank for pretest and posttest ensures identical questions → valid gain measurement. `lesson_id` enables per-lesson BKT initialization.

---

### exercise_questions

| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| lesson_id | UUID | FK → lessons.id, NOT NULL |
| question_text | TEXT | NOT NULL |
| options_jsonb | JSONB | NOT NULL, CHECK array length = 4 |
| correct_answer_index | INT | NOT NULL, CHECK 0-3 |
| hint_text | TEXT | NOT NULL |

**Purpose:** Text-only MCQ bank per lesson. Separate from assessment questions — these serve practice.

---

### activities

| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| title | VARCHAR(255) | NOT NULL |
| description | TEXT | NULL |
| order_index | INT | NOT NULL, UNIQUE |
| lesson_id_1 | UUID | FK → lessons.id, NOT NULL |
| lesson_id_2 | UUID | FK → lessons.id, NOT NULL |

**Purpose:** CHECK constraint ensures two distinct lessons. Always covers exactly two consecutive lessons.

---

### activity_questions

| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| activity_id | UUID | FK → activities.id, NOT NULL |
| question_text | TEXT | NOT NULL |
| options_jsonb | JSONB | NOT NULL, CHECK array length = 4 |
| correct_answer_index | INT | NOT NULL, CHECK 0-3 |
| media_jsonb | JSONB | NULL |
| order_index | INT | NOT NULL |
| hint_text | TEXT | NOT NULL |

**Purpose:** `media_jsonb` handles text/image/video. `order_index` controls video checkpoint sequencing.

---

## Group 3: Progress (2 tables)

### student_progress

| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| student_id | UUID | FK → users.id, NOT NULL, UNIQUE |
| current_lesson_id | UUID | FK → lessons.id, NULL |
| status | student_status ENUM | 'not_started', 'in_progress', 'completed', 'posttest_taken' |
| last_activity_at | TIMESTAMPTZ | NULL |

**Purpose:** State table, one row per student. UNIQUE ensures one row per student.

---

### lesson_progress

| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| student_id | UUID | FK → users.id, NOT NULL |
| lesson_id | UUID | FK → lessons.id, NOT NULL |
| status | lesson_status ENUM | 'not_started', 'in_progress', 'passed', 'needs_review' |
| first_started_at | TIMESTAMPTZ | NULL |
| last_activity_at | TIMESTAMPTZ | NULL |

**Purpose:** UNIQUE(student_id, lesson_id). Preserves history when Q-learning sends student back.

---

## Group 4: Assessment (3 tables)

### assessment_config

| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| type | assessment_type ENUM | 'pretest', 'posttest', UNIQUE |
| time_limit_seconds | INT | NULL (NULL = no limit) |
| updated_at | TIMESTAMPTZ | NOT NULL, default NOW() |

**Purpose:** Admin sets time limits once per type. Copied into session row when student starts.

---

### assessment_sessions

| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| student_id | UUID | FK → users.id, NOT NULL |
| type | assessment_type ENUM | 'pretest', 'posttest' |
| score | DECIMAL(5,2) | NOT NULL, CHECK 0-100 |
| total_questions | INT | NOT NULL, CHECK > 0 |
| time_limit_seconds | INT | NOT NULL, CHECK > 0 |
| admin_override | BOOLEAN | NOT NULL, default FALSE |
| started_at | TIMESTAMPTZ | NOT NULL |
| completed_at | TIMESTAMPTZ | NULL, CHECK ≥ started_at |

**Purpose:** No UNIQUE(student_id, type) — allows retakes via admin override. Per-session time limit records extensions.

---

### assessment_responses

| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| assessment_session_id | UUID | FK → assessment_sessions.id, NOT NULL |
| assessment_question_id | UUID | FK → assessment_questions.id, NOT NULL |
| selected_answer_index | INT | NOT NULL, CHECK 0-3 |
| is_correct | BOOLEAN | NOT NULL |

**Purpose:** Feeds BKT initialization (pretest) and gain analysis (posttest). `is_correct` frozen at response time.

---

## Group 5: Practice (4 tables)

### exercise_sessions

| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| student_id | UUID | FK → users.id, NOT NULL |
| lesson_id | UUID | FK → lessons.id, NOT NULL |
| score | DECIMAL(5,2) | NOT NULL, CHECK 0-100 |
| total_questions | INT | NOT NULL |
| study_time_seconds | INT | NOT NULL, CHECK ≥ 0 |
| ai_feedback | TEXT | NULL |
| started_at | TIMESTAMPTZ | NOT NULL |
| completed_at | TIMESTAMPTZ | NOT NULL, CHECK ≥ started_at |

**Purpose:** Written at completion. Q-LEARNING TRIGGER POINT. `ai_feedback` NULL if generation fails.

---

### exercise_responses

| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| exercise_session_id | UUID | FK → exercise_sessions.id, NOT NULL |
| exercise_question_id | UUID | FK → exercise_questions.id, NOT NULL |
| selected_answer_index | INT | NOT NULL, CHECK 0-3 |
| is_correct | BOOLEAN | NOT NULL |
| hint_used | BOOLEAN | NOT NULL, default FALSE |

**Purpose:** Raw data for hint tracking. Feeds BKT update and Q-learning state.

---

### activity_sessions

| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| student_id | UUID | FK → users.id, NOT NULL |
| activity_id | UUID | FK → activities.id, NOT NULL |
| score | DECIMAL(5,2) | NOT NULL, CHECK 0-100 |
| total_questions | INT | NOT NULL |
| study_time_seconds | INT | NOT NULL, CHECK ≥ 0 |
| ai_feedback | TEXT | NULL |
| started_at | TIMESTAMPTZ | NOT NULL |
| completed_at | TIMESTAMPTZ | NOT NULL, CHECK ≥ started_at |

**Purpose:** Second Q-LEARNING TRIGGER POINT. BKT updates both covered lessons.

---

### activity_responses

| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| activity_session_id | UUID | FK → activity_sessions.id, NOT NULL |
| activity_question_id | UUID | FK → activity_questions.id, NOT NULL |
| selected_answer_index | INT | NOT NULL, CHECK 0-3 |
| is_correct | BOOLEAN | NOT NULL |
| video_checkpoint_reached | BOOLEAN | NULL (NULL for non-video questions) |

**Purpose:** Records video checkpoint compliance.

---

## Group 6: Adaptive Engine (4 tables)

### bkt_model_parameters

| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| p_learn | DECIMAL(5,4) | NOT NULL, CHECK 0-1 |
| p_slip | DECIMAL(5,4) | NOT NULL, CHECK 0-1 |
| p_guess | DECIMAL(5,4) | NOT NULL, CHECK 0-1 |
| created_at | TIMESTAMPTZ | NOT NULL, default NOW() |
| updated_at | TIMESTAMPTZ | NOT NULL, default NOW() |

**Purpose:** Global parameters — one row for all students. Content properties, not student properties.

---

### bkt_mastery

| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| student_id | UUID | FK → users.id, NOT NULL |
| lesson_id | UUID | FK → lessons.id, NOT NULL |
| p_known | DECIMAL(5,4) | NOT NULL, CHECK 0-1 |
| updated_at | TIMESTAMPTZ | NOT NULL, default NOW() |

**Purpose:** UNIQUE(student_id, lesson_id) — one mastery value per student per lesson. Primary Q-learning input.

---

### exercise_q_decisions

| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| student_id | UUID | FK → users.id, NOT NULL |
| lesson_id | UUID | FK → lessons.id, NOT NULL |
| exercise_session_id | UUID | FK → exercise_sessions.id, NOT NULL, UNIQUE |
| action | q_action ENUM | 'advance', 'review', 'retake' |
| mastery_at_decision | DECIMAL(5,4) | NOT NULL, CHECK 0-1 |
| study_time_seconds | INT | NOT NULL |
| attempt_count | INT | NOT NULL |
| session_score | DECIMAL(5,2) | NOT NULL |
| hint_count | INT | NOT NULL |
| decided_at | TIMESTAMPTZ | NOT NULL, default NOW() |

**Purpose:** Append-only. Snapshot columns frozen at decision time. UNIQUE on session ensures exactly one decision per session.

---

### activity_q_decisions

Same structure as exercise_q_decisions, but `activity_session_id` FK → activity_sessions.id.

**Purpose:** Activity-triggered twin. Separate table so each row has a real FK to its source.

---

## Relationship Map

users ─┬─< classes (teacher_id)  
├─< class_students (student_id)  
├─< user_sessions  
├─< audit_log (admin_id)  
├─< student_progress  
├─< lesson_progress  
├─< assessment_sessions  
├─< exercise_sessions  
├─< activity_sessions  
├─< bkt_mastery  
├─< exercise_q_decisions  
└─< activity_q_decisions

classes ─┬─< class_students  
└─> users (teacher_id)

lessons ─┬─< lessons (prerequisite_lesson_id, self-FK)  
├─< assessment_questions  
├─< exercise_questions  
├─< activities (lesson_id_1, lesson_id_2)  
├─< student_progress (current_lesson_id)  
├─< lesson_progress  
├─< exercise_sessions  
└─< bkt_mastery

activities ─┬─< activity_questions  
└─< activity_sessions

assessment_sessions ──< assessment_responses  
exercise_sessions ────< exercise_responses  
exercise_sessions ────< exercise_q_decisions  
activity_sessions ────< activity_responses  
activity_sessions ────< activity_q_decisions

assessment_questions ──< assessment_responses  
exercise_questions ────< exercise_responses  
activity_questions ────< activity_responses


---

## Summary

| Group | Tables | Purpose |
|---|---|---|
| Auth & Org | 5 | Accounts, classes, sessions, audit |
| Content | 5 | Immutable curriculum, read-only at runtime |
| Progress | 2 | Where each student is |
| Assessment | 3 | Pretest/posttest delivery + config |
| Practice | 4 | Exercises/activities + responses |
| Adaptive | 4 | BKT + Q-learning + decision log |
| **Total** | **23** | Complete system coverage |
