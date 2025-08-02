"""
Specialized parser for Nikhil Distributors invoices
"""

import re
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from .pdf_extractor import PDFExtractor, PDFContent
from .text_cleaner import TextCleaner

logger = logging.getLogger(__name__)


class NikhilInvoiceParser:
    """Parse invoices from Nikhil Distributors"""
    
    def __init__(self):
        self.vendor_name = "NIKHIL DISTRIBUTORS"
        self.currency = "INR"
        self.extractor = PDFExtractor()
        
        # Regex patterns for Nikhil invoice format
        self.patterns = {
            'invoice_number': r'Invoice\s*#?:?\s*(INV-\d{4}-\d{4})',
            'date': r'Date:\s*([A-Za-z]+\s+\d{1,2},\s+\d{4})',
            'total': r'Grand\s*Total:?\s*[₹%]?\s*([\d,]+\.?\d*)',
            'subtotal': r'Subtotal:?\s*[₹%]?\s*([\d,]+\.?\d*)',
            'tax': r'Tax\s*\((\d+)%\s*(?:GST)?\):?\s*[₹%]?\s*([\d,]+\.?\d*)',
            # Updated product patterns to handle OCR variations
            'product_line': [
                r'^(\d+)\s+(.+?)\s+\((\d+)\)\s+(\d+)\s+[₹%]?([\d,]+\.?\d*)\s+[₹%]?([\d,]+\.?\d*)$',
                r'^(\d+)\s+(.+?)\s+(\d+)\s+[₹%]?([\d,]+\.?\d*)\s+[₹%]?([\d,]+\.?\d*)$',
                # Handle OCR variations with different spacing
                r'^(\d+)\s+(.+?)\s*\((\d+)\)\s*(\d+)\s*[₹%]?([\d,]+\.?\d*)\s*[₹%]?([\d,]+\.?\d*)$',
            ]
        }
    
    def parse_invoice(self, pdf_path: str) -> Dict[str, Any]:
        """
        Parse Nikhil Distributors invoice
        
        Args:
            pdf_path: Path to PDF invoice
            
        Returns:
            Dictionary with parsed invoice data
        """
        logger.info(f"Parsing Nikhil invoice: {pdf_path}")
        
        # Extract content from PDF
        extraction_result = self.extractor.extract_text_from_pdf(pdf_path)
        
        # Initialize result
        result = {
            'vendor_name': self.vendor_name,
            'currency': self.currency,
            'extraction_method': extraction_result.extraction_method,
            'success': False,
            'products': [],
            'errors': [],
            'raw_text': extraction_result.text,
            'tables': extraction_result.tables
        }
        
        # If extraction failed
        if not extraction_result.text:
            result['errors'].extend(extraction_result.errors)
            result['errors'].append("No text could be extracted from PDF")
            return result
        
        # Clean the extracted text
        cleaned_text = TextCleaner.clean_text(extraction_result.text)
        result['cleaned_text'] = cleaned_text
        
        # Extract invoice details
        self._extract_invoice_details(cleaned_text, result)
        
        # Extract products from tables if available
        if extraction_result.tables:
            self._extract_products_from_tables(extraction_result.tables, result)
        
        # If no products from tables, try text extraction
        if not result['products']:
            self._extract_products_from_text(cleaned_text, result)
        
        # If still no products, try OCR-specific patterns
        if not result['products'] and extraction_result.extraction_method == 'ocr':
            self._extract_products_ocr_specific(cleaned_text, result)
        
        # Validate the invoice
        self._validate_invoice(result)
        
        # Set success if we have key data
        if result.get('invoice_number'):
            result['success'] = True
        
        logger.info(f"Parsing complete. Success: {result['success']}, Products: {len(result['products'])}")
        
        return result
    
    def _extract_invoice_details(self, text: str, result: Dict):
        """Extract invoice header information"""
        # Invoice number
        match = re.search(self.patterns['invoice_number'], text, re.IGNORECASE)
        if match:
            result['invoice_number'] = match.group(1)
            logger.info(f"Found invoice number: {result['invoice_number']}")
        else:
            result['errors'].append("Invoice number not found")
        
        # Date
        match = re.search(self.patterns['date'], text, re.IGNORECASE)
        if match:
            result['invoice_date'] = match.group(1)
            logger.info(f"Found date: {result['invoice_date']}")
        else:
            result['errors'].append("Invoice date not found")
        
        # Total amount
        match = re.search(self.patterns['total'], text, re.IGNORECASE)
        if match:
            amount_str = match.group(1).replace(',', '')
            try:
                result['total_amount'] = float(amount_str)
                logger.info(f"Found total: ₹{result['total_amount']}")
            except ValueError:
                result['errors'].append(f"Invalid total amount: {amount_str}")
        
        # Subtotal
        match = re.search(self.patterns['subtotal'], text, re.IGNORECASE)
        if match:
            amount_str = match.group(1).replace(',', '')
            try:
                result['subtotal'] = float(amount_str)
            except ValueError:
                pass
        
        # Tax
        match = re.search(self.patterns['tax'], text, re.IGNORECASE)
        if match:
            if match.group(1):  # Tax percentage
                try:
                    result['tax_percentage'] = float(match.group(1))
                except ValueError:
                    pass
            if match.group(2):  # Tax amount
                amount_str = match.group(2).replace(',', '')
                try:
                    result['tax_amount'] = float(amount_str)
                except ValueError:
                    pass
    
    def _extract_products_from_tables(self, tables: List, result: Dict):
        """Extract products from PDF tables"""
        for table in tables:
            # Look for product table (has headers like Product, Quantity, Price)
            headers_lower = [h.lower() for h in table.headers]
            
            # Check if this looks like a product table
            has_product_col = any('product' in h or 'item' in h or 'description' in h for h in headers_lower)
            has_qty_col = any('qty' in h or 'quantity' in h for h in headers_lower)
            has_price_col = any('price' in h or 'rate' in h or 'amount' in h for h in headers_lower)
            
            if has_product_col and (has_qty_col or has_price_col):
                # This is likely the product table
                logger.info(f"Found product table with {len(table.rows)} rows")
                
                # Find column indices
                product_idx = next((i for i, h in enumerate(headers_lower) 
                                  if 'product' in h or 'item' in h or 'description' in h), 0)
                qty_idx = next((i for i, h in enumerate(headers_lower) 
                              if 'qty' in h or 'quantity' in h), -1)
                price_idx = next((i for i, h in enumerate(headers_lower) 
                                if 'unit' in h and 'price' in h), -1)
                total_idx = next((i for i, h in enumerate(headers_lower) 
                                if 'total' in h or 'amount' in h), -1)
                
                # Extract products from rows
                for row in table.rows:
                    if len(row) <= product_idx:
                        continue
                    
                    product_text = row[product_idx]
                    
                    # Skip if it's a total row
                    if any(keyword in product_text.lower() for keyword in ['total', 'subtotal', 'tax']):
                        continue
                    
                    # Parse product with pack size
                    product_match = re.match(r'(.+?)\s*\((\d+)\)$', product_text)
                    if product_match:
                        product_name = product_match.group(1).strip()
                        units = int(product_match.group(2))
                    else:
                        product_name = product_text
                        units = 1
                    
                    # Extract other fields
                    quantity = 1
                    if qty_idx >= 0 and qty_idx < len(row):
                        try:
                            quantity = int(row[qty_idx])
                        except ValueError:
                            pass
                    
                    unit_price = 0.0
                    if price_idx >= 0 and price_idx < len(row):
                        amount, _ = TextCleaner.extract_amount(row[price_idx])
                        unit_price = amount
                    
                    total = 0.0
                    if total_idx >= 0 and total_idx < len(row):
                        amount, _ = TextCleaner.extract_amount(row[total_idx])
                        total = amount
                    
                    # Calculate cost per unit
                    cost_per_unit = unit_price / units if units > 0 else unit_price
                    
                    product = {
                        'product_name': product_name,
                        'units': units,
                        'quantity': quantity,
                        'unit_price': unit_price,
                        'total': total,
                        'cost_per_unit': round(cost_per_unit, 2)
                    }
                    
                    result['products'].append(product)
                    logger.info(f"Extracted product: {product_name} ({units} units)")
    
    def _extract_products_from_text(self, text: str, result: Dict):
        """Extract products from text using regex patterns"""
        lines = text.split('\n')
        
        # Try each product pattern
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Try each pattern variant
            for pattern in self.patterns['product_line']:
                match = re.match(pattern, line)
                if match:
                    try:
                        groups = match.groups()
                        if len(groups) == 6:  # Pattern with pack size
                            sr_no = groups[0]
                            product_name = groups[1].strip()
                            units = int(groups[2])
                            quantity = int(groups[3])
                            unit_price_str = groups[4].replace(',', '')
                            total_str = groups[5].replace(',', '')
                        else:  # Pattern without pack size
                            sr_no = groups[0]
                            product_name = groups[1].strip()
                            units = 1
                            quantity = int(groups[2])
                            unit_price_str = groups[3].replace(',', '')
                            total_str = groups[4].replace(',', '')
                        
                        # Check if product name has pack size at the end
                        pack_match = re.search(r'(.+?)\s*\((\d+)\)$', product_name)
                        if pack_match:
                            product_name = pack_match.group(1).strip()
                            units = int(pack_match.group(2))
                        
                        unit_price = float(unit_price_str)
                        total = float(total_str)
                        cost_per_unit = unit_price / units if units > 0 else unit_price
                        
                        product = {
                            'sr_no': int(sr_no),
                            'product_name': product_name,
                            'units': units,
                            'quantity': quantity,
                            'unit_price': unit_price,
                            'total': total,
                            'cost_per_unit': round(cost_per_unit, 2)
                        }
                        
                        result['products'].append(product)
                        logger.info(f"Extracted product from text: {product_name}")
                        break
                        
                    except ValueError as e:
                        logger.warning(f"Failed to parse product line: {line} - {e}")
    
    def _extract_products_ocr_specific(self, text: str, result: Dict):
        """Extract products using OCR-specific patterns"""
        # Look for product patterns in OCR text
        # This handles cases where OCR might misread characters
        
        # Find lines that look like product entries
        lines = text.split('\n')
        for i, line in enumerate(lines):
            # Look for lines starting with numbers (product serial)
            if re.match(r'^\d+\s+\w+', line):
                # Try to extract product info
                # OCR might read ₹ as %, 7OZ as 70Z, etc.
                simplified_pattern = r'^(\d+)\s+(.+?)\s+(\d+)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)$'
                match = re.match(simplified_pattern, line)
                
                if match:
                    try:
                        sr_no = match.group(1)
                        product_info = match.group(2).strip()
                        quantity = int(match.group(3))
                        unit_price = float(match.group(4).replace(',', ''))
                        total = float(match.group(5).replace(',', ''))
                        
                        # Extract pack size if present
                        pack_match = re.search(r'\((\d+)\)', product_info)
                        if pack_match:
                            units = int(pack_match.group(1))
                            product_name = re.sub(r'\s*\(\d+\)', '', product_info).strip()
                        else:
                            units = 1
                            product_name = product_info
                        
                        # Clean product name
                        product_name = re.sub(r'[0O]Z\b', 'OZ', product_name)  # Fix O/0 confusion
                        product_name = re.sub(r'7OZ', '7OZ', product_name)
                        
                        cost_per_unit = unit_price / units if units > 0 else unit_price
                        
                        product = {
                            'sr_no': int(sr_no),
                            'product_name': product_name,
                            'units': units,
                            'quantity': quantity,
                            'unit_price': unit_price,
                            'total': total,
                            'cost_per_unit': round(cost_per_unit, 2)
                        }
                        
                        result['products'].append(product)
                        logger.info(f"Extracted product via OCR pattern: {product_name}")
                        
                    except ValueError as e:
                        logger.debug(f"OCR pattern failed for line: {line} - {e}")
    
    def _validate_invoice(self, result: Dict):
        """Validate invoice totals and calculations"""
        if not result['products']:
            result['errors'].append("No products found")
            return
        
        # Calculate total from products
        calculated_total = sum(p.get('total', 0) for p in result['products'])
        
        # If we have a subtotal, compare
        if result.get('subtotal') and abs(calculated_total - result['subtotal']) > 0.01:
            result['errors'].append(
                f"Subtotal mismatch: calculated {calculated_total:.2f} vs stated {result['subtotal']:.2f}"
            )
        
        # Verify individual product calculations
        for i, product in enumerate(result['products']):
            expected_total = product['quantity'] * product['unit_price']
            if 'total' in product and abs(expected_total - product['total']) > 0.01:
                result['errors'].append(
                    f"Product {i+1} total mismatch: calculated {expected_total:.2f} vs stated {product['total']:.2f}"
                )