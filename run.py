#!/usr/bin/env python3
"""
Скрипт для запуска Email Automation Platform FastAPI сервера
"""
import sys
from pathlib import Path

# Добавляем src директорию в PYTHONPATH
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

import uvicorn

from automation.config.settings import settings


def main():
    """Запуск FastAPI сервера с настройками из конфигурации"""
    print(f"🚀 Запуск Email Automation Platform на {settings.host}:{settings.port}")
    print(f"📚 API документация: http://{settings.host}:{settings.port}/docs")
    print(f"🔄 Debug режим: {settings.debug}")
    
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