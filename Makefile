# Makefile для Email Automation Platform

.PHONY: help install dev-install test lint format type-check clean run docker-build docker-up docker-down setup-dev

# Переменные
PYTHON := python3.12
PIP := pip3
VENV := .venv
ACTIVATE := $(VENV)/bin/activate

help: ## Показать справку по командам
	@echo "Email Automation Platform - Development Commands"
	@echo "================================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Установка и настройка
install: ## Установить зависимости
	$(PIP) install -e .

dev-install: ## Установить зависимости для разработки
	$(PIP) install -e ".[dev]"

setup-dev: ## Полная настройка среды разработки
	@echo "🚀 Настройка среды разработки..."
	cp .env.example .env
	mkdir -p storage/safe storage/quarantine logs
	$(MAKE) dev-install
	@echo "✅ Среда разработки настроена!"
	@echo "📝 Не забудьте отредактировать .env файл с вашими настройками"

venv: ## Создать виртуальное окружение
	$(PYTHON) -m venv $(VENV)
	@echo "Активируйте окружение: source $(ACTIVATE)"

# Разработка
run: ## Запустить сервер для разработки
	$(PYTHON) run.py

run-prod: ## Запустить сервер в production режиме
	uvicorn automation.main:app --host 0.0.0.0 --port 8000

celery-worker: ## Запустить Celery worker
	celery -A automation.celery_app worker --loglevel=info

celery-beat: ## Запустить Celery beat scheduler
	celery -A automation.celery_app beat --loglevel=info

celery-monitor: ## Запустить Celery flower для мониторинга
	celery -A automation.celery_app flower --port=5555

# Тестирование и качество кода
test: ## Запустить тесты
	pytest src/automation/tests/ -v

test-cov: ## Запустить тесты с покрытием
	pytest src/automation/tests/ --cov=automation --cov-report=html --cov-report=term

test-integration: ## Запустить интеграционные тесты
	pytest src/automation/tests/ -m integration -v

lint: ## Проверить код с помощью ruff
	ruff check src/ --config pyproject.toml

format: ## Форматировать код
	ruff format src/
	ruff check src/ --fix

type-check: ## Проверить типы с mypy
	mypy src/automation/

quality: lint type-check ## Проверить качество кода (lint + type-check)

# Очистка
clean: ## Очистить временные файлы
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	rm -rf build/ dist/ htmlcov/

clean-storage: ## Очистить файлы в storage (ОСТОРОЖНО!)
	@echo "⚠️  Это удалит все файлы в storage директориях!"
	@read -p "Продолжить? (y/N): " confirm && [ "$$confirm" = "y" ]
	rm -rf storage/safe/* storage/quarantine/*
	@echo "Storage очищен"

# Docker
docker-build: ## Собрать Docker образ
	docker build -t automation-platform:latest .

docker-up: ## Запустить все сервисы через Docker Compose
	docker-compose up -d

docker-down: ## Остановить все сервисы Docker Compose
	docker-compose down

docker-logs: ## Показать логи Docker контейнеров
	docker-compose logs -f

docker-shell: ## Открыть shell в основном контейнере
	docker-compose exec automation-platform bash

# База данных
db-init: ## Инициализировать базу данных
	$(PYTHON) -c "from automation.adapters.repository_sqlite import SqliteProcessedInvoiceRepository; from pathlib import Path; SqliteProcessedInvoiceRepository(Path('automation.db'))"

db-reset: ## Сбросить базу данных (ОСТОРОЖНО!)
	@echo "⚠️  Это удалит всю базу данных!"
	@read -p "Продолжить? (y/N): " confirm && [ "$$confirm" = "y" ]
	rm -f automation.db
	$(MAKE) db-init

# Мониторинг и отладка
logs: ## Показать логи приложения
	tail -f logs/automation.log

monitor: ## Запустить мониторинг системы
	watch -n 2 'df -h; echo ""; ps aux | grep -E "(python|celery)" | head -10'

health-check: ## Проверить состояние системы
	curl -f http://localhost:8000/api/v1/system/stats || echo "Сервер не отвечает"

# Документация
docs-serve: ## Запустить локальный сервер документации
	@echo "📚 Документация API доступна по адресу:"
	@echo "   Swagger UI: http://localhost:8000/docs"
	@echo "   ReDoc: http://localhost:8000/redoc"

# Deployment
deploy-staging: ## Деплой в staging окружение
	@echo "🚀 Деплой в staging..."
	# Здесь будут команды для деплоя

deploy-production: ## Деплой в production окружение
	@echo "🚀 Деплой в production..."
	@read -p "Подтвердите деплой в production (yes): " confirm && [ "$$confirm" = "yes" ]
	# Здесь будут команды для production деплоя

# Утилиты
check-deps: ## Проверить устаревшие зависимости
	$(PIP) list --outdated

backup: ## Создать резервную копию данных
	@echo "📦 Создание резервной копии..."
	mkdir -p backups
	cp -r storage/ backups/storage_$(shell date +%Y%m%d_%H%M%S)
	cp automation.db backups/automation_$(shell date +%Y%m%d_%H%M%S).db
	@echo "✅ Резервная копия создана в backups/"

security-check: ## Проверить безопасность зависимостей
	$(PIP) install safety
	safety check

update-deps: ## Обновить зависимости
	$(PIP) install --upgrade -e ".[dev]"

# По умолчанию показываем справку
.DEFAULT_GOAL := help