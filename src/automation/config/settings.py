# automation-platform/src/automation/config/settings.py

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # IMAP settings
    imap_host: str
    imap_user: str
    imap_password: str
    imap_port: int = 993
    imap_mailbox: str = "INBOX"

    # FastAPI settings
    app_name: str = "Email Automation Platform"
    app_version: str = "0.1.0"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000

    # File storage
    safe_storage_dir: str = "./storage/safe"
    quarantine_dir: str = "./storage/quarantine"
    max_file_size_mb: int = 50
    log_dir: str = "./logs"

    # Database
    database_url: str = "sqlite:///emails.db"
    redis_url: str = "redis://localhost:6379/0"

    # API settings
    api_endpoint: str = ""
    api_key: str = ""
    default_page_limit: int = 50
    cleanup_days_old: int = 30
    quarantine_days_old: int = 7
    logs_retention_days: int = 90
    archive_days_old: int = 90

    # Security
    allowed_file_extensions: list[str] = [".pdf", ".xlsx", ".docx", ".xml"]
    allowed_mime_types: list[str] = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/xml",
        "text/xml",
    ]
    scan_interval_minutes: int = 5

    # Config for loading .env file
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False
    )


settings = Settings()
