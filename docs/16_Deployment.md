# 16 — Deployment

---

## Overview

Deploy to Railway. One service (Django). PostgreSQL provided by Railway. No Docker. No separate vector DB.

---

## Railway Setup

### Services

| Service | What It Is |
|---|---|
| Django app | Deployed from GitHub repo |
| PostgreSQL | Railway plugin |

**No Qdrant. No extra services.**

---

## Required Files

### Procfile

```
web: gunicorn config.wsgi
```

### runtime.txt

```
python-3.12
```

### .gitignore

```
.env
venv/
__pycache__/
*.pyc
db.sqlite3
staticfiles/
qdrant_storage/
seed_data/lesson_embeddings.json
```

---

## Environment Variables (Railway)

| Variable | Value |
|---|---|
| SECRET_KEY | Random string (generate once) |
| DEBUG | False |
| DATABASE_URL | Auto-provided by Railway PostgreSQL |
| ALLOWED_HOSTS | your-app.up.railway.app |
| GROQ_API_KEY | From Groq console |
| GROQ_MODEL | gpt-oss-120b |
| OPENAI_API_KEY | From OpenAI platform |
| EMBEDDING_MODEL | text-embedding-3-small |

---

## Deploy Steps

### 1. Push to GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git push origin main
```

### 2. Create Railway Project

- Go to railway.app
- New Project
- Deploy from GitHub
- Select your repo

### 3. Add PostgreSQL

- Railway dashboard → New → Database → PostgreSQL
- Railway auto-provides DATABASE_URL

### 4. Set Environment Variables

- Add all variables from table above
- Railway injects them into your app

### 5. Run Migrations

```bash
# Railway CLI or dashboard shell
python manage.py migrate
```

### 6. Seed Content

```bash
python manage.py seed_content
```

### 7. Build RAG Index

```bash
python manage.py build_rag_index
```

### 8. Collect Static

```bash
python manage.py collectstatic --noinput
```

### 9. Create Admin Account

```bash
python manage.py createsuperuser
```

### 10. Smoke Test

- Visit your-app.up.railway.app
- Login page loads
- Create test teacher + student
- Student takes pretest
- Exercise triggers adaptive decisions
- Feedback appears on result page

---

## Railway Settings

### Region

- Singapore (low latency for PH users)

### Resources

| Service | Plan |
|---|---|
| Django app | Free tier / hobby |
| PostgreSQL | Free tier / hobby |

---

## Production Settings

```python
# settings.py (production)

DEBUG = env.bool('DEBUG', default=False)
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS')

DATABASES = {
    'default': dj_database_url.config(conn_max_age=600)
}

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    # ... rest
]
```

---

## Deployment Checklist

| # | Step | Done? |
|---|---|---|
| 1 | GitHub repo pushed | ☐ |
| 2 | Railway project created | ☐ |
| 3 | PostgreSQL added | ☐ |
| 4 | Env vars set | ☐ |
| 5 | Migrations run | ☐ |
| 6 | Content seeded | ☐ |
| 7 | RAG index built | ☐ |
| 8 | Static collected | ☐ |
| 9 | Admin account created | ☐ |
| 10 | Smoke test passed | ☐ |

---

## Useful Commands

```bash
# Local development
python manage.py runserver

# Migrations
python manage.py makemigrations
python manage.py migrate

# Content
python manage.py seed_content
python manage.py reset_content

# RAG
python manage.py build_rag_index

# Static
python manage.py collectstatic --noinput

# Admin
python manage.py createsuperuser

# Tests
python manage.py test
```

---

## Rollback / Reset

```bash
# Wipe everything and start fresh
python manage.py flush
python manage.py migrate
python manage.py seed_content
python manage.py build_rag_index
python manage.py createsuperuser
```

---

## Troubleshooting

| Issue                     | Fix                                            |
| ------------------------- | ---------------------------------------------- |
| Static files not loading  | Run collectstatic, check whitenoise middleware |
| Database connection fails | Check DATABASE_URL in Railway                  |
| OpenAI API fails          | Check OPENAI_API_KEY, credits loaded           |
| Groq API fails            | Check GROQ_API_KEY, free tier limits           |
| Embeddings file missing   | Run build_rag_index                            |
| Content missing           | Run seed_content                               |