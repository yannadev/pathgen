# 15 — Seed Data

---

## Overview

Content is loaded from JSON files in `seed_data/`. Three management commands handle content lifecycle.

---

## Management Commands

| Command | Purpose |
|---|---|
| `python manage.py seed_content` | Load/update content from JSON files into PostgreSQL |
| `python manage.py reset_content` | Wipe content tables (for demo → real content swap) |
| `python manage.py build_rag_index` | Chunk lessons → embed → write lesson_embeddings.json |

---

## JSON File Structures

### lessons.json

```json
[
  {
    "slug": "lesson-1-integers",
    "title": "Integers",
    "description": "Introduction to integers and operations",
    "order_index": 1,
    "prerequisite_lesson_id": null,
    "content_jsonb": [
      {
        "type": "heading",
        "text": "What are Integers?"
      },
      {
        "type": "paragraph",
        "text": "Integers are whole numbers that can be positive, negative, or zero."
      },
      {
        "type": "example",
        "text": "Examples: -5, -3, 0, 2, 7"
      },
      {
        "type": "heading",
        "text": "Adding Integers"
      },
      {
        "type": "paragraph",
        "text": "When adding two positive integers, add their absolute values and keep the positive sign."
      },
      {
        "type": "example",
        "text": "3 + 5 = 8"
      }
    ]
  },
  {
    "slug": "lesson-2-fractions",
    "title": "Fractions",
    "description": "Understanding fractions and operations",
    "order_index": 2,
    "prerequisite_lesson_id": null,
    "content_jsonb": [
      {
        "type": "heading",
        "text": "What is a Fraction?"
      },
      {
        "type": "paragraph",
        "text": "A fraction represents a part of a whole."
      }
    ]
  }
]
```

**Key:** `slug` is the idempotent key. `order_index` enforces sequence. `prerequisite_lesson_id` references previous lesson (null for first).

---

### assessment_questions.json

```json
[
  {
    "lesson_id": "uuid-of-lesson-1",
    "question_text": "What is the sum of -5 and 8?",
    "options_jsonb": ["-13", "-3", "3", "13"],
    "correct_answer_index": 2,
    "has_image": false,
    "image_url": null
  },
  {
    "lesson_id": "uuid-of-lesson-1",
    "question_text": "Which is the correct answer based on the number line?",
    "options_jsonb": ["-4", "-2", "2", "4"],
    "correct_answer_index": 3,
    "has_image": true,
    "image_url": "[https://storage.example.com/number-line.png](https://storage.example.com/number-line.png)"
  }
]
```

**Key:** Same bank used for BOTH pretest and posttest. `lesson_id` maps to lesson for BKT initialization.

---

### exercise_questions.json

```json
[
  {
    "lesson_id": "uuid-of-lesson-1",
    "question_text": "What is -7 + 4?",
    "options_jsonb": ["-11", "-3", "3", "11"],
    "correct_answer_index": 1,
    "hint_text": "When adding a negative and positive number, subtract the smaller absolute value from the larger and keep the sign of the larger."
  },
  {
    "lesson_id": "uuid-of-lesson-1",
    "question_text": "What is -2 - (-5)?",
    "options_jsonb": ["-7", "-3", "3", "7"],
    "correct_answer_index": 2,
    "hint_text": "Subtracting a negative is the same as adding its opposite: -2 + 5."
  }
]
```

**Key:** Text-only MCQ bank per lesson. `hint_text` shown on retake for wrong questions.

---

### activities.json

```json
[
  {
    "title": "Integers and Fractions Activity",
    "description": "Mixed practice covering lessons 1 and 2",
    "order_index": 1,
    "lesson_id_1": "uuid-of-lesson-1",
    "lesson_id_2": "uuid-of-lesson-2"
  }
]
```

**Key:** Always covers two consecutive lessons. `order_index` fixes sequence.

---

### activity_questions.json

