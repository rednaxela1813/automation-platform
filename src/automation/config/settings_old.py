from __future__ import annotations

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # IMAP настройки
    imap_host: str
    imap_user: str
    imap_password: str
    imap_mailbox: str = "INBOX"
    
    # FastAPI настройки
    app_name: str = "Email Automation Platform"
    app_version: str = "0.1.0"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Файловое хранилище
    safe_storage_dir: str = "./storage/safe"
    quarantine_dir: str = "./storage/quarantine"
    max_file_size_mb: int = 50
    
    # API настройки
    api_endpoint: str = ""
    api_key: str = ""
    
    # Конфигурация для загрузки .env файла
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    app_version: str = "0.1.0"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Файловое хранилище
    safe_storage_dir: str = "./storage/safe"
    quarantine_dir: str = "./storage/quarantine"
    max_file_size_mb: int = 50
    
    # API настройки
    api_endpoint: str = ""
    api_key: str = ""
    
    # Безопасность
    allowed_file_extensions: list[str] = [".pdf", ".xlsx", ".docx", ".xml"]
    scan_interval_minutes: int = 5


settings = Settings()
