"""
Оптимизированный PDF парсер для Shopify счетов
"""
from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from datetime import datetime
from pathlib import Path
from typing import Optional

import pdfplumber

from automation.domain.models import Invoice
from automation.ports.document_parser import ParseResult, PDFParser


class ShopifyPdfInvoiceParser:
    """Парсер для извлечения данных счетов Shopify из PDF файлов"""
    
    def can_parse(self, file_path: Path) -> bool:
        """Проверить, может ли парсер обработать файл"""
        return file_path.suffix.lower() == '.pdf'
    
    def parse_invoice(self, file_path: Path) -> ParseResult:
        """Парсить счет из PDF файла"""
        try:
            text = self.extract_text(file_path)
            invoice, extracted = self._extract_invoice_data(text, file_path.name)
            
            if invoice:
                return ParseResult(
                    success=True,
                    invoice=invoice,
                    metadata={
                        'extracted_text_length': len(text),
                        'parser_type': 'shopify_optimized',
                        'extracted_fields': extracted,
                    }
                )
            else:
                return ParseResult(
                    success=False,
                    errors=['Failed to extract invoice data from PDF'],
                    metadata={
                        'extracted_text_length': len(text),
                        'parser_type': 'shopify_optimized',
                        'extracted_fields': extracted,
                    }
                )
                
        except Exception as e:
            return ParseResult(
                success=False,
                errors=[f'PDF parsing error: {str(e)}']
            )
    
    def extract_text(self, file_path: Path) -> str:
        """Извлечь текст из PDF файла"""
        text_content = ""
        
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_content += page_text + "\n"
        
        return text_content
    
    def _extract_invoice_data(self, text: str, source_filename: str) -> tuple[Optional[Invoice], dict]:
        """Извлечь структурированные данные счета из текста (оптимизировано для Shopify)"""
        try:
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            
            # Инициализация данных
            invoice_data = {
                'invoice_number': None,
                'amount': None,
                'currency': None,
                'date': None,
                'partner_id': None,
                'description': ''
            }

            # 1) Invoice number
            invoice_data['invoice_number'] = self._extract_invoice_number(text, source_filename, lines)

            # 2) Date
            invoice_data['date'] = self._extract_date(text, source_filename, lines)

            # 3) Amount + currency
            amount, currency = self._extract_amount_and_currency(text, lines)
            if amount is not None:
                invoice_data['amount'] = amount
            if currency:
                invoice_data['currency'] = currency

            # 4) Partner
            invoice_data['partner_id'] = self._extract_partner(text, source_filename)

            # 5) Description (simple)
            invoice_data['description'] = self._extract_description(lines)
            
            # Проверяем, что основные данные найдены
            if invoice_data['invoice_number'] and invoice_data['amount']:
                try:
                    amount_decimal = invoice_data['amount']
                    invoice_date = self._parse_date(invoice_data['date']) if invoice_data['date'] else datetime.now().date()
                    
                    return Invoice(
                        partner_id=invoice_data['partner_id'] or "unknown_partner",
                        invoice_number=invoice_data['invoice_number'],
                        invoice_date=invoice_date,
                        amount=amount_decimal,
                        currency=invoice_data['currency'] or "EUR",
                        source_message_id=source_filename
                    )
                except (ValueError, TypeError, InvalidOperation) as e:
                    print(f"❌ Ошибка создания Invoice: {e}")
                    return None, invoice_data
                
            print(f"⚠️ Недостаточно данных для парсинга: номер={invoice_data['invoice_number']}, сумма={invoice_data['amount']}")
            return None, invoice_data
            
        except Exception as e:
            print(f"❌ Ошибка парсинга Shopify: {e}")
            return None, {}
    
    def _extract_invoice_number(self, text: str, filename: str, lines: list[str]) -> Optional[str]:
        patterns = [
            r'(?:Invoice|Invoice\s*No\.?|Invoice\s*#|Inv\.?|Bill|Bill\s*#|Order|Order\s*#|Receipt)\s*[:#]?\s*([A-Z0-9][A-Z0-9\-/]+)',
            r'(?:Счет|Счёт|Счет-фактура|СФ|Номер\s*счета)\s*[:#№]?\s*([А-Я0-9][А-Я0-9\-/]+)',
            r'(?:Rechnung|Faktura|Factura)\s*[:#]?\s*([A-Z0-9][A-Z0-9\-/]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        # Fallback: try filename (long digit sequence)
        stem = Path(filename).stem
        digit_match = re.search(r'(\d{6,})', stem)
        if digit_match:
            return digit_match.group(1)

        return None

    def _extract_date(self, text: str, filename: str, lines: list[str]) -> Optional[str]:
        patterns = [
            r'(?:Paid on|Date|Invoice Date|Order Date|Dated)\s*[:#]?\s*([A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4})',
            r'(?:Date|Dated|Invoice Date|Order Date|Дата|от)\s*[:#]?\s*([0-9]{1,2}[./-][0-9]{1,2}[./-][0-9]{2,4})',
            r'([0-9]{4}-[0-9]{2}-[0-9]{2})',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        # Fallback: date in filename (YYYYMMDD)
        stem = Path(filename).stem
        match = re.search(r'(\d{4})(\d{2})(\d{2})', stem)
        if match:
            return f"{match.group(3)}.{match.group(2)}.{match.group(1)}"

        return None

    def _extract_amount_and_currency(self, text: str, lines: list[str]) -> tuple[Optional[Decimal], Optional[str]]:
        keywords = [
            "total due", "amount due", "total amount", "grand total", "total",
            "balance due", "sum", "итого", "сумма"
        ]
        for i, line in enumerate(lines):
            lower = line.lower()
            if any(k in lower for k in keywords):
                amount, currency = self._parse_amount_from_line(line)
                if amount is None and i + 1 < len(lines):
                    amount, currency = self._parse_amount_from_line(lines[i + 1])
                if amount is not None:
                    return amount, currency

        # Fallback: first currency+number pattern in text
        amount, currency = self._parse_amount_from_text(text)
        return amount, currency

    def _parse_amount_from_line(self, line: str) -> tuple[Optional[Decimal], Optional[str]]:
        # Match currency code or symbol near a number
        patterns = [
            r'([€$£¥₽])\s*([0-9][0-9.,\s]*)',
            r'([A-Z]{3})\s*([0-9][0-9.,\s]*)',
            r'([0-9][0-9.,\s]*)\s*([A-Z]{3})',
        ]
        for pattern in patterns:
            match = re.search(pattern, line)
            if match:
                if len(match.groups()) == 2:
                    a, b = match.groups()
                    if re.match(r'[A-Z]{3}|[€$£¥₽]', a):
                        currency = self._normalize_currency(a)
                        amount_str = b
                    else:
                        currency = self._normalize_currency(b)
                        amount_str = a
                    amount = self._parse_decimal_amount(amount_str)
                    if amount is not None:
                        return amount, currency
        return None, None

    def _parse_amount_from_text(self, text: str) -> tuple[Optional[Decimal], Optional[str]]:
        match = re.search(r'([€$£¥₽]|[A-Z]{3})\s*([0-9][0-9.,\s]*)', text)
        if match:
            currency = self._normalize_currency(match.group(1))
            amount = self._parse_decimal_amount(match.group(2))
            return amount, currency
        return None, None

    def _parse_decimal_amount(self, amount_str: str) -> Optional[Decimal]:
        cleaned = amount_str.replace(" ", "").replace("\u00a0", "")
        if not cleaned:
            return None

        # Decide decimal separator
        if "," in cleaned and "." in cleaned:
            if cleaned.rfind(",") > cleaned.rfind("."):
                cleaned = cleaned.replace(".", "").replace(",", ".")
            else:
                cleaned = cleaned.replace(",", "")
        else:
            if cleaned.count(",") == 1 and len(cleaned.split(",")[-1]) in (2, 3):
                cleaned = cleaned.replace(",", ".")
            else:
                cleaned = cleaned.replace(",", "")

        try:
            return Decimal(cleaned)
        except InvalidOperation:
            return None

    def _normalize_currency(self, token: str) -> str:
        token = token.strip()
        symbols = {
            "€": "EUR",
            "$": "USD",
            "£": "GBP",
            "¥": "JPY",
            "₽": "RUB",
        }
        return symbols.get(token, token.upper())

    def _extract_partner(self, text: str, filename: str) -> Optional[str]:
        if "shopify" in text.lower():
            return "shopify"

        # Try "From:" line
        match = re.search(r'(?:From|Seller|Vendor|От|Продавец|Поставщик)\s*[:#]?\s*([^\n]+)', text, re.IGNORECASE)
        if match:
            partner = match.group(1).strip()
            return re.sub(r'\s+', '_', partner).lower()[:50]

        # Fallback: filename prefix
        stem = Path(filename).stem
        prefix = re.sub(r'[_-]+', ' ', stem).strip()
        prefix = re.sub(r'\d+', '', prefix).strip()
        if prefix:
            return re.sub(r'\s+', '_', prefix).lower()[:50]

        return None

    def _extract_description(self, lines: list[str]) -> str:
        for i, line in enumerate(lines):
            if 'OVERVIEW' in line.upper() and i + 1 < len(lines):
                company_line = lines[i + 1]
                company_clean = company_line.replace('Subscription', '').replace('(1 item)', '').strip()
                if company_clean and not company_clean.startswith('€'):
                    return f"Shopify subscription: {company_clean}"
        return ""
            
    def _parse_date(self, date_str: str):
        """Парсить дату из различных форматов"""
        if not date_str:
            return datetime.now().date()
            
        date_formats = [
            '%d.%m.%Y', '%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d',
            '%b %d, %Y', '%B %d, %Y', '%d %b %Y', '%d %B %Y'
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        
        # Если не удалось распарсить, используем текущую дату
        return datetime.now().date()


# Создаем алиас для совместимости
PdfInvoiceParser = ShopifyPdfInvoiceParser
