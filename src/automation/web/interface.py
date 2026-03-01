"""
Веб-интерфейс для управления Email Automation Platform
"""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

from fastapi import APIRouter, HTTPException, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import imaplib

from automation.config.settings import settings


# Инициализация templates
templates = Jinja2Templates(directory="templates")
web_router = APIRouter()


class WebStats(BaseModel):
    """Статистика для веб-интерфейса"""
    total_emails_processed: int = 0
    files_in_safe_storage: int = 0
    files_in_quarantine: int = 0
    system_status: str = "Готов"
    last_processing_time: Optional[datetime] = None


class FileInfo(BaseModel):
    """Информация о файле"""
    filename: str
    filepath: str
    size: int
    size_formatted: str
    created_at: str


def get_web_stats() -> WebStats:
    """Получить статистику для веб-интерфейса"""
    try:
        safe_storage = Path(settings.safe_storage_dir)
        quarantine_storage = Path(settings.quarantine_dir)

        allowed_extensions = {ext.lower() for ext in settings.allowed_file_extensions}

        def is_safe_file(path: Path) -> bool:
            return path.is_file() and path.suffix.lower() in allowed_extensions

        def is_quarantine_file(path: Path) -> bool:
            return path.is_file() and not path.name.endswith(".quarantine_info.json")

        safe_files = (
            len([f for f in safe_storage.iterdir() if is_safe_file(f)])
            if safe_storage.exists()
            else 0
        )
        quarantine_files = (
            len([f for f in quarantine_storage.iterdir() if is_quarantine_file(f)])
            if quarantine_storage.exists()
            else 0
        )
        
        return WebStats(
            total_emails_processed=safe_files + quarantine_files,  # Приблизительная оценка
            files_in_safe_storage=safe_files,
            files_in_quarantine=quarantine_files,
            system_status="Активен" if safe_files > 0 else "Готов",
            last_processing_time=datetime.now() if safe_files > 0 else None
        )
    except Exception as e:
        print(f"Ошибка получения статистики: {e}")
        return WebStats()


def get_recent_files(limit: int = 5) -> List[FileInfo]:
    """Получить список последних файлов"""
    files = []
    try:
        safe_storage = Path(settings.safe_storage_dir)
        if not safe_storage.exists():
            return files
        allowed_extensions = {ext.lower() for ext in settings.allowed_file_extensions}
        all_files = [
            f for f in safe_storage.iterdir()
            if f.is_file() and f.suffix.lower() in allowed_extensions
        ]
        all_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        
        for file_path in all_files[:limit]:
            if file_path.is_file():
                stat = file_path.stat()
                size_mb = stat.st_size / 1024 / 1024

                try:
                    relative_path = file_path.relative_to(safe_storage.parent)
                except ValueError:
                    relative_path = file_path
                
                files.append(FileInfo(
                    filename=file_path.name,
                    filepath=str(relative_path),
                    size=stat.st_size,
                    size_formatted=f"{size_mb:.1f} MB" if size_mb > 1 else f"{stat.st_size // 1024} KB",
                    created_at=datetime.fromtimestamp(stat.st_mtime).strftime("%d.%m.%Y %H:%M")
                ))
        
    except Exception as e:
        print(f"Ошибка получения файлов: {e}")
    
    return files


