# Email Automation Platform

A practical application for processing incoming emails with attachments and turning inbox noise into structured, usable data.

## Why this project exists

Many workflows have the same pain point: invoices, reports, and operational documents arrive by email and must be reviewed, saved, sorted, and entered manually into internal systems.

This project addresses that flow end-to-end:
- connects to an IMAP mailbox,
- extracts attachments,
- stores files safely,
- parses invoice-like data from documents,
- exposes everything through an API and web interface.

## What it can do today

At its current stage, the platform already supports a full baseline processing pipeline:

1. Connects to a mailbox via IMAP.
2. Fetches new emails and extracts attachments.
3. Validates file types and size limits.
4. Stores safe files in `safe` storage and suspicious files in `quarantine`.
5. Parses PDF/Excel files and extracts invoice fields.
6. Provides:
   - REST API (FastAPI),
   - web dashboard (status, files, logs, settings),
   - background scheduling with Celery.

## What it should do next

The goal is to grow this into a genuinely convenient email-processing application, not just a demo.

Near-term product direction:
- higher parsing accuracy across more document layouts,
- stronger duplicate/error handling,
- more robust processing orchestration (queues, retries, monitoring),
- better operator UX in the dashboard,
- richer analytics and observability,
- integrations with external systems (ERP/CRM/accounting).

## Important context

Even though this is currently a learning project, I treat it as preparation for a more serious product.

It is meant to be a practical foundation:
- to validate architecture decisions,
- to test real workflow assumptions,
- and to evolve step by step toward a production-grade solution.

## Tech stack

- Python + FastAPI
- Celery (background tasks)
- Redis (queue/broker)
- SQLite (current stage)
- Jinja2 templates (web UI)

## Quick start

```bash
# 1) Install
pip install -e .

# 2) Configure environment
cp .env.example .env
# fill in IMAP settings

# 3) Start API
python run.py

# 4) (optional) start background workers
celery -A automation.celery_app worker --loglevel=info
celery -A automation.celery_app beat --loglevel=info
```

API docs after startup:
- `http://localhost:8000/docs`
- `http://localhost:8000/redoc`

## Current status

The project is under active development. The architectural foundation and core processing flow are already in place; the next focus is parsing quality and UX polish so it becomes a useful day-to-day tool.
