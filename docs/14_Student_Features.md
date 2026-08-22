# 14 — Student Features

---

## Overview

Student is the learner. Sees only own learning path and progress. Takes pretest, lessons, exercises, activities, and posttest. Receives adaptive decisions and AI feedback.

---

## Login States

### No Class Assigned

- Student logs in
- Not in `class_students`
- Sees just_chill.html
- Message: "Please wait for the admin to add this account to your respective class."

### Class Assigned

- Student logs in
- Has class_students row
- Sees student_dashboard.html
- Shows: class name, teacher name

---

## Pretest Flow

### Start

- Student clicks "Start Pretest"
- pretest_start_confirm modal
- Timer starts

### During

- MCQ questions (mix of text and image)
- Timer visible
- time_warning modal at 5 minutes remaining

### Submit

- Click "Submit"
- pretest_submit_confirm modal
- System grades responses
- BKT initialized per lesson

### Result

- pretest_result.html
- Shows baseline score
- Button: "Start Learning"

---

## Lesson Path

### lesson_path.html

Shows fixed lesson sequence:

| Element | What It Shows |
|---|---|
| Lesson cards | Title, status, position |
| Current position | Highlighted |
| Locked lessons | Future lessons (not accessible yet) |
| Completed lessons | Checkmark |
| Activities | After every 2 lessons |
| Posttest | At end (unlocked when all done) |

---

## Lesson Reading

### lesson_page.html (Student View)

- Reads content blocks from content_jsonb
- Blocks: headings, paragraphs, examples, images
- No answers or hints visible

---

## Short Exercise

### short_exercise.html

- Text-only MCQ questions
- Randomly selected from lesson's question bank
- Study time tracked via heartbeat
- Submit button

### Retake Mode

- If Q-learning decides "retake"
- Same exercise again
- Hints appear for previously wrong questions
- hint_modal shows hint text

---

## Result Pages

### short_exercise_result.html

Shows:
- Score (percentage)
- AI feedback (if generated)
- Next action:
  - "Advance to next lesson" → link to next lesson
  - "Review this lesson" → link to lesson page
  - "Retry exercise with hints" → link to exercise retake

### activity_result.html

Same structure for activities:
- Score
- AI feedback
- Next action

---

## Activity Flow

### activity.html

- Mixed media questions
- Text questions
- Image questions
- Video questions with checkpoints
- video_checkpoint.js pauses at checkpoint seconds
- Question appears, student answers, video resumes

### Every 2 Lessons

- After lessons 2, 4, 6, 8, 10...
- Activity covers the previous 2 lessons

---

## Posttest Flow

### Access

- All lessons completed → posttest unlocked
- OR admin override → posttest available early

### Same as Pretest

- Same question bank
- Same delivery mechanics
- Timer applies

### Result

- posttest_result.html
- Shows final score
- Button: "View Completion"

---

## Completion

### completion.html

Shows:
- Pretest score
- Posttest score
- Learning gain (posttest - pretest)
- Completion message

---

## Profile

### student_profile.html

Student can:
- View own name, email
- Edit name
- Edit password
- Edit profile picture

Student cannot:
- Change role
- View other students
- See own BKT values directly (only through progress views)

---

## Key Restrictions

| Student CANNOT | Reason |
|---|---|
| See other students' data | Privacy |
| See answers before answering | Assessment integrity |
| See hints before retake | Adaptive design |
| Skip lessons | Prerequisite chain |
| Change lesson order | Fixed sequence |
| Take posttest early | Unless admin override |
| Edit own progress | System-managed |
| View teacher/admin pages | Role-based access |

---

## Permission Matrix (Student)

| Action                       | Allowed           |
| ---------------------------- | ----------------- |
| View own dashboard           | ✅                 |
| Take pretest                 | ✅                 |
| Read lessons                 | ✅                 |
| Take exercises               | ✅                 |
| Take activities              | ✅                 |
| Take posttest                | ✅ (when unlocked) |
| See own results              | ✅                 |
| See own AI feedback          | ✅                 |
| See hints (on retake)        | ✅                 |
| Edit own profile             | ✅                 |
| View other students          | ❌                 |
| See answers before answering | ❌                 |
| Skip lessons                 | ❌                 |
| Edit anything else           | ❌                 |