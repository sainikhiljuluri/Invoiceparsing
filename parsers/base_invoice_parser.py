"""
Base invoice parser class that all vendor parsers inherit from
"""

import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from abc import ABC, abstractmethod

from parsers.pdf_extractor import PDFExtractor, PDFContent
from parsers.text_cleaner import TextCleaner
from config.vendor_rules import VendorRules

logger = logging.getLogger(__name__)


class BaseInvoiceParser(ABC):
    """Base class for all invoice parsers"""
    
    def __init__(self, vendor_key: str, vendor_name: str, currency: str):
        self.vendor_key = vendor_key
        self.vendor_name = vendor_name
        self.currency = currency
        self.extractor = PDFExtractor()
        
        # Get vendor-specific patterns
        self.patterns = VendorRules.get_invoice_patterns(vendor_key)
        self.product_patterns = VendorRules.get_product_patterns(vendor_key)
        self.validation_rules = VendorRules.get_validation_rules(vendor_key)
    
    def parse_invoice(self, pdf_path: str) -> Dict[str, Any]:
        """
        Parse invoice with vendor-specific rules
        
        Args:
            pdf_path: Path to PDF invoice
            
        Returns:
            Dictionary with parsed invoice data
        """
        logger.info(f"Parsing {self.vendor_name} invoice: {pdf_path}")
        
        # Extract content from PDF
        extraction_result = self.extractor.extract_text_from_pdf(pdf_path)
        
        # Initialize result
        result = {
            'vendor_key': self.vendor_key,
            'vendor_name': self.vendor_name,
            'currency': self.currency,
            'extraction_method': extraction_result.extraction_method,
            'success': False,
            'products': [],
            'errors': [],
            'warnings': [],
            'raw_text': extraction_result.text,
            'tables': extraction_result.tables,
            'metadata': {}
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
        
        # Extract vendor-specific fields
        self._extract_vendor_specific_fields(cleaned_text, result)
        
        # Extract products
        self._extract_products(cleaned_text, extraction_result.tables, result)
        
        # Validate the invoice
        self._validate_invoice(result)
        
        # Set success if we have key data
        if result.get('invoice_number'):
            result['success'] = True
        
        # Post-process results
        self._post_process(result)
        
        logger.info(f"Parsing complete. Success: {result['success']}, Products: {len(result['products'])}")
        
        return result
    
    def _extract_invoice_details(self, text: str, result: Dict):
        """Extract standard invoice fields"""
        # Invoice number
        if 'invoice_number' in self.patterns:
            match = re.search(self.patterns['invoice_number'], text, re.IGNORECASE)
            if match:
                result['invoice_number'] = match.group(1)
                logger.info(f"Found invoice number: {result['invoice_number']}")
            else:
                result['errors'].append("Invoice number not found")
        
        # Date
        if 'date' in self.patterns:
            match = re.search(self.patterns['date'], text, re.IGNORECASE)
            if match:
                result['invoice_date'] = match.group(1)
                logger.info(f"Found date: {result['invoice_date']}")
            else:
                result['errors'].append("Invoice date not found")
        
        # Total amount
        if 'total' in self.patterns:
            match = re.search(self.patterns['total'], text, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(',', '')
                try:
                    result['total_amount'] = float(amount_str)
                    logger.info(f"Found total: {self.currency} {result['total_amount']}")
                except ValueError:
                    result['errors'].append(f"Invalid total amount: {amount_str}")
        
        # Subtotal
        if 'subtotal' in self.patterns:
            match = re.search(self.patterns['subtotal'], text, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(',', '')
                try:
                    result['subtotal'] = float(amount_str)
                except ValueError:
                    pass
        
        # Tax
        if 'tax' in self.patterns:
            match = re.search(self.patterns['tax'], text, re.IGNORECASE)
            if match:
                # Tax might have percentage and amount
                groups = match.groups()
                if len(groups) >= 1 and groups[0]:
                    try:
                        result['tax_percentage'] = float(groups[0])
                    except ValueError:
                        pass
                
                if len(groups) >= 2 and groups[1]:
                    amount_str = groups[1].replace(',', '')
                    try:
                        result['tax_amount'] = float(amount_str)
                    except ValueError:
                        pass
    
    @abstractmethod
    def _extract_vendor_specific_fields(self, text: str, result: Dict):
        """Extract vendor-specific fields - must be implemented by subclasses"""
        pass
    
    def _extract_products(self, text: str, tables: List, result: Dict):
        """Extract products using vendor patterns"""
        # First try table extraction
        if tables:
            self._extract_products_from_tables(tables, result)
        
        # If no products from tables, try text patterns
        if not result['products']:
            self._extract_products_from_text(text, result)
    
    def _extract_products_from_tables(self, tables: List, result: Dict):
        """Extract products from tables - can be overridden"""
        # Default implementation
        # Subclasses can override for vendor-specific table handling
        pass
    
    def _extract_products_from_text(self, text: str, result: Dict):
        """Extract products from text using patterns"""
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Try each product pattern
            for pattern in self.product_patterns:
                match = re.match(pattern, line)
                if match:
                    product = self._parse_product_match(match, pattern)
                    if product:
                        result['products'].append(product)
                        logger.debug(f"Extracted product: {product.get('product_name')}")
                    break
    
    @abstractmethod
    def _parse_product_match(self, match: re.Match, pattern: str) -> Optional[Dict]:
        """Parse product from regex match - must be implemented by subclasses"""
        pass
    
    def _validate_invoice(self, result: Dict):
        """Validate invoice data"""
        # Check required fields
        if not result.get('invoice_number'):
            result['warnings'].append("Missing invoice number")
        
        if not result.get('invoice_date'):
            result['warnings'].append("Missing invoice date")
        
        # Validate products
        if not result['products']:
            result['errors'].append("No products found")
        else:
            # Validate each product
            for i, product in enumerate(result['products']):
                # Price validation
                price = product.get('unit_price', 0)
                min_price = self.validation_rules.get('min_product_price', 0.01)
                max_price = self.validation_rules.get('max_product_price', 10000)
                
                if price < min_price or price > max_price:
                    result['warnings'].append(
                        f"Product {i+1} price {price} outside expected range"
                    )
                
                # Quantity validation
                qty = product.get('quantity', 0)
                min_qty = self.validation_rules.get('min_quantity', 1)
                max_qty = self.validation_rules.get('max_quantity', 10000)
                
                if qty < min_qty or qty > max_qty:
                    result['warnings'].append(
                        f"Product {i+1} quantity {qty} outside expected range"
                    )
        
        # Validate totals
        if result.get('products') and result.get('subtotal'):
            calculated_total = sum(p.get('total', 0) for p in result['products'])
            stated_subtotal = result['subtotal']
            
            if abs(calculated_total - stated_subtotal) > 0.01:
                result['warnings'].append(
                    f"Subtotal mismatch: calculated {calculated_total:.2f} vs stated {stated_subtotal:.2f}"
                )
    
    def _post_process(self, result: Dict):
        """Post-process results - can be overridden"""
        # Add any final processing
        # Calculate statistics
        if result['products']:
            result['metadata']['product_count'] = len(result['products'])
            result['metadata']['total_quantity'] = sum(
                p.get('quantity', 0) for p in result['products']
            )