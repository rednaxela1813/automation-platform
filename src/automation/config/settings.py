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

    # Enhanced security limits
    max_pdf_pages: int = 100
    max_text_size_kb: int = 1024  # 1MB of extracted text
    max_archive_files: int = 50
    max_archive_ratio: float = 10.0  # Compression ratio for zip-bomb detection
    dangerous_extensions: list[str] = [
        ".exe", ".scr", ".com", ".bat", ".cmd", ".pif", ".jar", ".js", ".vbs", 
        ".ps1", ".sh", ".app", ".deb", ".rpm", ".dmg", ".iso"
    ]
    
    # Antivirus settings
    enable_clamav: bool = False
    clamav_socket: str = "/var/run/clamav/clamd.ctl"
    quarantine_on_virus: bool = True

    # Retry settings  
    max_retry_attempts: int = 3
    retry_backoff_minutes: int = 15  # Exponential backoff base
    failed_retry_after_hours: int = 24  # Retry failed items after N hours

    # Config for loading .env file
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False
    )


settings = Settings()
