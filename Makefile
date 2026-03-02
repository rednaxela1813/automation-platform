# Makefile for Email Automation Platform

.PHONY: help install dev-install test lint format type-check clean run docker-build docker-up docker-down setup-dev

# Variables
PYTHON := python3.12
PIP := pip3
VENV := .venv
ACTIVATE := $(VENV)/bin/activate

help: ## Show command help
	@echo "Email Automation Platform - Development Commands"
	@echo "================================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Install and setup
install: ## Install dependencies
	$(PIP) install -e .

dev-install: ## Install development dependencies
	$(PIP) install -e ".[dev]"

setup-dev: ## Full development environment setup
	@echo "🚀 Setting up development environment..."
	cp .env.example .env
	mkdir -p storage/safe storage/quarantine logs
	$(MAKE) dev-install
	@echo "✅ Development environment is ready!"
	@echo "📝 Do not forget to edit .env with your settings"

venv: ## Create virtual environment
	$(PYTHON) -m venv $(VENV)
	@echo "Activate environment: source $(ACTIVATE)"

# Development
run: ## Run development server
	$(PYTHON) run.py

run-prod: ## Run server in production mode
	uvicorn automation.main:app --host 0.0.0.0 --port 8000

celery-worker: ## Run Celery worker
	celery -A automation.celery_app worker --loglevel=info

celery-beat: ## Run Celery beat scheduler
	celery -A automation.celery_app beat --loglevel=info

celery-monitor: ## Run Celery Flower for monitoring
	celery -A automation.celery_app flower --port=5555

# Testing and code quality
test: ## Run tests
	pytest src/automation/tests/ -v

test-cov: ## Run tests with coverage
	pytest src/automation/tests/ --cov=automation --cov-report=html --cov-report=term

test-integration: ## Run integration tests
	pytest src/automation/tests/ -m integration -v

lint: ## Check code with ruff
	ruff check src/ --config pyproject.toml

format: ## Format code
	ruff format src/
	ruff check src/ --fix

type-check: ## Type-check with mypy
	mypy src/automation/

quality: lint type-check ## Check code quality (lint + type-check)

# Cleanup
clean: ## Clean temporary files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	rm -rf build/ dist/ htmlcov/

clean-storage: ## Clean files in storage (CAUTION!)
	@echo "⚠️  This will delete all files in storage directories!"
	@read -p "Continue? (y/N): " confirm && [ "$$confirm" = "y" ]
	rm -rf storage/safe/* storage/quarantine/*
	@echo "Storage cleaned"

# Docker
docker-build: ## Build Docker image
	docker build -t automation-platform:latest .

docker-up: ## Start all services via Docker Compose
	docker-compose up -d

docker-down: ## Stop all Docker Compose services
	docker-compose down

docker-logs: ## Show Docker container logs
	docker-compose logs -f

docker-shell: ## Open shell in main container
	docker-compose exec automation-platform bash

# Database
db-init: ## Initialize database
	$(PYTHON) -c "from automation.adapters.repository_sqlite import SqliteProcessedInvoiceRepository; from pathlib import Path; SqliteProcessedInvoiceRepository(Path('automation.db'))"

db-reset: ## Reset database (CAUTION!)
	@echo "⚠️  This will delete the entire database!"
	@read -p "Continue? (y/N): " confirm && [ "$$confirm" = "y" ]
	rm -f automation.db
	$(MAKE) db-init

# Monitoring and debugging
logs: ## Show application logs
	tail -f logs/automation.log

monitor: ## Run system monitoring
	watch -n 2 'df -h; echo ""; ps aux | grep -E "(python|celery)" | head -10'

health-check: ## Check system status
	curl -f http://localhost:8000/api/v1/system/stats || echo "Server is not responding"

# Documentation
docs-serve: ## Run local documentation server
	@echo "📚 API documentation available at:"
	@echo "   Swagger UI: http://localhost:8000/docs"
	@echo "   ReDoc: http://localhost:8000/redoc"

# Deployment
deploy-staging: ## Deploy to staging
	@echo "🚀 Deploying to staging..."
	# Deployment commands go here

deploy-production: ## Deploy to production
	@echo "🚀 Deploying to production..."
	@read -p "Confirm production deployment (yes): " confirm && [ "$$confirm" = "yes" ]
	# Production deployment commands go here

# Utilities
check-deps: ## Check outdated dependencies
	$(PIP) list --outdated

backup: ## Create data backup
	@echo "📦 Creating backup..."
	mkdir -p backups
	cp -r storage/ backups/storage_$(shell date +%Y%m%d_%H%M%S)
	cp automation.db backups/automation_$(shell date +%Y%m%d_%H%M%S).db
	@echo "✅ Backup created in backups/"

security-check: ## Check dependency security
	$(PIP) install safety
	safety check

update-deps: ## Update dependencies
	$(PIP) install --upgrade -e ".[dev]"

# Show help by default
.DEFAULT_GOAL := help