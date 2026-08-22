# 09 — Q-Learning

---

## What Q-Learning Is

Q-learning decides the next action after a student completes an exercise or activity.

**Output:** One of three actions:
- **advance** — move to next lesson
- **review** — study current lesson again
- **retake** — retry exercise with hints

**Role:** Decision-making ONLY. Never estimates mastery. Never writes feedback.

---

## Where Q-Learning Lives

```
adaptive/
├── bkt.py               # BKT math
├── qlearning.py         # Q-table + action selection
└── orchestrator.py      # calls both at session completion
```

---

## The Q-Table

A Q-table maps states to action values.

| State | advance | review | retake |
|---|---|---|---|
| (0, 0) | 0.0 | 0.0 | 0.0 |
| (0, 1) | 0.0 | 0.0 | 0.0 |
| (1, 0) | 0.0 | 0.0 | 0.0 |
| ... | ... | ... | ... |

**Stored as:** JSON file in `adaptive/qtable.json` (or in the database — decision: JSON file for simplicity)

---

## States

A state is defined by two features:

| Feature | Bins | Values |
|---|---|---|
| Mastery level | 3 | low (0.0-0.4), medium (0.4-0.7), high (0.7-1.0) |
| Attempt count | 3 | 1, 2, 3+ |

**Total states:** 3 × 3 = 9

---

## Actions

| Action | Meaning |
|---|---|
| advance | Student has mastered this lesson — move on |
| review | Student needs more study time — re-read lesson |
| retake | Student needs practice — retry exercise with hints |

---

## Decision Inputs

When deciding, Q-learning receives:

| Input | Source |
|---|---|
| mastery_at_decision | bkt_mastery.p_known |
| study_time_seconds | Cumulative for this lesson |
| attempt_count | Exercise attempts for this lesson |
| session_score | Score of triggering session |
| hint_count | Cumulative hints for this lesson |

---

## Decision Logic

### At Decision Time

```python
# adaptive/qlearning.py

def get_action(state, q_table, epsilon=0.1):
    """
    Select action using epsilon-greedy strategy.
    """
    if np.random.random() < epsilon:
        # Explore: random action
        return np.random.choice(['advance', 'review', 'retake'])
    else:
        # Exploit: best known action for this state
        state_actions = q_table[state]
        return max(state_actions, key=state_actions.get)
```

---

## Rule-Based Fallback (Early System)

Before Q-table has learned enough, use rules:

| Condition | Action |
|---|---|
| mastery ≥ 0.7 AND score ≥ 70% | advance |
| mastery < 0.7 AND attempt_count < 2 | retake |
| mastery < 0.7 AND attempt_count ≥ 2 | review |
| score < 50% | retake (if attempts < 3) else review |

**This ensures sensible behavior from the start.**

---

## When Q-Learning Runs

| Trigger | What Happens |
|---|---|
| Exercise submitted | Decision written to exercise_q_decisions |
| Activity submitted | Decision written to activity_q_decisions |

---

## What Gets Stored

Every decision writes one row to `*_q_decisions` with frozen snapshots:

| Column | Why |
|---|---|
| action | The decision made |
| mastery_at_decision | BKT value at that moment |
| study_time_seconds | Cumulative study time |
| attempt_count | Attempts for this lesson |
| session_score | Score of triggering session |
| hint_count | Cumulative hints used |
| decided_at | Timestamp |

**These snapshots cannot be reconstructed later — they are thesis receipts.**

---

## What Q-Learning Does NOT Do

| Does NOT | Why |
|---|---|
| Estimate mastery | That's BKT |
| Generate feedback | That's RAG |
| Change lesson order | Fixed sequence |
| Modify BKT values | Read-only input |
| Store scores | Sessions tables do that |

---

## Data Flow

```
Exercise submitted
  → BKT updates mastery
  → qlearning.py get_action() called
  → Action decided
  → exercise_q_decisions row written (frozen snapshots)
  → Action applied:
      advance → lesson_progress updated, next lesson unlocked
      review → lesson_progress marked needs_review, student re-reads lesson
      retake → exercise available again with hints for wrong questions
```

---

## Key Design Decisions

| Decision | Why |
|---|---|
| Pure numpy | No ML framework needed |
| Q-table as JSON | Simple, transparent, version-controllable |
| Rule-based fallback | Sensible behavior before learning |
| Frozen snapshots | Thesis receipts — unreconstructable |
| One decision per session | UNIQUE constraint on session_id |
| Separate tables for exercise/activity | Real FKs, no polymorphic design |

---

## Thesis Wording

> "Q-learning serves as the adaptive decision module. The state space is defined by mastery level (low, medium, high) and attempt count (1, 2, 3+), yielding nine discrete states. Actions are advance, review, and retake. An epsilon-greedy strategy balances exploration and exploitation, with a rule-based fallback ensuring sensible behavior during early deployment. Every decision is logged with frozen snapshots of mastery, study time, attempts, score, and hint count, providing auditable evidence of the adaptive path."