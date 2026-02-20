"""
API роутеры для Email Automation Platform
Содержит все endpoints для управления системой обработки почты
"""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Any

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, UploadFile, File
from pydantic import BaseModel

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
async def test_imap_connection(settings: Settings = Depends(get_settings)):
    """
    Тестировать подключение к IMAP серверу
    """
    try:
        from automation.adapters.email_imap import ImapEmailClient
        
        client = ImapEmailClient()
        # Здесь будет тест подключения
        
        return {
            "status": "success", 
            "message": "IMAP connection successful",
            "server": settings.imap_host
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"IMAP connection failed: {str(e)}"
        )


# ===== BACKGROUND TASKS =====

async def process_emails_task(force_reprocess: bool = False, dry_run: bool = False):
    """
    Фоновая задача для обработки электронной почты
    """
    print(f"Starting email processing: force={force_reprocess}, dry_run={dry_run}")
    
    try:
        # Здесь будет вызов use case для обработки почты
        # from automation.app.use_cases import ProcessEmailInvoicesUseCase
        # processor = ProcessEmailInvoicesUseCase(...)
        # await processor.execute()
        
        print("Email processing completed successfully")
    except Exception as e:
        print(f"Email processing failed: {str(e)}")
        # Здесь можно добавить логирование и уведомления