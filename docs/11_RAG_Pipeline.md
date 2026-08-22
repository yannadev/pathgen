# 11 — RAG Pipeline

---

## What RAG Is

Retrieval-Augmented Generation — generates feedback grounded in actual lesson content.

**Output:** 3-5 sentences of feedback based on what the student got wrong.

**Role:** Feedback generation ONLY. Never estimates mastery. Never decides actions.

---

## Where RAG Lives

```
feedback/
├── chunker.py              # structure-aware chunking (300-500 tokens)
├── clients.py              # openai + groq clients
├── prompts.py              # prompt templates
├── retriever.py            # load JSON → embed query → cosine similarity → top 4
├── generator.py            # prompt → groq → feedback text
├── management/
│   └── commands/
│       └── build_rag_index.py  # chunk → embed → write JSON file
└── tests/
    └── __init__.py
```


---

## Two Phases

### Phase 1: Seed Time (Run Once)

```bash
python manage.py build_rag_index
```


### Phase 2: Runtime (Per Session Completion)

Triggered by orchestrator after exercise/activity submission.

---

## Phase 1 — Seed Time (5 Steps)

### Step 1: Read Lesson Content

- Read `seed_data/lessons.json`
- Extract `content_jsonb` from each lesson

### Step 2: Chunk the Content

- Walk through blocks in order
- Accumulate into chunks of 300-500 tokens
- Never split a worked example
- Break at natural boundaries (headings, end of examples)

### Step 3: Attach Metadata

Every chunk gets:
- `id` — "{lesson_slug}:{chunk_index}"
- `lesson_id`
- `lesson_slug`
- `chunk_index`
- `chunk_text`

### Step 4: Embed the Chunks

- Call OpenAI `text-embedding-3-small`
- Each chunk becomes a 1536-dimensional vector

### Step 5: Save to JSON

- Write everything to `seed_data/lesson_embeddings.json`

---

## Phase 2 — Runtime (8 Steps)

### Step 1: Student Submits Session

- Exercise or activity session submitted
- Responses graded
- Session row written

### Step 2: Build Query

- Collect all wrong items:
  - `question_text`
  - `hint_text`
- Concatenate into one query string

**Special case:** If everything correct → skip retrieval, prompt Groq for short praise.

### Step 3: Embed Query

- Call OpenAI `text-embedding-3-small` on query string
- Get 1536-dimensional vector

### Step 4: Retrieve Top 4 Chunks

