# # 02 — Tech Stack

---

## Stack Overview

| Layer | Technology | Version | Purpose |
|---|---|---|---|
| Backend framework | Django | 5.0+ | Web framework — templates, auth, ORM, admin |
| Database driver | psycopg | 3.1+ | PostgreSQL adapter for Django |
| DB URL parser | dj-database-url | 2.1+ | Parses DATABASE_URL env var |
| Env management | django-environ | 0.11+ | Reads .env file |
| Static files | whitenoise | 6.6+ | Serves static files in production |
| Server | gunicorn | 22.0+ | WSGI server for Railway |
| ML math | numpy | 1.26+ | BKT + Q-learning + cosine similarity |
| AI inference | groq | 0.9+ | Groq API client for feedback generation |
| Embeddings | openai | 1.30+ | OpenAI API client for embeddings |

---

## What Each Dependency Does

### Django 5.0+

**Role:** The backbone. Routing, templates, ORM, auth, sessions, admin.

**Used in:**
- All 9 apps (accounts, curriculum, progress, assessment, practice, adaptive, feedback, monitoring, core)
- Django templates for all pages
- Session auth + custom role decorators
- Django admin (restricted, content read-only)

---

### psycopg[binary] 3.1+

**Role:** Django's PostgreSQL adapter.

**Why PostgreSQL:**
- JSONB columns for flexible content
- ENUM types for roles, statuses, actions
- CHECK constraints for data validation
- ON DELETE RESTRICT for research data protection
- gen_random_uuid() for UUID PKs

---

### dj-database-url 2.1+

**Role:** Parses Railway's DATABASE_URL env var into Django config.

**Code:**
```python
DATABASES = {
    'default': dj_database_url.config(conn_max_age=600)
}

---

### django-environ 0.11+

**Role:** Manages environment variables. Reads .env locally, real env vars on Railway.

**Code:**
```python
import environ
env = environ.Env()
environ.Env.read_env()

SECRET_KEY = env('SECRET_KEY')
DEBUG = env.bool('DEBUG', default=False)
```

---

### whitenoise 6.6+

**Role:** Serves static files directly from Django in production. No nginx needed.

---

### gunicorn 22.0+

**Role:** Production WSGI server. Runs Django on Railway.

**Procfile:**
```
web: gunicorn config.wsgi
```

---

### numpy 1.26+

**Role:** The ONLY ML dependency. BKT, Q-learning, and cosine similarity.

**Why not scikit-learn/tensorflow:** BKT is a simple Bayesian update. Q-learning is a small table. numpy is all you need.

---

### groq 0.9+

**Role:** Fast LLM inference for feedback generation.

**Model:** gpt-oss-120b

**Used in:** feedback/generator.py

**Code:**
```python
from groq import Groq

client = Groq(api_key=settings.GROQ_API_KEY)

response = client.chat.completions.create(
    model="gpt-oss-120b",
    temperature=0.2,
    messages=[
        {"role": "system", "content": "You are a Grade 7 math tutor..."},
        {"role": "user", "content": prompt}
    ]
)
```

**Why Groq:** Fast, cheap, good enough for 3-5 sentence feedback.

---

### openai 1.30+

**Role:** Embeddings only. NOT generation.

**Model:** text-embedding-3-small

**Used in:** feedback/clients.py and build_rag_index command

**Code:**
```python
from openai import OpenAI

client = OpenAI(api_key=settings.OPENAI_API_KEY)

response = client.embeddings.create(
    model="text-embedding-3-small",
    input=text
)

embedding = response.data[0].embedding  # 1536-dim vector
```

**Why OpenAI embeddings:** Cheap, high-quality, exactly 1536 dimensions.

---

## How They Work Together

### Request Flow: Student Submits Exercise

```
1. Browser → POST /practice/exercise/<id>/submit
2. gunicorn receives request → Django view
3. Django ORM → psycopg → PostgreSQL (grade responses, write session)
4. numpy (BKT update) → psycopg → PostgreSQL (write bkt_mastery)
5. numpy (Q-learning decision) → psycopg → PostgreSQL (write q_decision)
6. openai (embed query) → JSON file (retrieve top 4 chunks)
7. groq (generate feedback from chunks)
8. psycopg → PostgreSQL (save ai_feedback)
9. Django template renders result page
10. whitenoise serves static files (JS/CSS)
```

---

## External Services

| Service | Called When | Purpose |
|---|---|---|
| PostgreSQL (Railway) | Every request | All data persistence |
| OpenAI | Seed time + session completion | Embed chunks and queries |
| Groq | Session completion | Generate feedback text |

---

## Dependencies NOT Needed

| Not Included | Why |
|---|---|
| Django REST Framework | No API — server-rendered templates |
| Celery / Redis | No background tasks — synchronous |
| React / Vue / Alpine | Vanilla JS only (3 files) |
| Tailwind CLI / Node | Tailwind via CDN |
| scikit-learn | BKT + Q-learning simple enough for numpy |
| JWT | Django session auth is enough |
| Pillow | No image processing |
| LangChain | Custom RAG pipeline is simpler and more transparent |
| Qdrant | JSON file storage is sufficient for scale |

---

## requirements.txt

```
Django>=5.0,<6
psycopg[binary]>=3.1
dj-database-url>=2.1
django-environ>=0.11
whitenoise>=6.6
gunicorn>=22.0
numpy>=1.26
groq>=0.9
openai>=1.30
```

---

## .env.example

```
SECRET_KEY=
DEBUG=True
DATABASE_URL=
ALLOWED_HOSTS=localhost,127.0.0.1
GROQ_API_KEY=
GROQ_MODEL=gpt-oss-120b
OPENAI_API_KEY=
EMBEDDING_MODEL=text-embedding-3-small
```

---

## Frontend Stack

| Layer | Technology | Purpose |
|---|---|---|
| HTML | Django templates | Server-rendered pages |
| CSS | Tailwind CSS (CDN) | Styling |
| Font | Geist | Typography |
| Icons | Iconsax | Icon set |
| JS | Vanilla JavaScript (3 files) | Heartbeat, timer, video checkpoints |

No build step. No Node. No bundler.

---

## Summary

| Resource | Count |
|---|---|
| Python dependencies | 9 |
| External services | 3 (Railway, OpenAI, Groq) |
| JS files | 3 |
| Apps | 9 |
| Tables | 23 |
