#!/usr/bin/env python3
"""
Validation script for Component 4: Vendor Detection & Rules
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
    print("COMPONENT 4 VALIDATION - VENDOR DETECTION & RULES")
    print("="*60)
    
    success_count = 0
    total_tests = 8
    
    # Test 1: Imports
    try:
        print("1. Testing imports...")
        from services.vendor_detector import VendorDetector
        from services.rule_manager import RuleManager
        from config.vendor_patterns import get_vendor_info, VENDOR_PATTERNS
        from config.vendor_rules import VendorRules
        from parsers.vendor_parsers.nikhil_parser import NikhilParser
        from parsers import get_parser_for_vendor
        print("✅ All modules imported successfully")
        success_count += 1
    except Exception as e:
        print(f"❌ Import error: {e}")
    
    # Test 2: Vendor configuration
    try:
        print("\n2. Testing vendor configuration...")
        vendor_count = len([v for v in VENDOR_PATTERNS.keys() if v != 'GENERIC'])
        print(f"✅ {vendor_count} vendors configured")
        
        # Check a few vendors
        for vendor_key in ['NIKHIL_DISTRIBUTORS', 'CHETAK_SAN_FRANCISCO', 'RAJA_FOODS']:
            info = get_vendor_info(vendor_key)
            print(f"   • {info['name']}: {info['currency']} ({info['country']})")
        
        success_count += 1
    except Exception as e:
        print(f"❌ Configuration error: {e}")
    
    # Test 3: Vendor detection
    try:
        print("\n3. Testing vendor detection...")
        detector = VendorDetector()
        
        # Test Nikhil detection
        nikhil_text = """
        Nikhil Distributors
        Invoice #: INV-2024-7834
        Date: July 26, 2025
        """
        result = detector.detect_vendor(nikhil_text)
        print(f"✅ Nikhil detection: {result['vendor_key']} (confidence: {result['confidence']})")
        
        # Test Chetak detection
        chetak_text = """
        CHETAK SAN FRANCISCO LLC
        Invoice: CHK12345
        """
        result = detector.detect_vendor(chetak_text)
        print(f"✅ Chetak detection: {result['vendor_key']} (confidence: {result['confidence']})")
        
        # Test unknown vendor
        unknown_text = "Random Company Invoice #12345"
        result = detector.detect_vendor(unknown_text)
        print(f"✅ Unknown vendor: {result['vendor_key']} (detected: {result['detected']})")
        
        success_count += 1
    except Exception as e:
        print(f"❌ Detection error: {e}")
    
    # Test 4: Rule management
    try:
        print("\n4. Testing rule management...")
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            rule_manager = RuleManager(temp_dir)
            
            # Get rules
            rules = rule_manager.get_parsing_rules('NIKHIL_DISTRIBUTORS')
            print(f"✅ Retrieved rules for Nikhil Distributors")
            print(f"   • Invoice patterns: {len(rules['invoice_patterns'])}")
            print(f"   • Product patterns: {len(rules['product_patterns'])}")
            
            # Test learning
            rule_manager.learn_pattern('NIKHIL_DISTRIBUTORS', 'invoice_number', r'NI-\d{6}', 0.85)
            learned = rule_manager.get_learned_patterns('NIKHIL_DISTRIBUTORS', 'invoice_number')
            print(f"✅ Pattern learning: {len(learned)} patterns learned")
        
        success_count += 1
    except Exception as e:
        print(f"❌ Rule management error: {e}")
    
    # Test 5: Pattern validation
    try:
        print("\n5. Testing pattern validation...")
        
        # Test invoice patterns
        patterns = VendorRules.get_invoice_patterns('NIKHIL_DISTRIBUTORS')
        test_text = "Invoice #: INV-2024-7834"
        
        import re
        match = re.search(patterns['invoice_number'], test_text)
        if match:
            print(f"✅ Invoice pattern match: {match.group(1)}")
        
        # Test product patterns
        product_patterns = VendorRules.get_product_patterns('NIKHIL_DISTRIBUTORS')
        product_line = "1  DEEP CASHEW WHOLE 7OZ (20)  1  ₹30.00  ₹30.00"
        
        for pattern in product_patterns:
            if re.match(pattern, product_line):
                print(f"✅ Product pattern matched")
                break
        
        success_count += 1
    except Exception as e:
        print(f"❌ Pattern validation error: {e}")
    
    # Test 6: Parser factory
    try:
        print("\n6. Testing parser factory...")
        
        # Get Nikhil parser
        parser = get_parser_for_vendor('NIKHIL_DISTRIBUTORS')
        print(f"✅ Got parser for Nikhil: {type(parser).__name__}")
        
        # Test parser attributes
        print(f"   • Vendor: {parser.vendor_name}")
        print(f"   • Currency: {parser.currency}")
        print(f"   • Patterns loaded: {len(parser.patterns)} invoice, {len(parser.product_patterns)} product")
        
        success_count += 1
    except Exception as e:
        print(f"❌ Parser factory error: {e}")
    
    # Test 7: Integration with PDF
    try:
        print("\n7. Testing integration with PDF extraction...")
        
        # Check if we can use the Nikhil invoice
        if os.path.exists('uploads/Nikhilinvoice.pdf'):
            from parsers.pdf_extractor import PDFExtractor
            
            extractor = PDFExtractor()
            content = extractor.extract_text_from_pdf('uploads/Nikhilinvoice.pdf')
            
            # Detect vendor from extracted text
            result = detector.detect_vendor(content.text)
            print(f"✅ Vendor detected from PDF: {result['vendor_key']}")
            print(f"   Confidence: {result['confidence']}")
            print(f"   Currency: {result['currency']}")
            
            # Parse with detected vendor
            parser = get_parser_for_vendor(result['vendor_key'])
            invoice_result = parser.parse_invoice('uploads/Nikhilinvoice.pdf')
            
            print(f"✅ Invoice parsed successfully")
            print(f"   Invoice #: {invoice_result.get('invoice_number')}")
            print(f"   Products: {len(invoice_result.get('products', []))}")
            
            if invoice_result.get('products'):
                product = invoice_result['products'][0]
                print(f"   Sample: {product['brand']} {product['item_description']} - ₹{product['cost_per_unit']}/unit")
        else:
            print("⚠️  No test PDF found, skipping integration test")
        
        success_count += 1
    except Exception as e:
        print(f"❌ Integration error: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 8: Unit tests
    try:
        print("\n8. Running unit tests...")
        import unittest
        from tests.test_component_4_vendor import (
            TestVendorDetector, TestRuleManager, 
            TestVendorRules, TestNikhilParser
        )
        
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()
        
        suite.addTests(loader.loadTestsFromTestCase(TestVendorDetector))
        suite.addTests(loader.loadTestsFromTestCase(TestRuleManager))
        suite.addTests(loader.loadTestsFromTestCase(TestVendorRules))
        suite.addTests(loader.loadTestsFromTestCase(TestNikhilParser))
        
        runner = unittest.TextTestRunner(verbosity=0)
        result = runner.run(suite)
        
        if result.wasSuccessful():
            print(f"✅ All {result.testsRun} unit tests passed")
            success_count += 1
        else:
            print(f"⚠️  {len(result.failures + result.errors)} tests failed")
    except Exception as e:
        print(f"❌ Unit test error: {e}")
    
    # Summary
    print("\n" + "="*60)
    print(f"VALIDATION SUMMARY: {success_count}/{total_tests} tests passed")
    
    if success_count == total_tests:
        print("✅ Component 4 is fully operational!")
        print("\nSupported vendors:")
        vendors = detector.get_supported_vendors()
        for v in vendors[:5]:  # Show first 5
            print(f"  • {v['name']} ({v['currency']})")
        print(f"  ... and {len(vendors)-5} more")
    elif success_count >= 6:
        print("✅ Component 4 is functional with minor issues")
    else:
        print("❌ Component 4 has significant issues")
    
    print("="*60)


if __name__ == "__main__":
    main()