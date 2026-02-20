# Contributing to Email Automation Platform

🙏 **Спасибо за интерес к участию в развитии Email Automation Platform!**

Этот документ содержит руководство для участников проекта.

## 🚀 Быстрый старт для разработчиков

### 1. Настройка среды разработки

```bash
# Клонирование репозитория
git clone https://github.com/your-username/automation-platform.git
cd automation-platform

# Создание виртуального окружения
python3.12 -m venv .venv
source .venv/bin/activate  # Linux/macOS
# или .venv\Scripts\activate  # Windows

# Установка зависимостей для разработки
make dev-install

# Настройка окружения
make setup-dev
```

### 2. Запуск для разработки

```bash
# Запуск основного сервера
make run

# В отдельном терминале - Celery worker
make celery-worker

# В третьем терминале - Celery beat
make celery-beat
```

## 📋 Процесс разработки

### Git workflow

Мы используем **Git Flow** модель:

- `main` - стабильная production ветка
- `develop` - основная ветка разработки
- `feature/*` - ветки для новых функций
- `hotfix/*` - ветки для критических исправлений
- `release/*` - ветки для подготовки релиз

### Создание feature

```bash
# Переходим на develop
git checkout develop
git pull origin develop

# Создаем feature ветку
git checkout -b feature/your-feature-name

# Делаем изменения, коммитим
git add .
git commit -m "feat: add your feature description"

# Пушим ветку
git push origin feature/your-feature-name

# Создаем Pull Request в GitHub
```

### Conventional Commits

