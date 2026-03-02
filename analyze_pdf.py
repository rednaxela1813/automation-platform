#!/usr/bin/env python3
"""Analyze PDF invoice structure for parser tuning"""
import sys
import os
from pathlib import Path
sys.path.insert(0, 'src')

import pdfplumber

def analyze_pdf_structure(pdf_path: Path) -> None:
    """Detailed PDF file structure analysis"""
    print(f"\n📄 Analysis: {pdf_path.name}")
    print("=" * 60)
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            print(f"📊 Page count: {len(pdf.pages)}")
            
            for page_num, page in enumerate(pdf.pages[:2]):  # First 2 pages  
                print(f"\n--- PAGE {page_num + 1} ---")
                
                # Extracting full text
                text = page.extract_text()
                if not text:
                    print("❌ Text not found")
                    continue
                    
                print("📝 Full text:")
                print("-" * 40) 
                print(text[:1000])  # First 1000 characters
                if len(text) > 1000:
                    print(f"\n... (total {len(text)} characters)")
                print("-" * 40)
                
                # Searching key patterns
                print("\n🔍 Key data analysis:")
                
                lines = text.split('\n')
                for i, line in enumerate(lines[:15]):  # First 15 lines
                    line = line.strip()
                    if not line:
                        continue
                        
                    # Searching potential invoice numbers  
                    if any(word in line.lower() for word in ['invoice', 'bill', 'no.', '#']):
                        print(f"  📋 Possible invoice number (line {i+1}): {line}")
                    
                    # Searching amounts (numbers with currency hints)
                    if any(symbol in line for symbol in ['$', '€', '₽', 'USD', 'EUR', 'RUB']):
                        print(f"  💰 Possible amount (line {i+1}): {line}")
                    
                    # Searching dates  
                    if any(char.isdigit() for char in line) and any(separator in line for separator in ['/', '-', '.']):
                        if len([part for part in line.replace('/', ' ').replace('-', ' ').replace('.', ' ').split() if part.isdigit()]) >= 2:
                            print(f"  📅 Possible date (line {i+1}): {line}")
                            
                    # Searching email/company
                    if '@' in line or any(word in line.lower() for word in ['company', 'corp', 'ltd', 'inc']):
                        print(f"  🏢 Possible company (line {i+1}): {line}")
                        
    except Exception as e:
        print(f"❌ Analysis error {pdf_path.name}: {e}")

def main():
    """Analyze all PDF files in storage"""
    print("🔍 PDF INVOICE STRUCTURE ANALYSIS")
    print("=" * 60)
    
    storage_dir = Path('./storage/safe')
    pdf_files = list(storage_dir.glob('*.pdf'))
    
    if not pdf_files:
        print("❌ No PDF files found in ./storage/safe/")
        return
        
    print(f"📄 PDF files found: {len(pdf_files)}")
    
    for pdf_file in pdf_files[:2]:  # Analyzing first 2 files
        analyze_pdf_structure(pdf_file)
        
    print(f"\n✅ Analysis complete. Files analyzed: {min(len(pdf_files), 2)}")

if __name__ == "__main__":
    main()