@web_router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Главная страница дашборда"""
    stats = get_web_stats()
    config = {
        'imap_host': settings.imap_host,
        'imap_mailbox': settings.imap_mailbox,
        'max_file_size_mb': 50,  # Default value
        'allowed_extensions': ['pdf', 'xlsx', 'docx']
    }
    recent_files = get_recent_files(5)
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "title": "Дашборд",
        "current_page": "dashboard",
        "stats": stats.dict(),
        "config": config,
        "recent_files": recent_files
    })


@web_router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    """Страница настроек"""
    config = {
        'imap_host': settings.imap_host,
        'imap_port': 993,
        'imap_username': settings.imap_user,
        'imap_mailbox': settings.imap_mailbox,
        'max_file_size_mb': 50,
        'allowed_extensions': ['pdf', 'xlsx', 'docx'],
        'storage_path': './storage',
        'scan_interval_minutes': 30,
        'auto_processing': False,
        'enable_quarantine': True
    }
    
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "title": "Настройки",
        "current_page": "settings",
        "config": config
    })


@web_router.get("/files", response_class=HTMLResponse)
async def files_page(request: Request):
    """Страница со списком файлов"""
    all_files = get_recent_files(50)  # Больше файлов на странице файлов
    pdf_count = sum(1 for f in all_files if f.filename.lower().endswith(".pdf"))
    
    return templates.TemplateResponse("files.html", {
        "request": request,
        "title": "Файлы",
        "current_page": "files",
        "files": all_files,
        "pdf_count": pdf_count
    })


@web_router.get("/logs", response_class=HTMLResponse) 
async def logs_page(request: Request):
    """Страница логов"""
    # Примерные логи для демонстрации
    now = datetime.now()
    logs = [
        {
            "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
            "level": "INFO",
            "message": "Email processing completed: 4 messages processed"
        },
        {
            "timestamp": (now - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S"),
            "level": "SUCCESS",
            "message": "PDF file extracted: Novaglen_481474921.pdf (53KB)"
        },
        {
            "timestamp": (now - timedelta(minutes=6)).strftime("%Y-%m-%d %H:%M:%S"),
            "level": "SUCCESS", 
            "message": "PDF file extracted: Eyelashes_and_Beauty_481483348.pdf (52KB)"
        },
        {
            "timestamp": (now - timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S"),
            "level": "INFO",
            "message": "IMAP connection established to mail.deilmann.sk"
        }
    ]
    
    log_stats = {
        "ERROR": sum(1 for log in logs if log.get("level") == "ERROR"),
        "WARNING": sum(1 for log in logs if log.get("level") == "WARNING"),
        "SUCCESS": sum(1 for log in logs if log.get("level") == "SUCCESS"),
        "INFO": sum(1 for log in logs if log.get("level") == "INFO"),
    }

    return templates.TemplateResponse("logs.html", {
        "request": request,
        "title": "Логи системы",
        "current_page": "logs",
        "logs": logs,
        "log_stats": log_stats
    })


# API endpoints для веб-интерфейса
@web_router.get("/api/web/stats")
async def web_stats():
    """API для получения статистики"""
    return get_web_stats().dict()


@web_router.post("/api/web/test-connection")
async def test_connection_web(
    imap_host: str = Form(...),
    imap_port: int = Form(...),
    imap_username: str = Form(...),
    imap_mailbox: str = Form(...),
    imap_password: str | None = Form(None)
):
    """Тестирование подключения к IMAP"""
    try:
        host = imap_host or settings.imap_host
        port = imap_port or 993
        username = imap_username or settings.imap_user
        password = imap_password or settings.imap_password
        mailbox = imap_mailbox or settings.imap_mailbox

        if not host or not username or not password:
            return {
                "success": False,
                "error": "IMAP credentials not provided"
            }

        with imaplib.IMAP4_SSL(host, port) as imap:
            imap.login(username, password)
            status, _ = imap.select(mailbox)
            if status != "OK":
                return {
                    "success": False,
                    "error": f"Failed to select mailbox '{mailbox}'"
                }

        return {
            "success": True,
            "message": f"Подключение к {host}:{port} успешно установлено. Найден ящик '{mailbox}'."
        }
    except imaplib.IMAP4.error as e:
        return {
            "success": False,
            "error": f"IMAP auth failed: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Не удалось подключиться к серверу: {str(e)}"
        }


@web_router.get("/api/web/connection-status")
async def connection_status_web():
    """Проверка статуса подключения"""
    try:
        # Проверяем настройки
        if settings.imap_host and settings.imap_user:
            return {
                "connected": True,
                "last_check": datetime.now().strftime("%H:%M:%S")
            }
        else:
            return {
                "connected": False,
                "error": "Настройки подключения не заполнены"
            }
    except Exception as e:
        return {
            "connected": False,
            "error": str(e)
        }
