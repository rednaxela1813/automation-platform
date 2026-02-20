"""
Настройка логирования для Email Automation Platform
"""
import logging
import logging.handlers
from pathlib import Path
from typing import Optional

from automation.config.settings import settings


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[Path] = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> logging.Logger:
    """
    Настроить логирование для приложения
    
    Args:
        log_level: Уровень логирования (DEBUG, INFO, WARNING, ERROR)
        log_file: Путь к файлу логов (если None - только console)
        max_bytes: Максимальный размер файла лога
        backup_count: Количество архивных файлов логов
    
    Returns:
        Настроенный logger
    """
    
    # Создаем основной logger
    logger = logging.getLogger("automation")
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Очищаем существующие handlers
    logger.handlers.clear()
    
    # Формат логирования
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    logger.addHandler(console_handler)
    
    # File handler (если указан путь к файлу)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(getattr(logging, log_level.upper()))
        logger.addHandler(file_handler)
    
    # Настраиваем логирование для сторонних библиотек
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.WARNING)
    
    logger.info(f"Logging setup completed. Level: {log_level}, File: {log_file}")
    
    return logger


def get_logger(name: str = "automation") -> logging.Logger:
    """Получить logger по имени"""
    return logging.getLogger(name)


# Настройка логирования при импорте модуля
log_file = Path("logs/automation.log") if not settings.debug else None
setup_logging(
    log_level="DEBUG" if settings.debug else "INFO",
    log_file=log_file
)