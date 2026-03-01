"""
Use Cases для бизнес-логики обработки email и счетов
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Iterable, Any
from dataclasses import dataclass
from datetime import datetime
import json

from automation.domain.models import Invoice, InvoiceStatus
from automation.ports.email import EmailProcessor, EmailMessage  
from automation.ports.repository import ProcessedInvoiceRepository
from automation.ports.document_parser import DocumentParser, ParseResult
from automation.ports.file_storage import FileStorageService, FileStorageResult


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
        document_parser: DocumentParser | Iterable[DocumentParser],
        file_storage: FileStorageService,
    ):
        self._email_processor = email_processor
        self._repository = repository
        if isinstance(document_parser, (list, tuple)):
            self._document_parsers = list(document_parser)
        else:
            self._document_parsers = [document_parser]
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
                # Помечаем письмо как обработанное после успешной обработки
                try:
                    self._email_processor.mark_as_processed(message.message_id)
                except Exception:
                    result.errors.append(f"Failed to mark message as processed: {message.message_id}")
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
            # Сохранить файл с автоматической проверкой безопасности
            result_type, file_path = self._file_storage.store_attachment(attachment)
            
            if result_type == FileStorageResult.QUARANTINE:
                result.files_quarantined += 1
                continue
            elif result_type == FileStorageResult.REJECTED:
                result.errors.append(f"File rejected: {attachment.filename}")
                continue
                
            # Файл сохранен в безопасном хранилище, обрабатываем его
            parser = self._select_parser(file_path)
            if not parser:
                result.errors.append(
                    f"No parser available for file type: {Path(file_path).suffix} ({attachment.filename})"
                )
                continue

            parse_result = parser.parse_invoice(Path(file_path))
            self._write_parse_result(Path(file_path), parse_result)
            
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

    def _write_parse_result(self, file_path: Path, parse_result: ParseResult) -> None:
        """Сохранить результат парсинга рядом с файлом"""
        try:
            invoice = parse_result.invoice
            payload: dict[str, Any] = {
                "parsed_at": datetime.now().isoformat(),
                "success": parse_result.success,
                "errors": parse_result.errors,
                "metadata": parse_result.metadata,
                "invoice": None,
            }

            if invoice:
                payload["invoice"] = {
                    "partner_id": invoice.partner_id,
                    "invoice_number": invoice.invoice_number,
                    "invoice_date": invoice.invoice_date.isoformat(),
                    "amount": str(invoice.amount),
                    "currency": invoice.currency,
                    "source_message_id": invoice.source_message_id,
                    "invoice_key": invoice.invoice_key,
                }

            parsed_path = file_path.with_suffix(".parsed.json")
            with open(parsed_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
        except Exception:
            # Не блокируем основной поток обработки
            return

    def _select_parser(self, file_path: str) -> DocumentParser | None:
        """Выбрать парсер по типу файла"""
        path = Path(file_path)
        for parser in self._document_parsers:
            try:
                if parser.can_parse(path):
                    return parser
            except Exception:
                continue
        return None
    
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