- Load `lesson_embeddings.json`
- Filter by `lesson_id` (the session's lesson or lessons)
- Compute cosine similarity with numpy
- Get top 4 most similar chunks

### Step 5: Build Prompt

- Role: "You are a Grade 7 math tutor for Philippine DepEd learners."
- Session result: score/total
- Wrong items: question → student chose X / correct was Y
- Retrieved chunks: "Use ONLY these excerpts — do not invent content."
- Instruction: Generalized summary + error pattern + specific concepts. Encouraging. No per-item listing.

### Step 6: Generate with Groq

- Call Groq `gpt-oss-120b`
- Temperature: 0.2
- Get 3-5 sentences

### Step 7: Store Feedback

- Save to `exercise_sessions.ai_feedback` or `activity_sessions.ai_feedback`
- If any step fails → NULL

### Step 8: Display on Result Page

- Result page shows: score, AI feedback, next action

---

## Chunking Logic

```python
# feedback/chunker.py

def chunk_content(content_jsonb):
    """
    Split lesson content into chunks of 300-500 tokens.
    Structure-aware: breaks at headings, never splits examples.
    """
    chunks = []
    current_chunk = []
    current_tokens = 0
    MAX_TOKENS = 500
    MIN_TOKENS = 300
    
    for block in content_jsonb:
        block_text = block.get('text', '')
        block_type = block.get('type', 'paragraph')
        block_tokens = estimate_tokens(block_text)
        
        # Break if adding this block exceeds max and we have enough
        if current_tokens + block_tokens > MAX_TOKENS and current_tokens >= MIN_TOKENS:
            chunks.append(" ".join(current_chunk))
            current_chunk = []
            current_tokens = 0
        
        # Never split a worked example
        if block_type == 'example' and block_tokens > MAX_TOKENS:
            if current_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk = []
                current_tokens = 0
            chunks.append(block_text)
            continue
        
        current_chunk.append(block_text)
        current_tokens += block_tokens
    
    if current_chunk:
        chunks.append(" ".join(current_chunk))
    
    return chunks


def estimate_tokens(text):
    """Rough estimate: 1 token ≈ 4 characters."""
    return len(text) // 4
```


---

## Embedding Logic

```python
# feedback/clients.py

from openai import OpenAI
from groq import Groq
from django.conf import settings

openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
groq_client = Groq(api_key=settings.GROQ_API_KEY)

def embed(text):
    """Convert text to 1536-dimensional vector."""
    response = openai_client.embeddings.create(
        model=settings.EMBEDDING_MODEL,
        input=text
    )
    return response.data[0].embedding
```


---

## Retrieval Logic

```python
# feedback/retriever.py

import json
import numpy as np

def retrieve(session_lesson_ids, wrong_questions):
    """Retrieve top 4 chunks for the session's lesson(s)."""
    
    # Load embeddings
    with open('seed_data/lesson_embeddings.json') as f:
        all_chunks = json.load(f)
    
    # Filter by lesson
    relevant_chunks = [
        chunk for chunk in all_chunks
        if chunk['lesson_id'] in session_lesson_ids
    ]
    
    # Build query from wrong items
    query_text = " ".join(
        q['question_text'] + " " + q['hint_text']
        for q in wrong_questions
    )
    
    # Embed query
    query_vector = embed(query_text)
    
    # Cosine similarity
    def cosine_sim(a, b):
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
    
    scored = [
        (cosine_sim(query_vector, chunk['vector']), chunk)
        for chunk in relevant_chunks
    ]
    
    top_4 = sorted(scored, key=lambda x: x[0], reverse=True)[:4]
    
    return [chunk for _, chunk in top_4]
```


---

## Generation Logic

```python
# feedback/generator.py

def generate_feedback(session_result, wrong_items, retrieved_chunks):
    """Generate 3-5 sentence feedback using Groq."""
    
    prompt = build_prompt(session_result, wrong_items, retrieved_chunks)
    
    response = groq_client.chat.completions.create(
        model=settings.GROQ_MODEL,
        temperature=0.2,
        messages=[
            {"role": "system", "content": "You are a Grade 7 math tutor for Philippine DepEd learners."},
            {"role": "user", "content": prompt}
        ]
    )
    
    return response.choices[0].message.content
```


---

## Key Design Decisions

| Decision | Why |
|---|---|
| Custom pipeline, no LangChain | Full transparency, simpler, easier to defend |
| Structure-aware chunking | Never split worked examples, preserve context |
| 300-500 token chunks | Specific enough, large enough |
| Metadata filter by lesson | Retrieval only from what student just studied |
| Top 4 chunks | Enough context without noise |
| Query from wrong items only | Targets misconceptions directly |
| Temperature 0.2 | Consistent, focused feedback |
| NULL on failure | Honest data, graceful degradation |
| Same embedding model for chunks and queries | Valid similarity comparison |
| JSON storage | No vector DB needed for this scale |


---

## Thesis Wording

> "The feedback module implements canonical dense-retrieval RAG (Lewis et al., 2020). Lesson content is chunked with structure-aware segmentation, embedded using OpenAI's text-embedding-3-small, and stored as a JSON artifact within the system repository. At runtime, the query is constructed from the student's incorrect responses, embedded with the same model, and retrieved with lesson-scoped metadata filtering. The top-4 retrieved chunks constrain a Groq language model to generate feedback grounded exclusively in the studied content."