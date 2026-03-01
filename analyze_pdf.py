#!/usr/bin/env python3
"""Анализ структуры PDF счетов для настройки парсера"""
import sys
import os
from pathlib import Path
sys.path.insert(0, 'src')

import pdfplumber

def analyze_pdf_structure(pdf_path: Path) -> None:
    """Детальный анализ структуры PDF файла"""
    print(f"\n📄 Анализ: {pdf_path.name}")
    print("=" * 60)
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            print(f"📊 Количество страниц: {len(pdf.pages)}")
            
            for page_num, page in enumerate(pdf.pages[:2]):  # Первые 2 страницы  
                print(f"\n--- СТРАНИЦА {page_num + 1} ---")
                
                # Извлекаем весь текст
                text = page.extract_text()
                if not text:
                    print("❌ Текст не найден")
                    continue
                    
                print("📝 Полный текст:")
                print("-" * 40) 
                print(text[:1000])  # Первые 1000 символов
                if len(text) > 1000:
                    print(f"\n... (всего {len(text)} символов)")
                print("-" * 40)
                
                # Поиск ключевых паттернов
                print("\n🔍 Анализ ключевых данных:")
                
                lines = text.split('\n')
                for i, line in enumerate(lines[:15]):  # Первые 15 строк
                    line = line.strip()
                    if not line:
                        continue
                        
                    # Поиск потенциальных номеров счетов  
                    if any(word in line.lower() for word in ['invoice', 'счет', 'bill', 'no.', '#']):
                        print(f"  📋 Возможный номер счета (строка {i+1}): {line}")
                    
                    # Поиск сумм (числа с валютой)
                    if any(symbol in line for symbol in ['$', '€', '₽', 'USD', 'EUR', 'RUB']):
                        print(f"  💰 Возможная сумма (строка {i+1}): {line}")
                    
                    # Поиск дат  
                    if any(char.isdigit() for char in line) and any(separator in line for separator in ['/', '-', '.']):
                        if len([part for part in line.replace('/', ' ').replace('-', ' ').replace('.', ' ').split() if part.isdigit()]) >= 2:
                            print(f"  📅 Возможная дата (строка {i+1}): {line}")
                            
                    # Поиск email/компаний
                    if '@' in line or any(word in line.lower() for word in ['company', 'corp', 'ltd', 'inc']):
                        print(f"  🏢 Возможная компания (строка {i+1}): {line}")
                        
    except Exception as e:
        print(f"❌ Ошибка анализа {pdf_path.name}: {e}")

def main():
    """Анализ всех PDF файлов в storage"""
    print("🔍 АНАЛИЗ СТРУКТУРЫ PDF СЧЕТОВ")
    print("=" * 60)
    
    storage_dir = Path('./storage/safe')
    pdf_files = list(storage_dir.glob('*.pdf'))
    
    if not pdf_files:
        print("❌ PDF файлы не найдены в ./storage/safe/")
        return
        
    print(f"📄 Найдено PDF файлов: {len(pdf_files)}")
    
    for pdf_file in pdf_files[:2]:  # Анализируем первые 2 файла
        analyze_pdf_structure(pdf_file)
        
    print(f"\n✅ Анализ завершен. Проанализировано файлов: {min(len(pdf_files), 2)}")

if __name__ == "__main__":
    main()