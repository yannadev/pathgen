# 08 — BKT Engine

---

## What BKT Is

Bayesian Knowledge Tracing — estimates the probability that a student has mastered a specific skill (lesson).

**Output:** `p_known` — a number between 0 and 1 for each student per lesson.

**Role:** Knowledge estimation ONLY. Never decides actions. Never writes feedback.

---

## Where BKT Lives

```
adaptive/
├── bkt.py               # pure numpy — no Django imports
├── qlearning.py         # Q-table + action selection
└── orchestrator.py      # calls bkt.py and qlearning.py at session completion
```

---

## Global Parameters

Stored in `bkt_model_parameters` table — one row for all students.

| Parameter | Meaning | Default |
|---|---|---|
| p_learn | P(learning the skill per practice opportunity) | 0.2 |
| p_slip | P(wrong answer despite knowing) | 0.1 |
| p_guess | P(right answer despite not knowing) | 0.25 |

**Why global:** These are content/assessment properties, not student properties. Shared by all students.

---

## Initialization (After Pretest)

When a student completes the pretest:

1. Pretest responses are grouped by `lesson_id` (via assessment_questions)
2. For each lesson:
   - Count correct answers
   - Count total questions
   - Compute initial `p_known`

### Formula

```
p_known_initial = (correct / total) × (1 - p_guess) + p_guess × (1 - correct / total)
```

### Simplified

If a student gets:
- 4/5 correct on Lesson 1 questions → high initial mastery for Lesson 1
- 1/5 correct on Lesson 2 questions → low initial mastery for Lesson 2

### Code Structure

```python
# adaptive/bkt.py

def init_mastery(correct_count, total_count, p_guess):
    """
    Initialize mastery probability from pretest results.
    """
    if total_count == 0:
        return 0.5  # no data — neutral
    
    accuracy = correct_count / total_count
    p_known = accuracy * (1 - p_guess) + p_guess * (1 - accuracy)
    
    return max(0.0, min(1.0, p_known))  # clamp to [0, 1]
```

---

## Update (After Exercise or Activity)

When a student completes an exercise or activity:

1. Responses are graded
2. Count correct and wrong answers
3. Apply Bayesian update

### Formula

```
P(observed responses | mastered) = (1 - p_slip)^correct × p_slip^wrong
P(observed responses | not mastered) = p_guess^correct × (1 - p_guess)^wrong

posterior = p_known × P(observed | mastered)
posterior /= posterior + (1 - p_known) × P(observed | not mastered)

p_known_new = posterior × (1 - p_learn) + p_learn
```

### What This Means

| Part | Meaning |
|---|---|
| First term | Evidence from this session's answers |
| Second term | Probability of learning from this practice opportunity |
| Combined | Updated mastery estimate |

### Code Structure

```python
# adaptive/bkt.py

def update_mastery(p_known, n_correct, n_wrong, p_learn, p_slip, p_guess):
    """
    Bayesian update of mastery probability after a session.
    """
    p_right_given_known = 1 - p_slip
    p_right_given_unknown = p_guess
    
    # Likelihood of observed responses under each state
    likelihood_known = (p_right_given_known ** n_correct) * (p_slip ** n_wrong)
    likelihood_unknown = (p_right_given_unknown ** n_correct) * ((1 - p_guess) ** n_wrong)
    
    # Bayesian update
    posterior = p_known * likelihood_known
    posterior /= (posterior + (1 - p_known) * likelihood_unknown)
    
    # Add learning probability
    p_known_new = posterior + (1 - posterior) * p_learn
    
    return max(0.0, min(1.0, p_known_new))
```

---

## When BKT Runs

| Trigger | What Happens |
|---|---|
| Pretest submitted | Initialize mastery for EVERY lesson |
| Exercise submitted | Update mastery for THAT lesson |
| Activity submitted | Update mastery for BOTH covered lessons |

---

## What BKT Does NOT Do

| Does NOT | Why |
|---|---|
| Decide actions | That's Q-learning |
| Generate feedback | That's RAG |
| Write to audit log | That's admin actions |
| Change lesson order | Fixed sequence |
| Store scores | Sessions/responses tables do that |

---

## Data Flow

```
Pretest submitted
  → assessment_responses written
  → bkt.py init_mastery() called per lesson
  → bkt_mastery rows created (one per lesson)

Exercise submitted
  → exercise_responses written
  → bkt.py update_mastery() called for that lesson
  → bkt_mastery row updated

Activity submitted
  → activity_responses written
  → bkt.py update_mastery() called for BOTH lessons
  → bkt_mastery rows updated
```

---

## Key Design Decisions

| Decision | Why |
|---|---|
| Pure numpy | No ML framework needed |
| No Django imports in bkt.py | Easy to test, clean separation |
| Global parameters in DB | Can tune without code changes |
| Initialized from pretest | Baseline per lesson, not just overall |
| Bayesian update | Standard BKT, defensible in thesis |

---

## Thesis Wording

> "Bayesian Knowledge Tracing estimates per-lesson mastery probabilities. Global parameters P(Learn), P(Slip), and P(Guess) are seeded from literature values and shared across students. Mastery is initialized from pretest responses and updated after each exercise and activity using standard Bayesian update. BKT serves exclusively as the knowledge estimation module — it does not make adaptive decisions or generate feedback."