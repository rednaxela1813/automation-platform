# Email Automation Platform

🚀 **Автоматизированная система обработки электронной почты с вложениями**

Система для автоматического получения писем, обработки вложений (PDF, Excel, Word, XML), безопасного хранения файлов и парсинга данных счетов.

## ⚡ Быстрый старт

### 1. Установка зависимостей

```bash
# Клонируйте и перейдите в директорию проекта
cd automation-platform

# Установите зависимости
pip install -e .

# Или для разработки
pip install -e ".[dev]"
```

### 2. Настройка окружения

```bash
# Скопируйте файл настроек
cp .env.example .env

# Отредактируйте .env файл с вашими настройками IMAP
nano .env
```

### 3. Запуск FastAPI сервера

```bash
# Запуск сервера
python run.py

# Или через uvicorn напрямую
uvicorn automation.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Доступ к API

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **API Base**: http://localhost:8000/api/v1

## 🛠 API Endpoints

### 📧 Обработка почты

- `POST /api/v1/emails/process` - Запустить обработку почты
- `GET /api/v1/emails/status` - Статус обработки

### 📁 Управление файлами

- `GET /api/v1/files/safe` - Файлы в безопасном хранилище
- `GET /api/v1/files/quarantine` - Файлы в карантине
- `DELETE /api/v1/files/quarantine/{filename}` - Удалить из карантина

### ⚙️ Система

- `GET /api/v1/system/stats` - Статистика системы
- `GET /api/v1/system/config` - Конфигурация
- `POST /api/v1/system/test-connection` - Тест IMAP подключения

## 🏗 Архитектура

Проект использует Clean Architecture:

```
src/automation/
├── main.py              # FastAPI приложение
├── api/                 # FastAPI роутеры и зависимости
├── domain/              # Бизнес-логика и модели
├── ports/               # Интерфейсы (абстракции)
├── adapters/            # Реализации (IMAP, файлы, парсеры)
├── app/                 # Use Cases (бизнес-сценарии)
└── config/              # Настройки
```

## 🔐 Безопасность

- ✅ Проверка типов файлов по расширению и MIME
- ✅ Ограничение размера файлов
- ✅ Карантин для подозрительных файлов
- ✅ Изолированное хранение безопасных файлов

## 📝 Пример использования API

```bash
# Запустить обработку почты
curl -X POST "http://localhost:8000/api/v1/emails/process" \
     -H "Content-Type: application/json" \
     -d '{"force_reprocess": false, "dry_run": false}'

# Получить статистику
curl "http://localhost:8000/api/v1/system/stats"

# Проверить подключение к IMAP
curl -X POST "http://localhost:8000/api/v1/system/test-connection"
```

## 🚧 В разработке

- [ ] Реализация адаптеров для файлового хранилища
- [ ] Парсеры документов (PDF, Excel, XML)
- [ ] Use Cases для обработки
- [ ] Интеграция с внешними API
- [ ] Планировщик задач
- [ ] Мониторинг и логирование

## 🧪 Тестирование

```bash
# Запуск тестов
pytest

# С покрытием кода
pytest --cov=automation
```

## 📚 Разработка

```bash
# Проверка типов
mypy src/

# Форматирование кода
ruff check src/
ruff format src/
```
