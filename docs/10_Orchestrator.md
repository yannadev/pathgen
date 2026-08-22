# 10 — Orchestrator

---

## What the Orchestrator Is

The orchestrator is the **grand central** — the function called when a student submits an exercise or activity.

It coordinates: **Grade → BKT → Q-learning → Apply Action → RAG Feedback**

---

## Where It Lives

```
adaptive/
├── bkt.py
├── qlearning.py
└── orchestrator.py    # ← this file
```

Called from: `practice/views.py` → `submit_session()`

---

## The Flow

```
Student submits exercise/activity
  ↓
1. GRADE RESPONSES
  ↓
2. BKT UPDATE
  ↓
3. Q-LEARNING DECISION
  ↓
4. APPLY ACTION
  ↓
5. RAG FEEDBACK
  ↓
6. RENDER RESULT PAGE
```

---

## Step by Step

### Step 1: Grade Responses

**What happens:**
- Compare selected answers to correct answers
- Write `exercise_sessions` or `activity_sessions` row
- Write `exercise_responses` or `activity_responses` rows

**Data written:**
- Score (percentage)
- Total questions
- Study time
- Each response with is_correct + hint_used

---

### Step 2: BKT Update

**What happens:**
- Call `bkt.py update_mastery()`
- For exercise: update that lesson's mastery
- For activity: update BOTH lessons' mastery

**Data written:**
- `bkt_mastery` rows updated with new p_known

---

### Step 3: Q-Learning Decision

**What happens:**
- Collect decision inputs:
  - mastery_at_decision (from step 2)
  - study_time_seconds (cumulative)
  - attempt_count (for this lesson)
  - session_score (from step 1)
  - hint_count (cumulative)
- Call `qlearning.py get_action()`
- Get action: advance / review / retake

**Data written:**
- One row in `exercise_q_decisions` or `activity_q_decisions`
- Frozen snapshots of all inputs
- UNIQUE constraint on session_id

---

### Step 4: Apply Action

**What happens based on action:**

| Action | Effect |
|---|---|
| advance | lesson_progress → passed, next lesson unlocked, student_progress.current_lesson_id updated |
| review | lesson_progress → needs_review, student reads lesson again |
| retake | Exercise available again, hints enabled for previously wrong questions |

---

### Step 5: RAG Feedback

**What happens:**
- Collect wrong items (question_text + hint_text)
- Build query
- Embed query (OpenAI)
- Retrieve top 4 chunks from lesson_embeddings.json
- Build prompt
- Generate feedback (Groq)
- Save to `ai_feedback` column

**If any step fails:**
- `ai_feedback = NULL`
- Page still renders without feedback
- System does NOT crash

---

### Step 6: Render Result Page

**What happens:**
- Redirect to result page
- Shows: score, AI feedback, next action

---

## Code Structure

```python
# adaptive/orchestrator.py

def process_session_completion(session, responses):
    """
    Called when student submits exercise or activity.
    """
    # Step 1: Grade
    score = grade_responses(session, responses)
    
    # Step 2: BKT
    mastery = bkt.update_mastery(
        p_known=session.student.current_mastery(session.lesson),
        n_correct=score.correct_count,
        n_wrong=score.wrong_count,
        p_learn=params.p_learn,
        p_slip=params.p_slip,
        p_guess=params.p_guess
    )
    bkt_mastery.objects.update_or_create(
        student=session.student,
        lesson=session.lesson,
        defaults={'p_known': mastery}
    )
    
    # Step 3: Q-learning
    state = get_state(mastery, attempt_count)
    action = qlearning.get_action(state, q_table)
    q_decisions.objects.create(
        student=session.student,
        lesson=session.lesson,
        session=session,
        action=action,
        mastery_at_decision=mastery,
        study_time_seconds=study_time,
        attempt_count=attempt_count,
        session_score=score.percentage,
        hint_count=hint_count
    )
    
    # Step 4: Apply action
    apply_action(action, session, student_progress, lesson_progress)
    
    # Step 5: RAG feedback
    feedback = generate_feedback(session, responses, score)
    session.ai_feedback = feedback
    session.save()
    
    # Step 6: Return result
    return {
        'score': score,
        'feedback': feedback,
        'action': action
    }
```

---

## Error Handling

| Failure Point | What Happens |
|---|---|
| Grading fails | Session not written — student can retry |
| BKT fails | Log error, continue without mastery update |
| Q-learning fails | Use rule-based fallback |
| RAG fails | ai_feedback = NULL, continue |
| Any API fails | Feedback skipped, page still works |

**The system never crashes because one module fails.**

---

## Key Design Decisions

| Decision | Why |
|---|---|
| Orchestrator separate from views | Clean separation — views handle HTTP, orchestrator handles logic |
| Sequential steps | Clear order, easy to debug |
| Frozen snapshots | Thesis receipts at decision time |
| Graceful degradation | RAG failure doesn't block BKT/Q-learning |
| One trigger point | Both exercise and activity go through same flow |

---

## Thesis Wording

> "The orchestrator module coordinates the adaptive pipeline. Upon session completion, it grades responses, updates BKT mastery, invokes Q-learning to select an action, applies that action to the student's progress state, and generates RAG-grounded feedback. Each module operates independently — failure in feedback generation does not affect mastery estimation or decision-making. The orchestrated flow writes frozen snapshots at each decision point, providing reproducible evidence of the adaptive process."