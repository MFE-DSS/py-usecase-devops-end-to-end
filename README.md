# Risk Metrics Service

Microservice Django REST exposant la **Tracking Error 12M** pour des fonds suivis en multi-management.

## Quick start (local, SQLite)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python manage.py migrate
python manage.py runserver
```

Open http://localhost:8000/health/ → `{"status":"ok"}`.

## Project layout

See [docs/revision/03_architecture.md](docs/revision/03_architecture.md).

## Studying for interview

Start with [docs/revision/00_index.md](docs/revision/00_index.md).
