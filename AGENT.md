# Pathgen Project Instructions

## Project

Pathgen is an adaptive-learning system for Grade 7 Philippine DepEd mathematics. The lesson sequence is fixed by prerequisite order, while each student's route adapts after practice through `advance`, `review`, or `retake` decisions.

The primary research outcome is learning gain:

posttest score - pretest score

The pretest and posttest must use the same assessment question bank.

## Communication Style

- Be concise. No fluff. Bullet points over paragraphs
- Show code, not explanations. Skip obvious context
- No filler phrases. Answer first. Explain only if asked
- Use shorthand (DRF, JWT, N+1). Flag issues in 1 line
- Direct implementation. Only relevant code parts
- If unsure: state assumption in 5 words, proceed

## Source of Truth

- Read the numbered files in `docs/` before making architectural changes. The repository currently contains `00_Overview.md` through `18_Glossary.md`.
- Preserve the documented boundaries unless the user explicitly approves a change.
- When documentation and implementation disagree, call out the discrepancy and update the smallest necessary surface.

## Technology and Shape

- Django 5 with server-rendered templates; do not introduce React, Vue, DRF, JWT, Celery, Redis, or a bundler without explicit approval.
- PostgreSQL in production, configured through `DATABASE_URL` with `dj-database-url` and `django-environ`.
- Tailwind via CDN, Geist typography, Iconsax, and minimal vanilla JavaScript.
- `numpy` is the only ML/math dependency. Use it for BKT, Q-learning, and cosine similarity.
- OpenAI `text-embedding-3-small` is used for embeddings only.
- Groq `gpt-oss-120b` is used for generated feedback.
- RAG embeddings live in `seed_data/lesson_embeddings.json`; no vector database is required.
- Deploy to Railway with Gunicorn and WhiteNoise; the intended region is Singapore.

## Architecture Boundaries

Keep the three adaptive pillars separate:

| Module | Responsibility | Must not do |
|---|---|---|
| BKT | Estimate per-student, per-lesson `p_known` | Choose actions or write feedback |
| Q-learning | Choose `advance`, `review`, or `retake` | Estimate mastery or write feedback |
| RAG-AI | Generate content-grounded feedback | Estimate mastery or choose actions |

The session-completion pipeline is always:

grade responses -> update BKT -> choose Q action -> apply action -> generate RAG feedback -> render result

It is coordinated by `adaptive/orchestrator.py`, not hidden inside an HTTP view. Feedback/API failure must degrade gracefully: leave `ai_feedback` as `NULL` and still render the result.

## Data Integrity

- Use UUID primary keys and foreign keys with `ON DELETE RESTRICT`.
- Preserve research data. Prefer soft deletion (`is_active = FALSE`, `deleted_at`) and append-only event/decision tables.
- Treat response correctness, scores, mastery-at-decision, session values, and Q-learning inputs as frozen historical snapshots.
- Never let admins, teachers, or students manually edit scores, BKT mastery, Q-learning decisions, or seeded content at runtime.
- Keep state separate from events: progress tables hold current state; sessions, responses, decisions, and audit logs preserve history.
- Enforce database constraints for answer indexes, scores, probability bounds, unique enrollments, lesson order, and distinct activity lessons.
- Seed commands must be idempotent, using stable keys such as lesson slugs and `update_or_create`.
- Do not hard-delete content or user/class records as part of normal application behavior. `reset_content` is a deliberate development/demo operation and must respect foreign-key protection.

## Learning Rules

- Lessons remain in prerequisite order; students cannot skip locked lessons or change the sequence.
- Pretest initializes BKT for every lesson from per-lesson responses.
- Exercises update BKT for one lesson; activities update BKT for both covered lessons.
- Activities cover exactly two consecutive lessons and appear after every two lessons.
- Q-learning uses three mastery bins × three attempt bins (nine states), epsilon-greedy selection, and a sensible rule-based fallback before the table has learned enough.
- Every exercise/activity session creates exactly one corresponding Q-decision row with frozen decision snapshots.
- Retakes expose hints only for questions previously answered incorrectly.
- Posttest access requires completion of all lessons unless an admin override grants access.

## Roles and Authorization

Use explicit server-side role checks and scope every query by the authenticated user:

- Admin: manages teacher/student accounts, classes, overrides, and system monitoring; cannot create another admin, edit content, edit adaptive decisions, or alter research results.
- Teacher: read-only access to content and progress for classes where `classes.teacher_id` is the current teacher; cannot view other teachers' students or modify records.
- Student: access only to their own path, sessions, results, and feedback; cannot see other students, answers before submission, or locked lessons.
- All roles may edit their own profile. Admin actions must write an append-only `audit_log` row.
- Account and class removal is soft deletion. Students without a class see the "Just Chill" state.
- Use Django session authentication, forced password change via `password_must_change`, and heartbeat-based study-time tracking.

