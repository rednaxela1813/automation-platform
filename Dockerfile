# Dockerfile для Email Automation Platform
FROM python:3.12-slim as base

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файлы проекта
COPY pyproject.toml ./
COPY src/ src/
COPY run.py ./

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir -e .

# Создаем директории для хранения
RUN mkdir -p storage/safe storage/quarantine logs

# Создаем пользователя для безопасности
RUN groupadd -r automation && useradd -r -g automation automation
RUN chown -R automation:automation /app
USER automation

# Открываем порт
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Запускаем приложение
CMD ["python", "run.py"]