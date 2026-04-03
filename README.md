# Email Automation Platform

Email Automation Platform processes invoice-like email attachments and turns them into structured data.

The project combines:
- IMAP mailbox ingestion
- secure attachment validation and quarantine
- invoice parsing for several document formats
- FastAPI API and HTML dashboard
- background processing with Celery

## Current capabilities

1. Connect to an IMAP mailbox and fetch new messages.
2. Extract attachments from emails.
3. Validate extension, MIME type, file size, and suspicious content.
4. Store accepted files in `storage/safe`.
5. Store rejected or suspicious files in `storage/quarantine` with sidecar metadata.
6. Parse supported documents and save extracted payload as `*.parsed.json`.
7. Expose operational visibility through REST API and web dashboard.
8. Track processing state in PostgreSQL with SQLAlchemy and Alembic.
9. Retry failed items through background tasks.

## Tech stack

- Python 3.12+
- FastAPI
- Jinja2 templates
- Celery + Redis
- PostgreSQL
- SQLAlchemy + Alembic
- Pydantic Settings
- Pytest + Ruff
- Docker Compose

## Project structure

- `src/automation/main.py` - FastAPI app factory
- `src/automation/api/endpoints/` - REST API endpoints
- `src/automation/web/interface.py` - HTML dashboard routes
- `src/automation/app/use_cases.py` - core business orchestration
- `src/automation/adapters/` - IMAP, parsers, storage, repository adapters
- `src/automation/db/` - SQLAlchemy models and engine/session helpers
- `src/automation/tasks/` - Celery background tasks
- `src/automation/tests/` - automated test suite
- `alembic/` - database migrations

## Local development

### 1. Create and activate virtual environment

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -e ".[dev]"
```

### 3. Configure environment

```bash
cp .env.example .env
```

Required notes:
- set real IMAP credentials in `.env`
- use `DATABASE_URL=...`, not `sqlalchemy.url=...`
- `DEBUG` must be a boolean-like value such as `true` or `false`

### 4. Start infrastructure

```bash
docker compose up -d database redis
```

### 5. Apply database schema

If your current shell exports an incompatible `DEBUG` value, run Alembic with `env -u DEBUG`:

```bash
source .venv/bin/activate
env -u DEBUG alembic upgrade head
```

### 6. Run the API locally

```bash
source .venv/bin/activate
env -u DEBUG python run.py
```

Optional workers:

```bash
source .venv/bin/activate
env -u DEBUG celery -A automation.celery_app worker --loglevel=info
env -u DEBUG celery -A automation.celery_app beat --loglevel=info
```

Docs:
- `http://localhost:8000/docs`
- `http://localhost:8000/redoc`

## Docker workflow

The `automation-platform` service is built with development dependencies, so tests can run inside Docker without manual `pip install`.

### Start full stack

```bash
docker compose up -d --build automation-platform celery-worker celery-beat nginx
```

If DB and Redis are not running yet:

```bash
docker compose up -d database redis
docker compose up -d --build automation-platform celery-worker celery-beat nginx
```

### Apply migrations in Docker

```bash
docker compose exec automation-platform alembic upgrade head
```

### Run tests in Docker

```bash
docker compose exec automation-platform python -m pytest -q
```

## Mailbox processing

By default the application fetches `UNSEEN` emails and does not mark messages as read just by inspecting them.

To trigger processing through the API:

```bash
curl -X POST http://localhost:8000/api/v1/emails/process \
  -H 'Content-Type: application/json' \
  -d '{"force_reprocess": false, "dry_run": false}'
```

To re-scan the whole mailbox:

```bash
curl -X POST http://localhost:8000/api/v1/emails/process \
  -H 'Content-Type: application/json' \
  -d '{"force_reprocess": true, "dry_run": false}'
```

## Resetting the environment

Full reset for a fresh mailbox run:

```bash
unset DEBUG
docker compose down -v
find storage/safe -mindepth 1 -delete
find storage/quarantine -mindepth 1 -delete
find logs -mindepth 1 -delete
docker compose up -d database redis
source .venv/bin/activate
env -u DEBUG alembic upgrade head
```

This removes:
- PostgreSQL data
- Redis data
- stored safe files
- quarantined files and sidecars
- application logs

## Database and migrations

Useful commands:

```bash
alembic upgrade head
alembic current
alembic history
alembic revision --autogenerate -m "describe change"
```

## Tests and quality checks

Run locally:

```bash
source .venv/bin/activate
env -u DEBUG pytest --cov=automation --cov-report=term-missing -q
ruff check src
```

Run in Docker:

```bash
docker compose exec automation-platform python -m pytest --cov=automation --cov-report=term-missing -q
```

Current state of the suite:
- `178 passed, 3 skipped`
- overall coverage: `85%`

The suite covers:
- use cases and processing orchestration
- IMAP adapter behavior
- storage and quarantine logic
- SQLAlchemy and SQLite repositories
- Celery task behavior
- API and web routes
- key document parsers and parser regressions

Manual IMAP diagnostics are excluded from the default suite and only run when explicitly enabled:

```bash
RUN_IMAP_TESTS=1 pytest -q src/automation/tests/test_imap.py src/automation/tests/test_emails.py
```

## Dashboard and API highlights

- dashboard shows safe files, quarantine files, logs, and config summary
- parsed JSON can be requested for a specific safe file
- quarantine list hides internal `*.quarantine_info.json` sidecars from totals
- deleting a quarantine file also deletes its sidecar metadata file

## Current maturity

This is an actively evolving project with a solid working core, not a finished production product.

Strong points:
- modular architecture with clear ports/adapters split
- operational API and dashboard
- strong regression coverage on the critical processing path
- quarantine and parsed-data visibility
- background retry and cleanup flows

Current limitations:
- parser accuracy still depends on document layout variance
- some secondary modules still have lower coverage than the core path
- production deployment and observability are not yet finalized

## Roadmap direction

- improve parser accuracy for more invoice layouts
- expand parser coverage for remaining vendor-specific formats
- improve dashboard UX for operational triage
- strengthen observability and alerting
- prepare downstream ERP/CRM/accounting integrations
