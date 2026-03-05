# Email Automation Platform

Email Automation Platform is a practical project for processing invoice-like email attachments and turning them into structured data.

The long-term goal is a convenient, reliable mailbox-processing app for daily operations.  
Although this started as a learning project, it is treated as preparation for a more serious production-grade product.

## Why this project exists

Many teams still process invoice emails manually:

- open mailbox,
- download attachments,
- validate files,
- extract invoice fields,
- pass data to internal systems.

This project automates that pipeline and provides operational visibility through API and dashboard.

## Current capabilities

1. Connect to IMAP mailbox and fetch new messages.
2. Extract attachments from emails.
3. Validate file extension and file size.
4. Store accepted files in `storage/safe`.
5. Store rejected/suspicious files in `storage/quarantine` with quarantine metadata.
6. Parse documents (PDF, Excel) and extract invoice data.
7. Save parsed payload as `*.parsed.json` near source file in safe storage.
8. Expose functionality through:

- FastAPI REST endpoints
- web dashboard (stats, recent files, quarantine list)
- background tasks with Celery

## Dashboard and API highlights

- View recent safe files and quarantine files in dashboard.
- Open parsed JSON for a specific safe file.
- Quarantine API now hides internal `*.quarantine_info.json` sidecar files from list totals.
- Quarantine delete removes both payload file and its sidecar metadata file.

![Dashboard](docs/images/Screenshot%202026-03-05%20at%2010.31.18.png)

## Security

✅ **Secret rotation completed**: All credentials have been rotated after SECURITY_WARNING incident  
✅ **Pre-commit hooks**: Gitleaks + TruffleHog for secret detection  
✅ **File safety**: Quarantine system protects against malicious attachments  
✅ **CI/CD security**: Automated safety and bandit scans

## Tech stack

- Python 3.12+ (tested locally with Python 3.13)
- FastAPI
- Celery + Redis
- SQLite (current stage)
- Jinja2 templates
- Pydantic Settings (`.env`-driven config)
- Pytest + Ruff

## Project structure

- `src/automation/main.py` - FastAPI app factory
- `src/automation/api/endpoints/` - API endpoints (`emails`, `files`, `system`)
- `src/automation/web/interface.py` - dashboard/web routes
- `src/automation/app/use_cases.py` - application business logic
- `src/automation/adapters/` - IMAP, parsers, storage, repository adapters
- `src/automation/tasks/` - Celery background jobs
- `src/automation/tests/` - automated tests

## Local development

```bash
# 1) Install dependencies
pip install -e ".[dev]"

# 2) Configure environment
cp .env.example .env
# fill IMAP credentials and other settings

# 3) Run API
python run.py

# 4) (optional) run workers
celery -A automation.celery_app worker --loglevel=info
celery -A automation.celery_app beat --loglevel=info
```

API docs:

- `http://localhost:8000/docs`
- `http://localhost:8000/redoc`

## Docker

```bash
docker compose up -d --build
```

Current `docker-compose.yml` is configured so the `automation-platform` service installs dev dependencies on startup, which allows running tests inside the container:

```bash
docker compose exec automation-platform python -m pytest
```

## Tests and quality checks

```bash
pytest -q
ruff check src
```

The test suite currently covers:

- core use cases
- SQLite repository behavior
- key file/system/email API endpoint behavior
- Shopify PDF parser regression scenarios
- path traversal protection for quarantine operations

## Current maturity

This is an actively evolving portfolio project with a working core pipeline, not a finished product.

Strong points:

- clear modular architecture (ports/adapters + use cases)
- usable API and dashboard
- quarantine and parsed-data visibility
- growing automated test coverage

Current limitations:

- parser accuracy still depends on document layout variance
- operational flows and monitoring are still being hardened
- production deployment/security/observability are not finalized yet

## Roadmap direction

- improve parsing accuracy for real-world invoice formats
- expand integration tests and end-to-end test scenarios
- improve dashboard UX for operational triage
- strengthen retry/error handling and observability
- prepare external integrations (ERP/CRM/accounting APIs)
