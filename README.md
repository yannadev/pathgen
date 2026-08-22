# Pathgen

Adaptive learning for Grade 7 Philippine DepEd mathematics, built with Django.

## Local setup

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python manage.py check
python manage.py runserver
```

Phase 1 provides the project shell and nine Django apps. Models and migrations are
introduced in Phase 2 so the custom user model can be configured before the first
database migration.

See `docs/17_Build_Order.md` for the implementation sequence.
