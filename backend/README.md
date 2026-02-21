# Tow'd You So — Backend

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

## Database migrations

Migrations are managed with [Alembic](https://alembic.sqlalchemy.org/). The database URL is read from `DATABASE_URL` in your `.env` file.

**Apply all migrations** (create/update tables):

```bash
alembic upgrade head
```

**Create a new migration** after changing models in `db/models.py`:

```bash
alembic revision --autogenerate -m "describe your change"
```

**View current migration status:**

```bash
alembic current
```

**Downgrade one revision:**

```bash
alembic downgrade -1
```

## Running the server

```bash
uvicorn main:app --reload
```

## Running tests

Tests use an in-memory SQLite database — no PostgreSQL required.

```bash
python -m pytest tests/
```

With verbose output:

```bash
python -m pytest tests/ -v
```