Мы используем [Conventional Commits](https://www.conventionalcommits.org/) для сообщений коммитов:

```bash
feat: new feature
fix: bug fix
docs: documentation changes
style: formatting, missing semicolons, etc
refactor: code refactoring
test: adding tests
chore: maintenance tasks
```

**Примеры:**

```bash
feat: add PDF invoice parser
fix: resolve IMAP connection timeout
docs: update API documentation
test: add use case tests
refactor: improve file storage architecture
```

## 🧪 Тестирование

### Запуск тестов

```bash
# Все тесты
make test

# Тесты с покрытием
make test-cov

# Только интеграционные тесты
make test-integration
```

### Требования к тестам

- **Unit тесты**: Каждый новый модуль должен иметь unit тесты
- **Integration тесты**: Для новых use cases и API endpoints
- **Покрытие**: Стремимся к >80% code coverage
- **Мокинг**: Используем `unittest.mock` для зависимостей

### Пример теста

```python
def test_email_processing_success(mock_dependencies, sample_email):
    # Arrange
    use_case = EmailProcessingUseCase(**mock_dependencies)
    mock_dependencies['repository'].claim.return_value = True

    # Act
    result = use_case.process_new_emails()

    # Assert
    assert result.messages_processed == 1
    mock_dependencies['repository'].mark_done.assert_called_once()
```

## 🎨 Качество кода

### Форматирование и линтинг

```bash
# Форматирование кода
make format

# Проверка линтером
make lint

# Проверка типов
make type-check

# Все проверки качества
make quality
```

### Стандарты кода

- **Форматирование**: Используем `ruff format`
- **Линтинг**: `ruff check` с настройками в `pyproject.toml`
- **Типы**: Обязательные type hints, проверка с `mypy`
- **Архитектура**: Следуем Clean Architecture принципам
- **Именование**: Описательные имена на английском языке

### Пример качественного кода

```python
"""
Модуль для обработки email сообщений.
"""
from __future__ import annotations

from typing import Protocol
from dataclasses import dataclass

from automation.domain.models import Invoice
from automation.ports.email import EmailMessage


@dataclass(frozen=True)
class ProcessingResult:
    """Результат обработки email сообщений."""
    messages_processed: int
    invoices_found: int
    errors: list[str]


class EmailProcessor(Protocol):
    """Интерфейс для обработки электронной почты."""

    def process_messages(self, messages: list[EmailMessage]) -> ProcessingResult:
        """Обработать список email сообщений."""
        ...
```

## 📚 Документация

### API документация

- FastAPI автоматически генерирует Swagger/OpenAPI документацию
- Используйте подробные docstring для всех функций
- Добавляйте примеры в Pydantic модели

```python
class InvoiceResponse(BaseModel):
    """Ответ с данными счета."""

    invoice_number: str = Field(
        description="Номер счета",
        example="INV-2024-001"
    )
    amount: Decimal = Field(
        description="Сумма счета",
        example=150.00
    )
```

### Code документация

- Модули: docstring с описанием назначения
- Классы: docstring с описанием ответственности
- Функции: docstring с параметрами и возвращаемыми значениями

```python
def parse_invoice(file_path: Path) -> ParseResult:
    """
    Извлечь данные счета из файла.

    Args:
        file_path: Путь к файлу для парсинга

    Returns:
        ParseResult с данными счета или ошибками

    Raises:
        FileNotFoundError: Если файл не найден
        InvalidFormatError: Если формат файла неподдерживаемый
    """
```

## 🔒 Безопасность

### Безопасность кода

- **Валидация входных данных**: Используйте Pydantic модели
- **Credentials**: Никогда не коммитьте .env файлы с credentials
- **SQL Injection**: Используйте parameterized queries
- **Path Traversal**: Проверяйте пути файлов
- **File Upload**: Валидируйте типы и размеры файлов

### Проверка уязвимостей

```bash
# Проверка зависимостей
make security-check

# Банкет для статического анализа
bandit -r src/
```

## 🐛 Issues и Bug Reports

### Создание Issue

При создании issue включите:

1. **Описание**: Четкое описание проблемы
2. **Шаги воспроизведения**: Пошаговые инструкции
3. **Ожидаемое поведение**: Что должно произойти
4. **Текущее поведение**: Что происходит на самом деле
5. **Окружение**: ОС, версия Python, зависимости
6. **Логи**: Релевантные логи или скриншоты

### Template для Bug Report

```markdown
**Описание бага**
Краткое описание проблемы.

**Шаги воспроизведения**

1. Перейти к '...'
2. Нажать на '....'
3. Прокрутить вниз до '....'
4. Увидеть ошибку

**Ожидаемое поведение**
Что должно было произойти.

**Скриншоты**
При необходимости добавьте скриншоты.

**Окружение:**

- ОС: [например iOS]
- Браузер [например chrome, safari]
- Версия [например 22]

**Дополнительный контекст**
Любая другая информация о проблеме.
```

## 📦 Релизы

### Версионирование

Мы используем [Semantic Versioning](https://semver.org/):

- `MAJOR.MINOR.PATCH` (например, `1.2.3`)
- `MAJOR`: Breaking changes
- `MINOR`: Новые функции (backward compatible)
- `PATCH`: Bug fixes

### Подготовка релиза

1. Создать `release/x.y.z` ветку от `develop`
2. Обновить версию в `pyproject.toml`
3. Обновить CHANGELOG.md
4. Создать Pull Request в `main`
5. После мержа создать git tag
6. GitHub Actions автоматически создаст релиз

## 🤝 Code Review

### Что проверяем в PR

- [ ] Код соответствует стандартам проекта
- [ ] Есть тесты для новой функциональности
- [ ] Тесты проходят
- [ ] Документация обновлена
- [ ] Нет breaking changes (или они задокументированы)
- [ ] Performance не деградирует

### Checklist для автора PR

- [ ] Локально прошли все тесты (`make test`)
- [ ] Качество кода проверено (`make quality`)
- [ ] Добавлены/обновлены тесты
- [ ] Обновлена документация
- [ ] PR имеет понятное описание
- [ ] Связанные issues указаны в описании

## 📞 Связь

- **GitHub Issues**: Для багов и feature requests
- **GitHub Discussions**: Для вопросов и обсуждений
- **Email**: maintainer@email-automation-platform.com

---

**Спасибо за участие в проекте! 🚀**
