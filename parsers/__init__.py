"""
PDF parsing module for invoice processing
"""

# Base imports
from .pdf_extractor import PDFExtractor, PDFContent, ExtractedTable
from .text_cleaner import TextCleaner

# Import base parser separately to avoid circular import
try:
    from .base_invoice_parser import BaseInvoiceParser
except ImportError:
    BaseInvoiceParser = None

# Vendor-specific parsers
try:
    from .vendor_parsers.nikhil_parser import NikhilParser
except ImportError:
    NikhilParser = None

try:
    from .vendor_parsers.fyve_elements_parser import FyveElementsParser
except ImportError:
    FyveElementsParser = None

# Parser factory
VENDOR_PARSERS = {
    'nikhil_distributors': NikhilParser,
    'NIKHIL_DISTRIBUTORS': NikhilParser,  # Support both formats
    'FYVE_ELEMENTS': FyveElementsParser,
    # Add other vendor parsers as they are implemented
}

def get_parser_for_vendor(vendor_key: str):
    """Get appropriate parser for vendor"""
    parser_class = VENDOR_PARSERS.get(vendor_key)
    if parser_class:
        return parser_class()
    else:
        # Return generic parser or raise error
        raise NotImplementedError(f"No parser available for vendor: {vendor_key}")

__all__ = [
    'PDFExtractor',
    'PDFContent', 
    'ExtractedTable',
    'TextCleaner',
    'BaseInvoiceParser',
    'NikhilParser',
    'FyveElementsParser',
    'get_parser_for_vendor',
    'VENDOR_PARSERS',
]