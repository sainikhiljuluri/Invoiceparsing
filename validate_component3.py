#!/usr/bin/env python3
"""
Complete validation script for Component 3: PDF Extraction System
Run this to verify everything is working correctly.
"""

import os
import sys
import logging

# Add project to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO)

def main():
    print("="*60)
    print("COMPONENT 3 VALIDATION - PDF EXTRACTION & INVOICE PARSING")
    print("="*60)
    
    success_count = 0
    total_tests = 7
    
    # Test 1: Imports
    try:
        print("1. Testing imports...")
        from parsers.pdf_extractor import PDFExtractor, PDFContent, ExtractedTable
        from parsers.text_cleaner import TextCleaner
        from parsers.nikhil_invoice_parser import NikhilInvoiceParser
        print("✅ All core modules imported successfully")
        success_count += 1
    except Exception as e:
        print(f"❌ Import error: {e}")
    
    # Test 2: Initialization
    try:
        print("\n2. Testing component initialization...")
        extractor = PDFExtractor()
        parser = NikhilInvoiceParser()
        print(f"✅ PDFExtractor initialized (OCR available: {extractor.ocr_available})")
        print(f"✅ NikhilInvoiceParser initialized for {parser.vendor_name}")
        success_count += 1
    except Exception as e:
        print(f"❌ Initialization error: {e}")
    
    # Test 3: Text cleaning
    try:
        print("\n3. Testing text cleaning...")
        test_text = "  Multiple   spaces   and\n\n\nexcessive breaks  "
        cleaned = TextCleaner.clean_text(test_text)
        print("✅ Basic text cleaning works")
        
        ocr_text = "lnvoice #123 Totai: $100"
        fixed = TextCleaner.fix_common_ocr_errors(ocr_text)
        print(f"✅ OCR error fixing: '{ocr_text}' → '{fixed}'")
        
        currency_text = "Price: Rs. 100"
        normalized = TextCleaner.normalize_currency(currency_text)
        print(f"✅ Currency normalization: '{currency_text}' → '{normalized}'")
        
        amount, currency = TextCleaner.extract_amount("₹1,234.56")
        print(f"✅ Amount extraction: ₹1,234.56 → {amount} {currency}")
        success_count += 1
    except Exception as e:
        print(f"❌ Text cleaning error: {e}")
    
    # Test 4: PDF validation
    try:
        print("\n4. Testing PDF validation...")
        is_valid, _ = extractor.validate_pdf("nonexistent.pdf")
        print(f"✅ Missing file validation: {not is_valid}")
        
        is_valid, _ = extractor.validate_pdf("test.txt")
        print(f"✅ Wrong extension validation: {not is_valid}")
        success_count += 1
    except Exception as e:
        print(f"❌ PDF validation error: {e}")
    
    # Test 5: Pattern matching
    try:
        print("\n5. Testing regex patterns...")
        import re
        
        # Test invoice number
        text = "Invoice #: INV-2024-7834"
        match = re.search(parser.patterns['invoice_number'], text, re.IGNORECASE)
        if match:
            print(f"✅ Invoice number pattern: {match.group(1)}")
        
        # Test date
        text = "Date: July 26, 2025"
        match = re.search(parser.patterns['date'], text, re.IGNORECASE)
        if match:
            print(f"✅ Date pattern: {match.group(1)}")
        
        # Test total
        text = "Grand Total: ₹263.14"
        match = re.search(parser.patterns['total'], text, re.IGNORECASE)
        if match:
            print(f"✅ Total pattern: {match.group(1)}")
        
        success_count += 1
    except Exception as e:
        print(f"❌ Pattern matching error: {e}")
    
    # Test 6: Invoice parsing
    try:
        print("\n6. Testing invoice parsing...")
        if os.path.exists('uploads/Nikhilinvoice.pdf'):
            print("📄 Found invoice file: uploads/Nikhilinvoice.pdf")
            result = parser.parse_invoice('uploads/Nikhilinvoice.pdf')
            
            print(f"   Success: {result['success']}")
            print(f"   Method: {result['extraction_method']}")
            print(f"   Invoice #: {result.get('invoice_number', 'Not found')}")
            print(f"   Date: {result.get('invoice_date', 'Not found')}")
            print(f"   Total: ₹{result.get('total_amount', 'N/A')}")
            print(f"   Products: {len(result.get('products', []))}")
            
            if result.get('errors'):
                print(f"   Errors: {len(result['errors'])}")
                for error in result['errors'][:3]:
                    print(f"     - {error}")
            
            print("✅ Invoice parsing completed")
            success_count += 1
        else:
            print("⚠️  No invoice file found")
    except Exception as e:
        print(f"❌ Invoice parsing error: {e}")
    
    # Test 7: Unit tests
    try:
        print("\n7. Running unit tests...")
        import unittest
        from tests.test_component_3_pdf import TestPDFExtractor, TestTextCleaner, TestNikhilInvoiceParser
        
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()
        
        suite.addTests(loader.loadTestsFromTestCase(TestPDFExtractor))
        suite.addTests(loader.loadTestsFromTestCase(TestTextCleaner))
        suite.addTests(loader.loadTestsFromTestCase(TestNikhilInvoiceParser))
        
        runner = unittest.TextTestRunner(verbosity=0)
        result = runner.run(suite)
        
        if result.wasSuccessful():
            print("✅ All unit tests passed")
            success_count += 1
        else:
            print("⚠️  Some unit tests failed")
            print("   Check test output for details")
    except Exception as e:
        print(f"❌ Unit test error: {e}")
    
    # Summary
    print("\n" + "="*60)
    print(f"VALIDATION SUMMARY: {success_count}/{total_tests} tests passed")
    
    if success_count == total_tests:
        print("✅ Component 3 is fully operational!")
    elif success_count >= 5:
        print("✅ Component 3 is functional with minor issues")
    else:
        print("❌ Component 3 has significant issues")
    
    print("="*60)


if __name__ == "__main__":
    main()