## App Ownership

Target Django apps and responsibilities:

- `accounts`: users, classes, enrollments, sessions, audit log, auth/profile flows.
- `curriculum`: lessons and seeded assessment/exercise/activity content.
- `progress`: student and lesson progress state.
- `assessment`: pretest/posttest sessions, responses, and time configuration.
- `practice`: exercise/activity mechanics and the submit trigger point.
- `adaptive`: BKT, Q-learning, orchestrator, and decision persistence.
- `feedback`: chunking, embedding clients, retrieval, prompts, generation, and RAG index command.
- `monitoring`: read-only teacher/admin dashboards.
- `core`: decorators, middleware, and shared infrastructure.

Keep pure adaptive functions free of Django imports where documented so they can be tested in isolation.

## Frontend Rules

- Primary color: #0CC0DF
- Replicate shadcn/ui aesthetic
- Tailwind CDN + Geist + Iconsax
- Sidebar layout with profile dropdown
- All pages mobile-responsive:
  - Mobile-first approach (p-4 default, md:p-6, lg:p-8)
  - Sidebar: collapsible on mobile (hidden md:flex)
  - Tables: horizontal scroll on mobile (overflow-x-auto)
  - Modals: full-width on mobile (w-full md:max-w-md)
  - Grids: stack on mobile (grid-cols-1 md:grid-cols-2 lg:grid-cols-3)
  - Touch targets: minimum 44px on buttons and clickable elements
  - Student, teacher, admin all responsive
- Use Django templates and the documented page/modal structure. Keep student, teacher, and admin base templates distinct.
- Keep student content free of answers and hints; teacher/admin content views may show them read-only.
- Use accessible forms, explicit confirmation for destructive or irreversible actions, visible timer warnings, and clear empty/error states.
- Keep the interface calm and classroom-focused; do not add decorative UI that weakens task clarity or assessment integrity.
- For frontend visual work, consult the local skill at `../skills/taste/SKILL.md` and adapt its guidance to Django templates. Do not add a SPA or GSAP runtime solely to satisfy a visual preference.

## Key Terms

- Just Chill = "Please wait for the admin to add this account to your respective class."
- Empty State = "Chill lang, just chill."
- BKT = Bayesian Knowledge Tracing (mastery estimation)
- Q-learning = action selection (advance/review/retake)
- RAG = Retrieval-Augmented Generation (feedback)
- Orchestrator = Grade → BKT → Q-learning → Apply → RAG
- Primary color = #0CC0DF

## Build Order

Follow the documented sequence unless there is a strong reason to deviate:

1. Project setup and settings
2. Models, constraints, migrations
3. Core auth, role checks, heartbeat, base templates
4. Seed data commands
5. Pure BKT and Q-learning logic with tests
6. Student pretest and learning path
7. Orchestrator and exercise flow
8. Activities and video checkpoints
9. RAG pipeline and feedback display
10. Posttest and completion/learning-gain page
11. Teacher monitoring
12. Admin management, overrides, and audit log
13. Modals and profile pages
14. Full tests and deployment

## Validation

Before considering a change complete:

- Run focused tests for changed logic, then the full Django test suite when available.
- Test authorization with both allowed and forbidden users, especially teacher class scoping and student isolation.
- Test the full student path: login -> pretest -> BKT initialization -> lesson -> exercise -> BKT/Q/RAG orchestration -> activity -> posttest -> learning gain.
- Test graceful degradation when OpenAI, Groq, or the embeddings file is unavailable.
- Verify migrations, seed idempotency, database constraints, timers, heartbeat duration, and audit rows.
- Never commit secrets, `.env`, generated embeddings, virtual environments, or static build output.

Useful commands:

python manage.py makemigrations
python manage.py migrate
python manage.py seed_content
python manage.py build_rag_index
python manage.py test
python manage.py runserver

## Deployment Expectations

Production requires `SECRET_KEY`, `DEBUG=False`, `DATABASE_URL`, `ALLOWED_HOSTS`, `GROQ_API_KEY`, `GROQ_MODEL`, `OPENAI_API_KEY`, and `EMBEDDING_MODEL`. Deploy with Gunicorn, run migrations, seed content, build the RAG index, collect static files, create an admin account, and perform a smoke test before study data collection.