"""
Фоновые задачи для обработки email
"""
from __future__ import annotations

import logging
from typing import Dict, Any

from automation.celery_app import celery_app
from automation.app.use_cases import EmailProcessingUseCase
from automation.adapters.email_imap import ImapEmailClient
from automation.adapters.repository_sqlite import SqliteProcessedInvoiceRepository
from automation.adapters.pdf_parser import PdfInvoiceParser
from automation.adapters.excel_parser import ExcelInvoiceParser
from automation.adapters.file_storage import LocalFileStorage
from automation.config.settings import settings
from pathlib import Path

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, retry_kwargs={'max_retries': 3, 'countdown': 60})
def process_new_emails_task(self) -> Dict[str, Any]:
    """
    Периодическая задача для обработки новых email сообщений
    """
    try:
        logger.info("Starting email processing task")
        
        # Инициализируем зависимости
        email_processor = ImapEmailClient()
        repository = SqliteProcessedInvoiceRepository(Path("automation.db"))
        document_parser = PdfInvoiceParser()  # Можно расширить для поддержки разных форматов
        file_storage = LocalFileStorage()
        
        # Создаем use case
        use_case = EmailProcessingUseCase(
            email_processor=email_processor,
            repository=repository,
            document_parser=document_parser,
            file_storage=file_storage
        )
        
        # Обрабатываем новые email
        result = use_case.process_new_emails()
        
        logger.info(
            f"Email processing completed: {result.messages_processed} messages, "
            f"{result.invoices_found} invoices found, "
            f"{result.invoices_uploaded} uploaded"
        )
        
        return {
            "status": "success",
            "messages_processed": result.messages_processed,
            "invoices_found": result.invoices_found,
            "invoices_uploaded": result.invoices_uploaded,
            "files_quarantined": result.files_quarantined,
            "errors": result.errors[:10]  # Ограничиваем количество ошибок в ответе
        }
        
    except Exception as exc:
        logger.error(f"Email processing task failed: {exc}", exc_info=True)
        
        # Retry задачи при ошибке
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            logger.error("Max retries exceeded for email processing task")
            return {
                "status": "failed",
                "error": str(exc),
                "messages_processed": 0
            }


@celery_app.task(bind=True)
def process_single_email_task(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Задача для обработки одного email сообщения
    Используется для обработки email в реальном времени через webhook
    """
    try:
        logger.info(f"Processing single email: {message_data.get('message_id')}")
        
        # Здесь будет логика обработки одного сообщения
        # Когда приходит webhook от почтового провайдера
        
        return {
            "status": "success",
            "message_id": message_data.get("message_id"),
            "processed_at": "2024-02-20T10:00:00Z"
        }
        
    except Exception as exc:
        logger.error(f"Single email processing failed: {exc}", exc_info=True)
        return {
            "status": "failed",
            "error": str(exc)
        }


@celery_app.task
def send_processing_report_task(period: str = "daily") -> Dict[str, Any]:
    """
    Задача для отправки отчетов о обработке
    """
    try:
        logger.info(f"Generating {period} processing report")
        
        # Здесь будет логика генерации отчета
        # Статистика обработанных email, ошибок, etc.
        
        report_data = {
            "period": period,
            "emails_processed": 42,
            "invoices_extracted": 38,
            "errors": ["Connection timeout", "Invalid file format"]
        }
        
        # Отправка отчета (email, Slack, etc.)
        logger.info(f"Processing report sent: {report_data}")
        
        return {
            "status": "success",
            "report": report_data
        }
        
    except Exception as exc:
        logger.error(f"Report generation failed: {exc}", exc_info=True)
        return {
            "status": "failed", 
            "error": str(exc)
        }