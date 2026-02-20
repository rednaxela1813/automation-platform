"""
FastAPI dependencies для Dependency Injection
Здесь определяются все зависимости которые будут инжектиться в endpoints
"""
from __future__ import annotations

from functools import lru_cache

from automation.config.settings import Settings


@lru_cache()
def get_settings() -> Settings:
    """
    Dependency для получения настроек приложения
    Кешируется для производительности
    """
    from automation.config.settings import settings
    return settings


async def get_email_processor():
    """
    Dependency для получения email процессора
    В будущем здесь будет создаваться экземпляр с использованием DI
    """
    from automation.adapters.email_imap import ImapEmailClient
    return ImapEmailClient()


async def get_file_storage():
    """
    Dependency для получения файлового хранилища
    """
    # В будущем здесь будет создаваться FileStorage service
    pass


async def get_document_parser():
    """  
    Dependency для получения парсера документов
    """
    # В будущем здесь будет создаваться DocumentParser service
    pass


# Dependency для проверки API ключей (если понадобится)
async def verify_api_key(api_key: str = None):
    """
    Проверка API ключа для защищенных endpoints
    """
    settings = get_settings()
    
    if not settings.api_key:
        return True  # Если API ключ не настроен, разрешаем доступ
    
    if api_key != settings.api_key:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return True