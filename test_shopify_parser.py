#!/usr/bin/env python3
"""
Тест нового Shopify PDF парсера с реальными файлами
"""

from pathlib import Path
import sys

# Добавляем путь к модулям
sys.path.append('/Users/alexanderkiselev/Documents/programming/automation/automation-platform/src')

from automation.adapters.shopify_pdf_parser import ShopifyPdfInvoiceParser


def test_shopify_parser():
    """Тестируем новый парсер с реальными PDF файлами Shopify"""
    
    parser = ShopifyPdfInvoiceParser()
    
    # Ищем PDF файлы в папке storage/safe
    safe_storage = Path('./storage/safe')
    pdf_files = list(safe_storage.glob('*.pdf'))
    
    print(f"🔍 Найдено PDF файлов: {len(pdf_files)}")
    
    for pdf_file in pdf_files:
        print(f"\n📄 Анализирую файл: {pdf_file.name}")
        print(f"   Размер: {pdf_file.stat().st_size} байт")
        
        # Проверяем, может ли парсер обработать файл
        if not parser.can_parse(pdf_file):
            print("   ❌ Парсер не может обработать этот файл")
            continue
            
        # Извлекаем текст
        try:
            text = parser.extract_text(pdf_file)
            print(f"   📝 Извлечено текста: {len(text)} символов")
            
            # Показываем первые 200 символов
            preview = text[:200].replace('\n', ' ')
            print(f"   📋 Превью: {preview}...")
            
        except Exception as e:
            print(f"   ❌ Ошибка извлечения текста: {e}")
            continue
        
        # Парсим счет
        try:
            parse_result = parser.parse_invoice(pdf_file) 
            
            if parse_result.success:
                invoice = parse_result.invoice
                print(f"   ✅ Счет успешно обработан:")
                print(f"      Партнер: {invoice.partner_id}")
                print(f"      Номер: {invoice.invoice_number}")
                print(f"      Дата: {invoice.invoice_date}")
                print(f"      Сумма: {invoice.amount} {invoice.currency}")
                print(f"      Ключ: {invoice.invoice_key}")
                
                print(f"   📊 Метаданные: {parse_result.metadata}")
                
            else:
                print(f"   ❌ Ошибка парсинга: {parse_result.errors}")
                
        except Exception as e:
            print(f"   ❌ Исключение при парсинге: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    print("🧪 Тест Shopify PDF парсера")
    print("=" * 50)
    
    test_shopify_parser()