# 06 — User Flows

Complete walkthroughs of how each role moves through the system.

---

## Student Flow

### 1. Login

Student logs in  
↓  
Has class?  
├── NO → just_chill.html ("Please wait for the admin...")  
└── YES → Continue  
↓  
password_must_change?  
├── YES → change_password.html  
└── NO → Continue  
↓  
Pretest taken?  
├── NO → student_dashboard.html → prompt to take pretest  
└── YES → student_dashboard.html → show progress


---

### 2. Pretest Flow

student_dashboard.html  
→ Click "Start Pretest"  
→ pretest_start_confirm modal  
→ pretest.html (timer starts)  
→ Answer MCQ questions  
→ time_warning modal (5 min remaining)  
→ Click "Submit"  
→ pretest_submit_confirm modal  
→ Grade responses  
→ Write assessment_sessions + assessment_responses  
→ Initialize BKT per lesson from pretest answers  
→ Create student_progress row  
→ pretest_result.html (show score)  
→ Click "Start Learning"  
→ lesson_path.html


---

### 3. Lesson Flow

lesson_path.html  
→ Click current lesson  
→ lesson_page.html (read content blocks)  
→ Click "Start Exercise"  
→ exercise_start_confirm modal  
→ short_exercise.html  
→ Answer MCQ questions  
→ Click "Submit"  
→ exercise_submit_confirm modal  
→ Grade responses  
→ Write exercise_sessions + exercise_responses  
→ BKT updates mastery for this lesson  
→ Q-learning decides: advance / review / retake  
→ RAG generates feedback  
→ short_exercise_result.html  
→ Shows: score, AI feedback, next step


---

### 4. Decision Outcomes

| Decision | What Happens |
|---|---|
| **Advance** | Next lesson unlocks. Student returns to lesson_path.html |
| **Review** | Same lesson again. Student reads lesson_page.html, then new exercise |
| **Retake** | Same exercise again. Hints now appear for previously wrong questions |

---

### 5. Activity Flow (Every 2 Lessons)

After completing 2 lessons  
→ lesson_path.html shows activity  
→ Click "Start Activity"  
→ activity_start_confirm modal  
→ activity.html  
→ Answer mixed media questions (text, image, video)  
→ video_checkpoint.js pauses at checkpoint seconds  
→ Click "Submit"  
→ activity_submit_confirm modal  
→ Grade responses  
→ Write activity_sessions + activity_responses  
→ BKT updates mastery for BOTH lessons  
→ Q-learning decides  
→ RAG generates feedback  
→ activity_result.html


---

### 6. Posttest Flow

All lessons completed (or admin override)  
→ lesson_path.html shows "Start Posttest"  
→ Click "Start Posttest"  
→ posttest_start_confirm modal  
→ posttest.html (timer starts)  
→ Answer MCQ questions  
→ time_warning modal (5 min remaining)  
→ Click "Submit"  
→ posttest_submit_confirm modal  
→ Grade responses  
→ Write assessment_sessions + assessment_responses  
→ posttest_result.html (show score)  
→ Click "View Completion"  
→ completion.html  
→ Shows: pretest score, posttest score, learning gain


---

## Teacher Flow

### 1. Login

Teacher logs in  
↓  
password_must_change?  
├── YES → change_password.html  
└── NO → Continue  
↓  
teacher_dashboard.html  
→ Shows assigned classes summary


---

### 2. View Classes

teacher_dashboard.html  
→ Click "Classrooms"  
→ teacher_classroom_list.html  
→ Shows all assigned classes  
→ Click a class  
→ classroom_detail.html  
→ Shows student list


---

### 3. View Student Detail

classroom_detail.html  
→ Click student name  
→ student_quick_view modal (quick snapshot)  
→ Click "View Full Detail"  
→ student_detail.html  
→ Shows 10 monitoring metrics:

1. Student info
    
2. Current lesson
    
3. Overall progress
    
4. Assessment results
    
5. BKT mastery estimates
    
6. Q-learning decisions
    
7. Attempts
    
8. Study time summary
    
9. Hint usage
    
10. Last activity


---

### 4. View Content

Teacher sidebar  
→ Click "Content"  
→ content_page.html  
→ Browse lessons, exercises, activities  
→ Click "Preview" → content_preview modal  
→ Click "Open Full Page"  
→ lesson_page.html or activity_page.html  
→ Read-only view with answers/hints visible


---

## Admin Flow

### 1. Login

Admin logs in  
↓  
password_must_change?  
├── YES → change_password.html  
└── NO → Continue  
↓  
admin_dashboard.html  
→ System-wide stats


---

### 2. User Management

admin_dashboard.html  
→ Click "Users"  
→ user_management.html  
→ Shows all users (teachers + students)  
→ Actions:

- Create User → create_user modal
    
- Edit User → edit_user modal
    
- Deactivate User → deactivate_user_confirm modal
    
- Reset Password → reset_password_confirm modal
    
- Create Class → create_class modal


---

### 3. Class Management

user_management.html or admin_dashboard.html  
→ Click a class  
→ classroom_detail.html  
→ Actions:

- Add Student → add_student_to_class modal
    
- Remove Student → remove_student_from_class modal
    
- Edit Class → edit_class modal
    
- Delete Class → delete_class_confirm modal  
    → Click student name  
    → student_detail.html (view-only)


---

### 4. Content View

Admin sidebar  
→ Click "Contents"  
→ content_page.html  
→ Browse all lessons and activities  
→ Read-only view with answers/hints visible


---

### 5. Overrides

Admin sidebar  
→ Click "Override"  
→ admin_override.html  
→ Select student  
→ Actions:

- Reset Pretest → reset_pretest_confirm modal  
    → Wipes progress, student restarts  
    → audit_log row written
    
- Force Posttest → force_posttest_confirm modal  
    → Grants early posttest access  
    → audit_log row written
    
- Extend Time → extend_time modal  
    → Adds minutes to active test session  
    → audit_log row written


---

### 6. Activity Log

Admin sidebar  
→ Click "Activity Logs"  
→ activity_log.html  
→ Shows all admin actions  
→ Click a row  
→ audit_detail modal  
→ Shows full audit details


---

## Complete Flow Map


LOGIN  
├── STUDENT → JustChill (if no class) → Dashboard → Pretest → Lesson Path → Lessons → Exercises → Activities → Posttest → Completion  
├── TEACHER → Dashboard → Classrooms → Student Detail / Content  
└── ADMIN → Dashboard → Users / Classrooms / Contents / Override / Activity Logs


---

## Key State Checks

| Check                 | When              | What Happens                     |
| --------------------- | ----------------- | -------------------------------- |
| Has class?            | Student login     | No → Just Chill screen           |
| Password must change? | Any login         | Yes → Force change password      |
| Pretest taken?        | Student dashboard | No → Prompt to take pretest      |
| All lessons done?     | Posttest access   | No → Block unless admin override |
| Admin override?       | Posttest access   | Yes → Allow early posttest       |
| Active session?       | Extend time       | Only works on in-progress test   |
## Error Handling

| Situation                                 | Response                              |
| ----------------------------------------- | ------------------------------------- |
| Student tries to skip lesson              | Blocked — prerequisite chain enforced |
| Student tries posttest without completing | Blocked — unless admin override       |
| Teacher tries to view other class         | Blocked — own class only              |
| Admin tries to delete class with students | Blocked — FK RESTRICT + app guard     |
| RAG generation fails                      | ai_feedback = NULL, page still works  |
| OpenAI API fails                          | Feedback skipped, page still works    |
| Groq API fails                            | Feedback skipped, page still works    |