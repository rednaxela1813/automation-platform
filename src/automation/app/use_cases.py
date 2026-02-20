"""
Use Cases для бизнес-логики обработки email и счетов
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass

from automation.domain.models import Invoice, InvoiceStatus
from automation.ports.email import EmailProcessor, EmailMessage  
from automation.ports.repository import ProcessedInvoiceRepository
from automation.ports.document_parser import DocumentParser, ParseResult
from automation.ports.file_storage import FileStorage


@dataclass
class ProcessingResult:
    """Результат обработки email"""
    messages_processed: int
    invoices_found: int
    invoices_uploaded: int
    files_quarantined: int
    errors: List[str]


class EmailProcessingUseCase:
    """Use case для обработки входящих email сообщений"""
    
    def __init__(
        self,
        email_processor: EmailProcessor,
        repository: ProcessedInvoiceRepository,
        document_parser: DocumentParser,
        file_storage: FileStorage,
    ):
        self._email_processor = email_processor
        self._repository = repository
        self._document_parser = document_parser  
        self._file_storage = file_storage
    
    def process_new_emails(self, dry_run: bool = False) -> ProcessingResult:
        """Обработать новые email сообщения"""
        messages = self._email_processor.fetch_new_messages()
        
        result = ProcessingResult(
            messages_processed=len(messages),
            invoices_found=0,
            invoices_uploaded=0,
            files_quarantined=0,
            errors=[]
        )
        
        for message in messages:
            try:
                self._process_single_message(message, result, dry_run)
            except Exception as e:
                result.errors.append(f"Error processing message {message.message_id}: {str(e)}")
        
        return result
    
    def _process_single_message(
        self, 
        message: EmailMessage, 
        result: ProcessingResult,
        dry_run: bool
    ) -> None:
        """Обработать одно сообщение"""
        for attachment in message.attachments:
            if not self._is_valid_attachment(attachment):
                result.files_quarantined += 1
                if not dry_run:
                    self._file_storage.store_quarantine(attachment)
                continue
                
            # Сохранить файл для парсинга
            file_path = self._file_storage.store_safe(attachment)
            
            # Извлечь данные счета
            parse_result = self._document_parser.parse_invoice(file_path)
            
            if parse_result.success and parse_result.invoice:
                result.invoices_found += 1
                
                # Проверить дубликаты
                if self._repository.claim(parse_result.invoice.invoice_key):
                    if not dry_run:
                        # Здесь должна быть отправка в внешний API
                        pass
                    result.invoices_uploaded += 1
                    
                    if not dry_run:
                        self._repository.mark_done(parse_result.invoice.invoice_key)
    
    def _is_valid_attachment(self, attachment) -> bool:
        """Проверить валидность вложения"""
        # Проверка размера, типа файла, etc
        return True


class InvoiceValidationUseCase:
    """Use case для валидации данных счетов"""
    
    def __init__(self, repository: ProcessedInvoiceRepository):
        self._repository = repository
    
    def validate_invoice_data(self, invoice: Invoice) -> bool:
        """Валидировать данные счета"""
        # Проверки бизнес-правил
        if invoice.amount <= 0:
            return False
        if not invoice.partner_id:
            return False
        return True
