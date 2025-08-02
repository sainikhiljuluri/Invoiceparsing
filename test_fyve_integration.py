#!/usr/bin/env python3
"""Test Fyve Elements integration"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.vendor_detector import VendorDetector
from parsers import get_parser_for_vendor

# Test vendor detection
print("Testing vendor detection...")
detector = VendorDetector()
text = "Fyve Elements LLC Order # S61972"
result = detector.detect_vendor(text)
print(f"Detected: {result['vendor_key']} (confidence: {result['confidence']})")

# Test parser
print("\nTesting parser...")
parser = get_parser_for_vendor('FYVE_ELEMENTS')
print(f"Parser loaded: {parser.vendor_name}")

# Parse invoice if available
if os.path.exists('uploads/SCAN0123.pdf'):
    print("\nParsing SCAN0123.pdf...")
    result = parser.parse_invoice('uploads/SCAN0123.pdf')
    print(f"Success: {result['success']}")
    print(f"Invoice #: {result.get('invoice_number')}")
    print(f"Products: {len(result.get('products', []))}")
else:
    print("\nNote: Place SCAN0123.pdf in uploads/ folder to test parsing")
