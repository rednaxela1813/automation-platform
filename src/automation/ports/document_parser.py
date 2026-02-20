"""
Порты для парсинга документов
Определяют интерфейсы для извлечения данных из различных типов файлов
"""
from __future__ import annotations

from typing import Protocol, Optional, Dict, Any
from pathlib import Path
from enum import Enum

from automation.domain.models import Invoice


class DocumentType(str, Enum):
    """Типы поддерживаемых документов"""
    PDF = "pdf"
    XLSX = "xlsx"
    DOCX = "docx"  
    XML = "xml"


class ParseResult:
    """Результат парсинга документа"""
    
    def __init__(self, success: bool, invoice: Optional[Invoice] = None, 
                 errors: Optional[list[str]] = None, metadata: Optional[Dict[str, Any]] = None):
        self.success = success
        self.invoice = invoice
        self.errors = errors or []
        self.metadata = metadata or {}


class DocumentParser(Protocol):
    """Интерфейс для парсинга документов"""
    
    def can_parse(self, file_path: Path) -> bool:
        """Проверить, может ли парсер обработать файл"""
        ...
    
    def parse_invoice(self, file_path: Path) -> ParseResult:
        """Парсить счет из файла"""
        ...
    
    def extract_text(self, file_path: Path) -> str:
        """Извлечь текст из документа"""
        ...


class PDFParser(Protocol):
    """Специализированный парсер для PDF файлов"""
    
    def parse_invoice(self, file_path: Path) -> ParseResult:
        """Парсить счет из PDF"""
        ...


class ExcelParser(Protocol):
    """Специализированный парсер для Excel файлов"""
    
    def parse_invoice(self, file_path: Path) -> ParseResult:
        """Парсить счет из Excel файла"""
        ...


class XMLParser(Protocol):
    """Специализированный парсер для XML файлов"""
    
    def parse_invoice(self, file_path: Path) -> ParseResult:
        """Парсить счет из XML файла"""
        ...