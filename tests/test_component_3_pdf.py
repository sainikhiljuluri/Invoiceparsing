"""
Unit tests for Component 3: PDF Extraction System
"""

import unittest
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.pdf_extractor import PDFExtractor, PDFContent, ExtractedTable
from parsers.text_cleaner import TextCleaner
from parsers.nikhil_invoice_parser import NikhilInvoiceParser


class TestPDFExtractor(unittest.TestCase):
    """Test PDF extraction functionality"""
    
    def setUp(self):
        self.extractor = PDFExtractor()
        self.test_pdf_path = "test_invoice.pdf"
    
    def test_initialization(self):
        """Test PDFExtractor initialization"""
        self.assertEqual(self.extractor.supported_formats, ['.pdf'])
        self.assertIsInstance(self.extractor.extraction_methods, list)
        self.assertTrue(hasattr(self.extractor, 'ocr_available'))
    
    def test_validate_pdf_missing_file(self):
        """Test validation of missing PDF file"""
        is_valid, message = self.extractor.validate_pdf("nonexistent.pdf")
        self.assertFalse(is_valid)
        self.assertIn("File not found", message)
    
    def test_validate_pdf_wrong_extension(self):
        """Test validation of non-PDF file"""
        is_valid, message = self.extractor.validate_pdf("test.txt")
        self.assertFalse(is_valid)
        self.assertTrue("not a pdf" in message.lower() or "file not found" in message.lower())
    
    @patch('os.path.exists')
    @patch('os.path.getsize')
    def test_validate_pdf_empty_file(self, mock_getsize, mock_exists):
        """Test validation of empty PDF file"""
        mock_exists.return_value = True
        mock_getsize.return_value = 0
        
        is_valid, message = self.extractor.validate_pdf("empty.pdf")
        self.assertFalse(is_valid)
        self.assertIn("Empty file", message)


class TestTextCleaner(unittest.TestCase):
    """Test text cleaning functionality"""
    
    def test_clean_text_basic(self):
        """Test basic text cleaning"""
        dirty_text = "  Multiple   spaces   and\n\n\nexcessive breaks  "
        clean = TextCleaner.clean_text(dirty_text)
        self.assertEqual(clean, "Multiple spaces and\n\nexcessive breaks")
    
    def test_fix_ocr_errors(self):
        """Test OCR error correction"""
        ocr_text = "lnvoice #123 Totai: $100"
        fixed = TextCleaner.fix_common_ocr_errors(ocr_text)
        self.assertEqual(fixed, "Invoice #123 Total: $100")
    
    def test_normalize_currency(self):
        """Test currency normalization"""
        text = "Price: Rs. 100 or ₹ 200"
        normalized = TextCleaner.normalize_currency(text)
        # Check that Rs. is converted to ₹
        self.assertIn("₹100", normalized)
        self.assertNotIn("Rs.", normalized)
    
    def test_extract_amount_inr(self):
        """Test INR amount extraction"""
        amount, currency = TextCleaner.extract_amount("₹1,234.56")
        self.assertEqual(amount, 1234.56)
        self.assertEqual(currency, "INR")
    
    def test_extract_amount_usd(self):
        """Test USD amount extraction"""
        amount, currency = TextCleaner.extract_amount("$99.99")
        self.assertEqual(amount, 99.99)
        self.assertEqual(currency, "USD")
    
    def test_normalize_product_name(self):
        """Test product name normalization"""
        name = "Deep Cashew 500gm"
        normalized = TextCleaner.normalize_product_name(name)
        # GM should be expanded when it's a separate word
        self.assertEqual(normalized, "DEEP CASHEW 500GRAM")


class TestNikhilInvoiceParser(unittest.TestCase):
    """Test Nikhil invoice parser"""
    
    def setUp(self):
        self.parser = NikhilInvoiceParser()
    
    def test_initialization(self):
        """Test parser initialization"""
        self.assertEqual(self.parser.vendor_name, "NIKHIL DISTRIBUTORS")
        self.assertEqual(self.parser.currency, "INR")
        self.assertIsInstance(self.parser.patterns, dict)
    
    def test_pattern_matching_invoice_number(self):
        """Test invoice number pattern matching"""
        import re
        text = "Invoice #: INV-2024-7834"
        match = re.search(self.parser.patterns['invoice_number'], text, re.IGNORECASE)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), "INV-2024-7834")
    
    def test_pattern_matching_date(self):
        """Test date pattern matching"""
        import re
        text = "Date: July 26, 2025"
        match = re.search(self.parser.patterns['date'], text, re.IGNORECASE)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), "July 26, 2025")
    
    def test_pattern_matching_total(self):
        """Test total amount pattern matching"""
        import re
        text = "Grand Total: ₹263.14"
        match = re.search(self.parser.patterns['total'], text, re.IGNORECASE)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), "263.14")
    
    @patch('parsers.nikhil_invoice_parser.PDFExtractor')
    def test_parse_invoice_no_text(self, mock_extractor_class):
        """Test parsing with no extracted text"""
        # Setup mock
        mock_extractor = Mock()
        mock_extractor_class.return_value = mock_extractor
        
        # Create a proper PDFContent object
        mock_content = PDFContent(
            text="",
            tables=[],
            metadata={},
            extraction_method="failed",
            pages=0,
            errors=["No text extracted"]
        )
        
        mock_extractor.extract_text_from_pdf.return_value = mock_content
        
        # Create parser and parse
        parser = NikhilInvoiceParser()
        result = parser.parse_invoice("test.pdf")
        
        # Assertions
        self.assertFalse(result['success'])
        self.assertTrue(any("No text could be extracted" in error for error in result['errors']))


if __name__ == '__main__':
    unittest.main()