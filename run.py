#!/usr/bin/env python3
"""
Скрипт для запуска Email Automation Platform FastAPI сервера
"""

import uvicorn

from automation.config.settings import settings


def main():
    """Запуск FastAPI сервера с настройками из конфигурации"""
    uvicorn.run(
        "automation.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        reload_dirs=["src"] if settings.debug else None,
        log_level="info"
    )


if __name__ == "__main__":
    main()