```json
[
  {
    "activity_id": "uuid-of-activity-1",
    "question_text": "What is the result of 1/2 + 1/4?",
    "options_jsonb": ["1/6", "2/6", "3/4", "1/8"],
    "correct_answer_index": 2,
    "media_jsonb": null,
    "order_index": 1,
    "hint_text": "Find the least common denominator first."
  },
  {
    "activity_id": "uuid-of-activity-1",
    "question_text": "Watch the video and answer: What is the sum of the two integers shown?",
    "options_jsonb": ["-5", "-1", "1", "5"],
    "correct_answer_index": 1,
    "media_jsonb": {
      "type": "video",
      "url": "[https://storage.example.com/integers-video.mp4](https://storage.example.com/integers-video.mp4)",
      "checkpoint_seconds": 45
    },
    "order_index": 2,
    "hint_text": "Pay attention to the signs of the integers."
  }
]
```

**Key:** `media_jsonb` is NULL for text-only, has type for image/video. `order_index` controls video checkpoint sequence.

---

### lesson_embeddings.json (Generated)

```json
[
  {
    "id": "lesson-1-integers:0",
    "lesson_id": "uuid-of-lesson-1",
    "lesson_slug": "lesson-1-integers",
    "chunk_index": 0,
    "chunk_text": "What are Integers? Integers are whole numbers that can be positive, negative, or zero...",
    "vector": [0.023, -0.112, 0.874, ...]
  },
  {
    "id": "lesson-1-integers:1",
    "lesson_id": "uuid-of-lesson-1",
    "lesson_slug": "lesson-1-integers",
    "chunk_index": 1,
    "chunk_text": "Adding Integers. When adding two positive integers...",
    "vector": [-0.045, 0.238, 0.671, ...]
  }
]
```

**Key:** Generated by `build_rag_index`. Never manually edited. Delete and regenerate when lessons change.

---

## Seed Command Logic

### seed_content.py

```python
from django.core.management.base import BaseCommand
import json

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        # Load lessons
        with open('seed_data/lessons.json') as f:
            lessons = json.load(f)
        
        for lesson in lessons:
            Lesson.objects.update_or_create(
                slug=lesson['slug'],
                defaults={
                    'title': lesson['title'],
                    'description': lesson.get('description'),
                    'order_index': lesson['order_index'],
                    'prerequisite_lesson_id': lesson.get('prerequisite_lesson_id'),
                    'content_jsonb': lesson['content_jsonb']
                }
            )
        
        # Repeat for assessment_questions, exercise_questions, activities, activity_questions
        # Using update_or_create with appropriate keys
```

---

## Reset Command Logic

### reset_content.py

```python
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        # Delete in order (children first)
        AssessmentQuestion.objects.all().delete()
        ExerciseQuestion.objects.all().delete()
        ActivityQuestion.objects.all().delete()
        Activity.objects.all().delete()
        Lesson.objects.all().delete()
        
        self.stdout.write("Content wiped.")
```

**Warning:** Only works if no student data references content (FK RESTRICT will block deletion).

---

## Build RAG Index Logic

### build_rag_index.py

```python
from django.core.management.base import BaseCommand
import json

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        with open('seed_data/lessons.json') as f:
            lessons = json.load(f)
        
        embeddings = []
        for lesson in lessons:
            chunks = chunk_content(lesson['content_jsonb'])
            for idx, chunk_text in enumerate(chunks):
                vector = embed(chunk_text)
                embeddings.append({
                    'id': f"{lesson['slug']}:{idx}",
                    'lesson_id': lesson['id'],
                    'lesson_slug': lesson['slug'],
                    'chunk_index': idx,
                    'chunk_text': chunk_text,
                    'vector': vector
                })
        
        with open('seed_data/lesson_embeddings.json', 'w') as f:
            json.dump(embeddings, f)
        
        self.stdout.write(f"Built {len(embeddings)} embeddings.")
```

---

## Demo Content Strategy

### During Development

1. Create demo lessons.json with 2-3 fake lessons
2. Create demo questions for each type
3. Test the full system

### Before Real Study

1. Wipe database (`python manage.py flush`)
2. Replace seed_data with real content
3. Run `seed_content`
4. Run `build_rag_index`
5. Create real accounts
6. Begin data collection

---

## Content Types Supported

| Block Type    | Used In                            | Example          |
| ------------- | ---------------------------------- | ---------------- |
| heading       | lessons                            | Section title    |
| paragraph     | lessons                            | Explanation text |
| example       | lessons                            | Worked example   |
| image         | lessons, activities                | Visual aid       |
| video         | activities                         | With checkpoint  |
| text question | exercises, activities, assessments | MCQ only         |