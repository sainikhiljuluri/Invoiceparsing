"""
Text cleaning and normalization utilities for invoice processing
"""

import re
import unicodedata
from typing import List, Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class TextCleaner:
    """Clean and normalize text extracted from PDFs"""
    
    @staticmethod
    def clean_text(text: str) -> str:
        """
        Clean and normalize text
        
        Args:
            text: Raw text from PDF
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Normalize unicode characters
        text = unicodedata.normalize('NFKD', text)
        
        # Replace multiple spaces with single space, but preserve line breaks
        text = re.sub(r'[ \t]+', ' ', text)  # Replace multiple spaces/tabs with single space
        text = re.sub(r'\n{3,}', '\n\n', text)  # Limit to max 2 consecutive line breaks
        
        # Remove zero-width spaces and other invisible characters
        text = re.sub(r'[\u200b\u200c\u200d\ufeff]', '', text)
        
        # Fix common OCR errors
        text = TextCleaner.fix_common_ocr_errors(text)
        
        # Remove excessive line breaks
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Trim whitespace
        text = text.strip()
        
        return text
    
    @staticmethod
    def fix_common_ocr_errors(text: str) -> str:
        """Fix common OCR recognition errors"""
        replacements = {
            # Common character substitutions
            'lnvoice': 'Invoice',
            'Ihvoice': 'Invoice',
            '|nvoice': 'Invoice',
            'Arnount': 'Amount',
            'Anount': 'Amount',
            'Ouantity': 'Quantity',
            'Prıce': 'Price',
            'Totai': 'Total',
            'Tota1': 'Total',
            'Subtotai': 'Subtotal',
        }
        
        for wrong, correct in replacements.items():
            text = text.replace(wrong, correct)
        
        return text
    
    @staticmethod
    def normalize_currency(text: str) -> str:
        """Normalize currency symbols and amounts"""
        # Indian Rupee variations
        text = re.sub(r'Rs\.?\s*', '₹', text)
        text = re.sub(r'₹\s+', '₹', text)
        
        # USD variations
        text = re.sub(r'\$\s*USD', '$', text)
        text = re.sub(r'USD\s*\$', '$', text)
        
        # Remove spaces between currency and amount
        text = re.sub(r'([₹$])\s+(\d)', r'\1\2', text)
        
        return text
    
    @staticmethod
    def extract_amount(text: str) -> Tuple[Optional[float], Optional[str]]:
        """
        Extract amount and currency from text
        
        Returns:
            Tuple of (amount, currency) or (None, None) if not found
        """
        if not text:
            return None, None
            
        # Match currency and amount
        patterns = [
            (r'₹\s*([\d,]+\.?\d*)', 'INR'),
            (r'\$\s*([\d,]+\.?\d*)', 'USD'),
            (r'([\d,]+\.?\d*)\s*₹', 'INR'),
            (r'([\d,]+\.?\d*)\s*\$', 'USD'),
            (r'Rs\.?\s*([\d,]+\.?\d*)', 'INR'),
            (r'USD\s*([\d,]+\.?\d*)', 'USD'),
            (r'%\s*([\d,]+\.?\d*)', 'INR'),  # Handle OCR error where ₹ becomes %
        ]
        
        for pattern, currency in patterns:
            match = re.search(pattern, text)
            if match:
                amount_str = match.group(1).replace(',', '')
                try:
                    amount = float(amount_str)
                    return amount, currency
                except ValueError:
                    continue
        
        # Try to find just a number if no currency
        number_match = re.search(r'([\d,]+\.?\d*)', text)
        if number_match:
            amount_str = number_match.group(1).replace(',', '')
            try:
                return float(amount_str), 'UNKNOWN'
            except ValueError:
                pass
        
        return None, None
    
    @staticmethod
    def clean_table_data(table: List[List[str]]) -> List[List[str]]:
        """Clean data extracted from tables"""
        cleaned_table = []
        
        for row in table:
            cleaned_row = []
            for cell in row:
                # Clean each cell
                cleaned_cell = TextCleaner.clean_text(cell)
                cleaned_row.append(cleaned_cell)
            
            # Only add non-empty rows
            if any(cell for cell in cleaned_row):
                cleaned_table.append(cleaned_row)
        
        return cleaned_table
    
    @staticmethod
    def normalize_product_name(name: str) -> str:
        """Normalize product names for matching"""
        if not name:
            return ""
        
        # Convert to uppercase
        name = name.upper()
        
        # Remove special characters except spaces and hyphens
        name = re.sub(r'[^A-Z0-9\s\-]', '', name)
        
        # Normalize spaces
        name = re.sub(r'\s+', ' ', name)
        
        # Common abbreviation expansions - handle both word boundaries and number boundaries
        abbreviations = [
            (r'\bGM\b', 'GRAM'),  # Word boundary GM
            (r'(\d)GM\b', r'\1GRAM'),  # Number followed by GM
            (r'\bKG\b', 'KILOGRAM'),
            (r'(\d)KG\b', r'\1KILOGRAM'),
            (r'\bLB\b', 'POUND'),
            (r'(\d)LB\b', r'\1POUND'),
            (r'\bOZ\b', 'OUNCE'),
            (r'(\d)OZ\b', r'\1OUNCE'),
            (r'\bPKT\b', 'PACKET'),
            (r'\bPCS\b', 'PIECES')
        ]
        
        for pattern, replacement in abbreviations:
            name = re.sub(pattern, replacement, name)
        
        return name.strip()