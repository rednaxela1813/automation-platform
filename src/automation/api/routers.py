"""
API роутеры для Email Automation Platform
Содержит все endpoints для управления системой обработки почты
"""
from __future__ import annotations

from datetime import datetime, timedelta
import mimetypes
from pathlib import Path
from urllib.parse import unquote
from typing import Dict, List, Any

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, UploadFile, File, Query
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel
import imaplib

from automation.api.dependencies import get_email_processor, get_settings
from automation.config.settings import Settings


router = APIRouter()


# Pydantic модели для API
class ProcessingStatusResponse(BaseModel):
    status: str
    message: str
    processed_at: datetime
    emails_processed: int = 0
    files_processed: int = 0
    files_quarantined: int = 0


class EmailProcessingRequest(BaseModel):
    force_reprocess: bool = False
    dry_run: bool = False


class SystemStatsResponse(BaseModel):
    total_emails_processed: int
    files_in_safe_storage: int
    files_in_quarantine: int
    last_processing_time: datetime | None
    system_status: str


class ConfigResponse(BaseModel):
    imap_host: str
    imap_mailbox: str
    max_file_size_mb: int
    allowed_extensions: List[str]
    scan_interval_minutes: int


class TestConnectionRequest(BaseModel):
    imap_host: str | None = None
    imap_port: int | None = None
    imap_username: str | None = None
    imap_password: str | None = None
    imap_mailbox: str | None = None


# ===== EMAIL PROCESSING ENDPOINTS =====

