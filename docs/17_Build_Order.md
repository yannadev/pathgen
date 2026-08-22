# 17 — Build Order

---

## Overview

Sequential build phases. Follow in order. Each phase = concrete tasks.

---

## Phase 1: Project Setup

1. Create virtual environment
2. Install requirements.txt
3. Start Django project (config)
4. Configure settings.py (env vars, database, static)
5. Create 9 apps: accounts, curriculum, progress, assessment, practice, adaptive, feedback, monitoring, core

---

## Phase 2: Data Layer

1. Write all 23 models across apps
2. Run makemigrations + migrate
3. Verify tables in database

**Tables by app:**
- accounts: users, classes, class_students, user_sessions, audit_log
- curriculum: lessons, assessment_questions, exercise_questions, activities, activity_questions
- progress: student_progress, lesson_progress
- assessment: assessment_sessions, assessment_responses, assessment_config
- practice: exercise_sessions, exercise_responses, activity_sessions, activity_responses
- adaptive: bkt_model_parameters, bkt_mastery, exercise_q_decisions, activity_q_decisions

---

## Phase 3: Core Infrastructure

1. Role decorators (core/decorators.py)
2. Heartbeat middleware (core/middleware.py)
3. Login/logout views
4. Forced password change flow
5. Role-based redirects
6. Base templates (base, student_base, teacher_base, admin_base)
7. Sidebar components
8. Just Chill page
9. Empty state component

---

## Phase 4: Seed Data

1. Write seed_data JSON files (demo content)
2. seed_content command
3. reset_content command
4. Run seed, verify content loads

---

## Phase 5: Adaptive Engine (Pure Logic)

1. `adaptive/bkt.py` — init_mastery, update_mastery
2. `adaptive/qlearning.py` — Q-table, get_action
3. Seed bkt_model_parameters (p_learn=0.2, p_slip=0.1, p_guess=0.25)
4. Test with pure Python (no Django)

---

## Phase 6: Student Pretest Flow

1. Start pretest (creates session, starts timer)
2. Question delivery
3. Timer JS
4. Submit → grade → responses written
5. BKT initialization per lesson
6. Pretest result page
7. Create student_progress row

---

## Phase 7: Student Learning Path

1. Student dashboard
2. Lesson path (fixed sequence with status)
3. Lesson reading (render content_jsonb)
4. Short exercise flow
5. Study time tracking

---

## Phase 8: Orchestrator

1. `adaptive/orchestrator.py`
2. Wire into practice views
3. Flow: Grade → BKT → Q-learning → Apply action
4. Write q_decisions with frozen snapshots
5. Exercise result page (score + next action)

---

## Phase 9: Activity Flow

1. Activity page (mixed media)
2. Video checkpoint JS
3. Submit → grade → BKT for both lessons → Q-learning
4. Activity result page

---

## Phase 10: RAG Pipeline

1. `feedback/chunker.py` — structure-aware chunking
2. `feedback/clients.py` — OpenAI + Groq clients
3. `build_rag_index.py` command — chunk → embed → JSON
4. Run build_rag_index
5. `feedback/retriever.py` — embed query → cosine → top 4
6. `feedback/generator.py` — prompt → Groq → feedback
7. `feedback/prompts.py` — prompt templates
8. Wire into orchestrator (after Q-learning)
9. Save ai_feedback
10. Show on result pages

---

## Phase 11: Posttest Flow

1. Reuse pretest mechanics
2. Posttest page + timer
3. Submit → grade → responses
4. Posttest result page
5. Completion page (learning gain)

---

## Phase 12: Teacher Features

1. Teacher dashboard
2. Classroom list (own classes only)
3. Classroom detail (students with status)
4. Student detail (10 metrics)
5. Content pages (read-only with answers/hints)

---

## Phase 13: Admin Features

1. Admin dashboard (system stats)
2. User management (create/edit/deactivate/reset)
3. Class management (create/edit/add/remove/delete)
4. Admin override (reset pretest / force posttest / extend time)
5. Activity log (audit trail)
6. Every action writes audit_log row

---

## Phase 14: Modals

Build all 26 modals:
- Shared: logout_confirm
- Student: 10 modals
- Teacher/Admin: 2 modals
- Admin: 13 modals

---

## Phase 15: Profile Pages

1. Student profile
2. Teacher profile
3. Admin profile

---

## Phase 16: Tests

1. test_bkt.py — pure function tests
2. test_qlearning.py — pure function tests
3. test_feedback.py — chunker/retriever tests

---

## Phase 17: Deployment

1. Push to GitHub
2. Create Railway project
3. Add PostgreSQL
4. Set environment variables
5. Run migrations
6. Seed content
7. Build RAG index
8. Collect static
9. Create admin account
10. Smoke test

---

## Priority Order

| Priority | Phase | Why |
|---|---|---|
| 1 | Data layer | Everything depends on models |
| 2 | Core infrastructure | Can't test without auth |
| 3 | Adaptive engine | Core logic, testable in isolation |
| 4 | Student flow | Main user journey |
| 5 | Orchestrator | Ties everything together |
| 6 | RAG | Feedback after core works |
| 7 | Teacher/Admin | Monitoring after learning works |
| 8 | Deployment | Last step |
