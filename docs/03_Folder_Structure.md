# 03 — Folder Structure
pathgen/  
├── manage.py  
├── Procfile  
├── runtime.txt  
├── requirements.txt  
├── .env.example  
├── .gitignore  
│  
├── config/  
│ ├── **init**.py  
│ ├── settings.py  
│ ├── urls.py  
│ ├── wsgi.py  
│ └── asgi.py  
│  
├── core/  
│ ├── **init**.py  
│ ├── decorators.py # role_required, student_only, teacher_own_class, admin_only  
│ └── middleware.py # heartbeat (login/30-60s ping/logout)  
│  
├── accounts/ # users, classes, class_students, user_sessions, audit_log  
│ ├── **init**.py  
│ ├── models.py  
│ ├── forms.py  
│ ├── urls.py  
│ ├── views.py  
│ ├── admin.py  
│ └── templates/  
│ └── accounts/  
│ ├── login.html  
│ ├── change_password.html  
│ ├── student_profile.html  
│ ├── teacher_profile.html  
│ └── admin_profile.html  
│  
├── curriculum/ # lessons, assessment_questions, exercise_questions, activities, activity_questions  
│ ├── **init**.py  
│ ├── models.py  
│ ├── urls.py  
│ ├── views.py  
│ ├── admin.py  
│ ├── management/  
│ │ └── commands/  
│ │ ├── seed_content.py  
│ │ └── reset_content.py  
│ └── templates/  
│ └── curriculum/  
│ └── lesson_page.html # student reads lesson content  
│  
├── progress/ # student_progress, lesson_progress  
│ ├── **init**.py  
│ ├── models.py  
│ ├── urls.py  
│ ├── views.py  
│ └── templates/  
│ └── progress/  
│ ├── student_dashboard.html  
│ ├── lesson_path.html  
│ └── completion.html  
│  
├── assessment/ # assessment_sessions, assessment_responses, assessment_config  
│ ├── **init**.py  
│ ├── models.py  
│ ├── forms.py  
│ ├── urls.py  
│ ├── views.py  
│ └── templates/  
│ └── assessment/  
│ ├── pretest.html  
│ ├── pretest_result.html  
│ ├── posttest.html  
│ └── posttest_result.html  
│  
├── practice/ # exercise_sessions/responses, activity_sessions/responses  
│ ├── **init**.py  
│ ├── models.py  
│ ├── forms.py  
│ ├── urls.py  
│ ├── views.py # ★ submit_session = grade → BKT → Q-decision → RAG feedback  
│ └── templates/  
│ └── practice/  
│ ├── short_exercise.html  
│ ├── short_exercise_result.html  
│ ├── activity.html  
│ └── activity_result.html  
│  
├── adaptive/ # bkt_model_parameters, bkt_mastery, exercise_q_decisions, activity_q_decisions  
│ ├── **init**.py  
│ ├── models.py  
│ ├── bkt.py # pure numpy — init from pretest, update per session  
│ ├── qlearning.py # Q-table + action selection  
│ └── orchestrator.py # called at session completion  
│  
├── feedback/ # RAG module (JSON-based, no vector DB)  
│ ├── **init**.py  
│ ├── chunker.py # structure-aware chunking (300-500 tokens)  
│ ├── clients.py # openai + groq clients  
│ ├── prompts.py # prompt templates  
│ ├── retriever.py # load JSON → embed query → cosine similarity → top 4  
│ ├── generator.py # prompt → groq → feedback text  
│ ├── management/  
│ │ └── commands/  
│ │ └── build_rag_index.py # chunk → embed → write JSON file  
│ └── tests/  
│ └── **init**.py  
│  
├── monitoring/ # read-only dashboards for teacher + admin  
│ ├── **init**.py  
│ ├── urls.py  
│ ├── views.py  
│ └── templates/  
│ └── monitoring/  
│ ├── teacher/  
│ │ ├── teacher_dashboard.html  
│ │ └── teacher_classroom_list.html  
│ │  
│ ├── admin/  
│ │ ├── admin_dashboard.html  
│ │ ├── user_management.html  
│ │ ├── admin_override.html  
│ │ └── activity_log.html  
│ │  
│ └── shared/  
│ ├── classroom_detail.html  
│ ├── student_detail.html  
│ ├── content_page.html  
│ ├── lesson_page.html # teacher/admin view-only  
│ └── activity_page.html # teacher/admin view-only  
│  
├── templates/  
│ ├── base.html # Tailwind CDN, Geist font, Iconsax CDN  
│ ├── student_base.html # sidebar: Dashboard, Lesson, Profile  
│ ├── teacher_base.html # sidebar: Dashboard, Classrooms, Content, Profile  
│ ├── admin_base.html # sidebar: Dashboard, Users, Classrooms, Contents, Override, Activity Logs, Profile  
│ └── components/  
│ ├── sidebar.html  
│ ├── profile_dropdown.html # Picture + Name + Role → click → account + logout  
│ ├── just_chill.html # "Please wait for the admin to add this account to your respective class."  
│ ├── empty_state.html # "Chill lang, just chill."  
│ └── modals/  
│ ├── logout_confirm.html  
│ ├── pretest_start_confirm.html  
│ ├── pretest_submit_confirm.html  
│ ├── exercise_start_confirm.html  
│ ├── exercise_submit_confirm.html  
│ ├── activity_start_confirm.html  
│ ├── activity_submit_confirm.html  
│ ├── posttest_start_confirm.html  
│ ├── posttest_submit_confirm.html  
│ ├── hint_modal.html  
│ ├── time_warning.html  
│ ├── student_quick_view.html  
│ ├── content_preview.html  
│ ├── create_user.html  
│ ├── edit_user.html  
│ ├── deactivate_user_confirm.html  
│ ├── reset_password_confirm.html  
│ ├── create_class.html  
│ ├── edit_class.html  
│ ├── add_student_to_class.html  
│ ├── remove_student_from_class.html  
│ ├── delete_class_confirm.html  
│ ├── reset_pretest_confirm.html  
│ ├── force_posttest_confirm.html  
│ ├── extend_time.html  
│ └── audit_detail.html  
│  
├── static/  
│ ├── css/  
│ │ └── main.css  
│ ├── js/  
│ │ ├── heartbeat.js # 30-60s ping to user_sessions  
│ │ ├── timer.js # assessment countdown  
│ │ └── video_checkpoint.js # activity video: pause at checkpoint → show question  
│ └── assets/  
│ ├── logos/  
│ │ ├── pathgen_logo.svg  
│ │ └── pathgen_logo_emblem.svg  
│ └── profiles/  
│ ├── admin_default_profile.svg  
│ ├── teacher_default_profile.svg  
│ └── student_default_profile.svg  
│  
├── seed_data/  
│ ├── lessons.json  
│ ├── assessment_questions.json  
│ ├── exercise_questions.json  
│ ├── activities.json  
│ ├── activity_questions.json  
│ └── lesson_embeddings.json # generated by build_rag_index  
│  
└── tests/  
├── **init**.py  
├── test_bkt.py  
├── test_qlearning.py  
└── test_feedback.py


---

## App Ownership

| App | Owns Tables | Responsibility |
|---|---|---|
| accounts | users, classes, class_students, user_sessions, audit_log | Auth, roles, admin actions, heartbeat |
| curriculum | lessons, assessment_questions, exercise_questions, activities, activity_questions | Content + seed commands |
| progress | student_progress, lesson_progress | Where each student is on the path |
| assessment | assessment_sessions, assessment_responses, assessment_config | Pretest/posttest delivery |
| practice | exercise_sessions/responses, activity_sessions/responses | Quiz mechanics + submit trigger point |
| adaptive | bkt_model_parameters, bkt_mastery, exercise_q_decisions, activity_q_decisions | Pure-logic engine + persistence |
| feedback | — (JSON file storage) | Chunker, embedder, retriever, generator |
| monitoring | — (reads everything) | Teacher/admin dashboards |
| core | — | Role decorators, heartbeat middleware |

---

## Counts

| Component | Count |
|---|---|
| Django apps | 9 |
| Page templates | 29 |
| Modal templates | 26 |
| Component templates | 4 |
| Base templates | 4 |
| Management commands | 3 |
| JS files | 3 |
| Asset files | 5 |
| Python dependencies | 9 |
| Database tables | 23 