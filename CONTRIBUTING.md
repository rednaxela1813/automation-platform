# Contributing

Thanks for contributing to Email Automation Platform.

## Development Setup
```bash
git clone <repo-url>
cd automation-platform
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

## Run locally
```bash
python run.py
celery -A automation.celery_app worker --loglevel=info
celery -A automation.celery_app beat --loglevel=info
```

## Branching
- `main`: stable production branch
- `develop`: main development branch
- `feature/*`: new features
- `hotfix/*`: urgent fixes
- `release/*`: release prep

## Commit style
Use Conventional Commits:
- `feat:`
- `fix:`
- `docs:`
- `refactor:`
- `test:`
- `chore:`

## Quality checks
```bash
pytest
pytest --cov=src
ruff check src
ruff format src
mypy src
```

## Pull Request checklist
- Code follows project conventions.
- Tests added/updated and passing.
- Documentation updated when behavior changed.
- No secrets or sensitive data committed.

## Security
- Validate all external inputs.
- Use parameterized SQL queries.
- Never commit `.env`.
- Validate uploaded file type and size.