@router.post("/emails/process", response_model=ProcessingStatusResponse)
async def trigger_email_processing(
    request: EmailProcessingRequest,
    background_tasks: BackgroundTasks,
    settings: Settings = Depends(get_settings)
):
    """
    Запустить обработку электронной почты
    Можно запускать принудительно или в тестовом режиме
    """
    try:
        # Запускаем обработку в фоновой задаче
        background_tasks.add_task(process_emails_task, request.force_reprocess, request.dry_run)
        
        return ProcessingStatusResponse(
            status="started",
            message="Email processing started in background",
            processed_at=datetime.now()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start processing: {str(e)}")


@router.get("/emails/status", response_model=ProcessingStatusResponse)
async def get_processing_status():
    """
    Получить статус последней обработки почты
    """
    # Здесь будет логика получения статуса из базы или кеша
    return ProcessingStatusResponse(
        status="idle",
        message="No active processing",
        processed_at=datetime.now()
    )


# ===== FILE MANAGEMENT ENDPOINTS =====
def _resolve_safe_file(path_value: str, settings: Settings) -> Path:
    safe_dir = Path(settings.safe_storage_dir).resolve()
    storage_root = safe_dir.parent.resolve()

    decoded = unquote(path_value or "").lstrip("/")
    if not decoded:
        raise HTTPException(status_code=404, detail="File not found")

    # Primary: "safe/filename.ext" relative to storage root
    candidate = (storage_root / decoded).resolve()
    if candidate.is_file() and candidate.is_relative_to(safe_dir):
        return candidate

    # Fallback: path relative to safe dir
    candidate = (safe_dir / decoded).resolve()
    if candidate.is_file() and candidate.is_relative_to(safe_dir):
        return candidate

    raise HTTPException(status_code=404, detail="File not found")

@router.get("/files/safe")
async def list_safe_files(
    limit: int = 50,
    offset: int = 0,
    settings: Settings = Depends(get_settings)
):
    """
    Получить список файлов в безопасном хранилище
    """
    from pathlib import Path
    
    safe_dir = Path(settings.safe_storage_dir)
    if not safe_dir.exists():
        return {"files": [], "total": 0}
    
    files = list(safe_dir.glob("*"))
    files = files[offset:offset + limit]
    
    file_info = []
    for file in files:
        if file.is_file():
            stat = file.stat()
            file_info.append({
                "name": file.name,
                "size": stat.st_size,
                "created_at": datetime.fromtimestamp(stat.st_ctime),
                "modified_at": datetime.fromtimestamp(stat.st_mtime)
            })
    
    return {
        "files": file_info,
        "total": len(list(safe_dir.glob("*")))
    }


@router.get("/files/view/{path_value:path}")
async def view_safe_file(
    path_value: str,
    settings: Settings = Depends(get_settings)
):
    file_path = _resolve_safe_file(path_value, settings)
    media_type, _ = mimetypes.guess_type(str(file_path))
    return FileResponse(
        path=str(file_path),
        media_type=media_type or "application/octet-stream",
        filename=file_path.name,
        headers={"Content-Disposition": f'inline; filename="{file_path.name}"'},
    )


@router.get("/files/download")
async def download_safe_file(
    path: str = Query(..., description="Relative path to safe storage file"),
    settings: Settings = Depends(get_settings)
):
    file_path = _resolve_safe_file(path, settings)
    media_type, _ = mimetypes.guess_type(str(file_path))
    return FileResponse(
        path=str(file_path),
        media_type=media_type or "application/octet-stream",
        filename=file_path.name,
    )


@router.get("/files/info")
async def file_info(
    path: str = Query(..., description="Relative path to safe storage file"),
    settings: Settings = Depends(get_settings)
):
    file_path = _resolve_safe_file(path, settings)
    stat = file_path.stat()
    size_kb = stat.st_size / 1024
    size_formatted = f"{size_kb:.1f} KB" if size_kb < 1024 else f"{size_kb / 1024:.1f} MB"
    mime_type, _ = mimetypes.guess_type(str(file_path))

    return {
        "success": True,
        "filename": file_path.name,
        "size": stat.st_size,
        "size_formatted": size_formatted,
        "created_at": datetime.fromtimestamp(stat.st_mtime).strftime("%d.%m.%Y %H:%M"),
        "mime_type": mime_type,
        "extracted_data": None,
    }


@router.get("/files/analyze")
async def analyze_file(
    path: str = Query(..., description="Relative path to safe storage file"),
    settings: Settings = Depends(get_settings)
):
    _resolve_safe_file(path, settings)
    return PlainTextResponse("Analyze is not implemented yet.", status_code=501)


@router.post("/files/cleanup")
async def cleanup_old_files(
    settings: Settings = Depends(get_settings)
):
    safe_dir = Path(settings.safe_storage_dir)
    if not safe_dir.exists():
        return {"message": "Safe storage directory not found", "files_removed": 0}

    cutoff = datetime.now() - timedelta(days=30)
    removed = 0
    for file_path in safe_dir.iterdir():
        if not file_path.is_file():
            continue
        if datetime.fromtimestamp(file_path.stat().st_mtime) < cutoff:
            try:
                file_path.unlink()
                removed += 1
            except OSError:
                continue

    return {"message": f"Removed {removed} files", "files_removed": removed}


@router.get("/files/quarantine")
async def list_quarantine_files(
    limit: int = 50,
    offset: int = 0,
    settings: Settings = Depends(get_settings)
):
    """
    Получить список файлов в карантине
    """
    from pathlib import Path
    
    quarantine_dir = Path(settings.quarantine_dir)
    if not quarantine_dir.exists():
        return {"files": [], "total": 0}
    
    files = list(quarantine_dir.glob("*"))
    files = files[offset:offset + limit]
    
    file_info = []
    for file in files:
        if file.is_file():
            stat = file.stat()
            file_info.append({
                "name": file.name,
                "size": stat.st_size,
                "created_at": datetime.fromtimestamp(stat.st_ctime),
                "quarantine_reason": "Unknown",  # Можно расширить метаданными
            })
    
    return {
        "files": file_info,
        "total": len(list(quarantine_dir.glob("*")))
    }


@router.delete("/files/quarantine/{filename}")
async def delete_quarantine_file(
    filename: str,
    settings: Settings = Depends(get_settings)
):
    """
    Удалить файл из карантина
    """
    from pathlib import Path
    
    file_path = Path(settings.quarantine_dir) / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found in quarantine")
    
    if not file_path.is_file():
        raise HTTPException(status_code=400, detail="Invalid file")
    
    try:
        file_path.unlink()
        return {"message": f"File {filename} deleted from quarantine"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")


# ===== SYSTEM MANAGEMENT ENDPOINTS =====

@router.get("/system/stats", response_model=SystemStatsResponse)
async def get_system_stats(settings: Settings = Depends(get_settings)):
    """
    Получить статистику системы
    """
    from pathlib import Path
    
    safe_files = len(list(Path(settings.safe_storage_dir).glob("*"))) if Path(settings.safe_storage_dir).exists() else 0
    quarantine_files = len(list(Path(settings.quarantine_dir).glob("*"))) if Path(settings.quarantine_dir).exists() else 0
    
    return SystemStatsResponse(
        total_emails_processed=0,  # Будет браться из базы данных
        files_in_safe_storage=safe_files,
        files_in_quarantine=quarantine_files,
        last_processing_time=None,  # Будет браться из базы данных
        system_status="healthy"
    )


@router.get("/system/config", response_model=ConfigResponse)
async def get_system_config(settings: Settings = Depends(get_settings)):
    """
    Получить текущую конфигурацию системы
    """
    return ConfigResponse(
        imap_host=settings.imap_host,
        imap_mailbox=settings.imap_mailbox,
        max_file_size_mb=settings.max_file_size_mb,
        allowed_extensions=settings.allowed_file_extensions,
        scan_interval_minutes=settings.scan_interval_minutes
    )


@router.post("/system/test-connection")
async def test_imap_connection(
    request: TestConnectionRequest | None = None,
    settings: Settings = Depends(get_settings)
):
    """
    Тестировать подключение к IMAP серверу
    """
    try:
        req = request or TestConnectionRequest()
        host = req.imap_host or settings.imap_host
        port = req.imap_port or 993
        username = req.imap_username or settings.imap_user
        password = req.imap_password or settings.imap_password
        mailbox = req.imap_mailbox or settings.imap_mailbox

        if not host or not username or not password:
            return {
                "success": False,
                "status": "failed",
                "error": "IMAP credentials not provided"
            }

        with imaplib.IMAP4_SSL(host, port) as imap:
            imap.login(username, password)
            status, _ = imap.select(mailbox)
            if status != "OK":
                return {
                    "success": False,
                    "status": "failed",
                    "error": f"Failed to select mailbox '{mailbox}'"
                }

        return {
            "success": True,
            "status": "success",
            "message": f"IMAP connection successful. Mailbox '{mailbox}' доступен.",
            "server": host
        }
    except imaplib.IMAP4.error as e:
        return {
            "success": False,
            "status": "failed",
            "error": f"IMAP auth failed: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "status": "failed",
            "error": f"IMAP connection failed: {str(e)}"
        }


# ===== BACKGROUND TASKS =====

async def process_emails_task(force_reprocess: bool = False, dry_run: bool = False):
    """
    Фоновая задача для обработки электронной почты
    """
    print(f"🚀 Starting email processing: force={force_reprocess}, dry_run={dry_run}")
    
    try:
        # Импортируем необходимые зависимости
        from automation.app.use_cases import EmailProcessingUseCase
        from automation.adapters.email_imap import ImapEmailClient
        from automation.adapters.repository_sqlite import SqliteProcessedInvoiceRepository
        from automation.adapters.shopify_pdf_parser import ShopifyPdfInvoiceParser
        from automation.adapters.pdf_parser import PdfInvoiceParser
        from automation.adapters.excel_parser import ExcelInvoiceParser
        from automation.adapters.file_storage import LocalFileStorage
        from automation.config.settings import settings
        
        # Создаем адаптеры
        email_client = ImapEmailClient()  # Использует настройки из settings автоматически
        
        db_path = settings.database_url
        if db_path.startswith("sqlite:///"):
            db_path = db_path.replace("sqlite:///", "")
        repository = SqliteProcessedInvoiceRepository(db_path)
        document_parsers = [
            ShopifyPdfInvoiceParser(),
            PdfInvoiceParser(),
            ExcelInvoiceParser(),
        ]
        file_storage = LocalFileStorage()  # Использует настройки из settings автоматически
        
        # Создаем и выполняем use case
        use_case = EmailProcessingUseCase(
            email_processor=email_client,
            repository=repository,
            document_parser=document_parsers,
            file_storage=file_storage
        )
        
        result = use_case.process_new_emails(dry_run=dry_run)
        
        print(f"✅ Email processing completed: {result.messages_processed} messages, "
              f"{result.invoices_found} invoices found, {result.invoices_uploaded} uploaded, "
              f"{result.files_quarantined} quarantined")
        
    except Exception as e:
        print(f"❌ Email processing failed: {str(e)}")
        import traceback
        traceback.print_exc()
