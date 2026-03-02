#!/usr/bin/env python3
"""
Test new Shopify PDF parser with real files
"""

from pathlib import Path
import sys

# Add module path
sys.path.append('/Users/alexanderkiselev/Documents/programming/automation/automation-platform/src')

from automation.adapters.shopify_pdf_parser import ShopifyPdfInvoiceParser


def test_shopify_parser():
    """Test new parser with real PDF files Shopify"""
    
    parser = ShopifyPdfInvoiceParser()
    
    # Search PDF files in storage/safe
    safe_storage = Path('./storage/safe')
    pdf_files = list(safe_storage.glob('*.pdf'))
    
    print(f"🔍 PDF files found: {len(pdf_files)}")
    
    for pdf_file in pdf_files:
        print(f"\n📄 Analyzing file: {pdf_file.name}")
        print(f"   Size: {pdf_file.stat().st_size} bytes")
        
        # Check if parser can process file
        if not parser.can_parse(pdf_file):
            print("   ❌ Parser cannot process this file")
            continue
            
        # Extract text
        try:
            text = parser.extract_text(pdf_file)
            print(f"   📝 Extracted text length: {len(text)} characters")
            
            # Show first 200 characters
            preview = text[:200].replace('\n', ' ')
            print(f"   📋 Preview: {preview}...")
            
        except Exception as e:
            print(f"   ❌ Text extraction error: {e}")
            continue
        
        # Parse invoice
        try:
            parse_result = parser.parse_invoice(pdf_file) 
            
            if parse_result.success:
                invoice = parse_result.invoice
                print(f"   ✅ Invoice processed successfully:")
                print(f"      Partner: {invoice.partner_id}")
                print(f"      Number: {invoice.invoice_number}")
                print(f"      Date: {invoice.invoice_date}")
                print(f"      Amount: {invoice.amount} {invoice.currency}")
                print(f"      Key: {invoice.invoice_key}")
                
                print(f"   📊 Metadata: {parse_result.metadata}")
                
            else:
                print(f"   ❌ Parsing error: {parse_result.errors}")
                
        except Exception as e:
            print(f"   ❌ Parsing exception: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    print("🧪 Shopify PDF parser test")
    print("=" * 50)
    
    test_shopify_parser()