from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # IMAP settings
    imap_host: str
    imap_user: str
    imap_password: str
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

    # API settings
    api_endpoint: str = ""
    api_key: str = ""

    # Config for loading .env file
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False
    )
    app_version: str = "0.1.0"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000

    # File storage
    safe_storage_dir: str = "./storage/safe"
    quarantine_dir: str = "./storage/quarantine"
    max_file_size_mb: int = 50

    # API settings
    api_endpoint: str = ""
    api_key: str = ""

    # Security
    allowed_file_extensions: list[str] = [".pdf", ".xlsx", ".docx", ".xml"]
    scan_interval_minutes: int = 5


settings = Settings()
