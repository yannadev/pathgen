# 00 — System Overview

## What This System Is

Pathgen is an adaptive learning system for Grade 7 Philippine DepEd mathematics.

The lesson sequence is FIXED (prerequisite chain — order never changes), but each student's PATH through that sequence ADAPTS. After every exercise and activity, the system decides:

- **Advance** — move to next lesson
- **Review** — study current lesson again
- **Retake** — retry exercise with hints

A pretest sets baseline. A posttest (same questions) measures learning gain. That gain is the thesis result.

---

## Three-Pillar Architecture

| Module | Job | Never Does |
|---|---|---|
| BKT | Estimates mastery probability per lesson | Never decides actions, never writes feedback |
| Q-learning | Decides action (advance/review/retake) | Never estimates mastery, never writes feedback |
| RAG-AI | Generates feedback from lesson content | Never estimates mastery, never decides actions |

Mastery lives in `bkt_mastery`.
Actions live in `*_q_decisions` tables.
Feedback lives in `ai_feedback` columns.

---

## Roles

### Admin
**Can:**
- Create teacher and student accounts
- Deactivate accounts (soft delete)
- Create classes, assign teachers and students
- Reset student's pretest (wipes progress)
- Force posttest eligibility
- Extend assessment time limits
- View all student progress
- View audit log
- Edit own profile

**Cannot:**
- Edit content
- Edit BKT or Q-learning decisions
- Create other admin accounts

### Teacher
**Can:**
- View own class students' progress
- View content (lessons, exercises, activities)
- Edit own profile

**Cannot:**
- Edit content
- Edit student records
- View students outside their class

### Student
**Can:**
- See own learning path and progress
- Take pretest, lessons, exercises, activities, posttest
- See own feedback and results
- Edit own profile

**Cannot:**
- See other students' data
- See answers before answering
- Skip lessons

---

## Learning Flow

1. **Login**
2. **Pretest** — MCQ, timed, questions mapped to lessons
3. **BKT Initialization** — per-lesson mastery from pretest answers
4. **Dashboard / Learning Path** — fixed lesson sequence with status
5. **Lesson** — read structured content blocks
6. **Short Exercise** — text-only MCQs, study time tracked
7. **Session Completion** — Grade → BKT update → Q-learning decision → RAG feedback
8. **Result Page** — score, feedback, next action
9. **Activity** (every 2 lessons) — mixed media, updates BKT for both lessons
10. **Posttest** — same questions as pretest
11. **Completion** — learning gain shown

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django 5 + Templates |
| Database | PostgreSQL (Railway) |
| ML Math | numpy |
| Embeddings | OpenAI text-embedding-3-small |
| Generation | Groq gpt-oss-120b |
| RAG Storage | JSON file in project |
| Frontend | Tailwind CDN + Geist + Iconsax + vanilla JS |
| Server | gunicorn + whitenoise |
| Platform | Railway |

---

## Key Principles

1. Lesson order fixed, path adaptive
2. BKT + Q-learning = adaptive decisions
3. RAG feedback grounded in content
4. Research data never deleted
5. Three-pillar separation for thesis defense