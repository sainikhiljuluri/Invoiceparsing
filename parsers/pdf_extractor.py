"""
PDF extraction module with multiple extraction methods and OCR support
"""

import os
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

# PDF processing libraries
try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

try:
    import pytesseract
    from PIL import Image
    import pdf2image
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class ExtractedTable:
    """Container for extracted table data"""
    headers: List[str]
    rows: List[List[str]]
    page_number: int


@dataclass
class PDFContent:
    """Container for extracted PDF content"""
    text: str
    tables: List[ExtractedTable]
    metadata: Dict[str, Any]
    extraction_method: str
    pages: int
    errors: List[str]


class PDFExtractor:
    """Extract text and tables from PDF files using multiple methods"""
    
    def __init__(self):
        self.supported_formats = ['.pdf']
        self.ocr_available = OCR_AVAILABLE
        self.extraction_methods = [
            ('pdfplumber', self._extract_with_pdfplumber),
            ('pypdf2', self._extract_with_pypdf2),
            ('ocr', self._extract_with_ocr)
        ]
        
        # Log available methods
        available_methods = [m[0] for m in self.extraction_methods if self._is_method_available(m[0])]
        logger.info(f"PDFExtractor initialized with methods: {available_methods}")
    
    def extract(self, pdf_path: str) -> PDFContent:
        """Extract content from PDF using best available method"""
        return self.extract_text_from_pdf(pdf_path)
    
    def extract_text_from_pdf(self, pdf_path: str) -> PDFContent:
        """
        Extract text and tables from PDF using multiple methods
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            PDFContent object with extracted data
        """
        # Validate PDF
        is_valid, message = self.validate_pdf(pdf_path)
        if not is_valid:
            return PDFContent(
                text="",
                tables=[],
                metadata={},
                extraction_method="none",
                pages=0,
                errors=[message]
            )
        
        errors = []
        
        # Try each extraction method
        for method_name, method_func in self.extraction_methods:
            if not self._is_method_available(method_name):
                continue
                
            try:
                logger.info(f"Attempting extraction with {method_name}")
                content = method_func(pdf_path)
                
                # If we got meaningful content, return it
                if content and content.text and len(content.text.strip()) > 50:
                    logger.info(f"Successfully extracted with {method_name}")
                    return content
                    
            except Exception as e:
                error_msg = f"{method_name} extraction failed: {str(e)}"
                logger.warning(error_msg)
                errors.append(error_msg)
                continue
        
        # If all methods failed
        return PDFContent(
            text="",
            tables=[],
            metadata={},
            extraction_method="failed",
            pages=0,
            errors=errors
        )
    
    def _is_method_available(self, method_name: str) -> bool:
        """Check if extraction method is available"""
        if method_name == 'pdfplumber':
            return PDFPLUMBER_AVAILABLE
        elif method_name == 'pypdf2':
            return PYPDF2_AVAILABLE
        elif method_name == 'ocr':
            return OCR_AVAILABLE
        return False
    
    def _extract_with_pdfplumber(self, pdf_path: str) -> PDFContent:
        """Extract using pdfplumber (best for tables)"""
        if not PDFPLUMBER_AVAILABLE:
            raise ImportError("pdfplumber not available")
            
        text_content = []
        tables = []
        metadata = {}
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                metadata = {
                    'pages': len(pdf.pages),
                    'metadata': pdf.metadata if hasattr(pdf, 'metadata') else {}
                }
                
                for page_num, page in enumerate(pdf.pages):
                    # Extract text
                    page_text = page.extract_text() or ""
                    text_content.append(page_text)
                    
                    # Extract tables
                    page_tables = page.extract_tables()
                    for table_data in page_tables:
                        if table_data and len(table_data) > 1:
                            # First row as headers
                            headers = [str(cell or "").strip() for cell in table_data[0]]
                            rows = [[str(cell or "").strip() for cell in row] for row in table_data[1:]]
                            
                            table = ExtractedTable(
                                headers=headers,
                                rows=rows,
                                page_number=page_num + 1
                            )
                            tables.append(table)
            
            return PDFContent(
                text="\n\n".join(text_content),
                tables=tables,
                metadata=metadata,
                extraction_method="pdfplumber",
                pages=metadata.get('pages', 0),
                errors=[]
            )
        except Exception as e:
            logger.error(f"pdfplumber extraction error: {e}")
            raise
    
    def _extract_with_pypdf2(self, pdf_path: str) -> PDFContent:
        """Extract using PyPDF2 (fallback method)"""
        if not PYPDF2_AVAILABLE:
            raise ImportError("PyPDF2 not available")
            
        text_content = []
        metadata = {}
        
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                metadata = {
                    'pages': len(pdf_reader.pages),
                    'metadata': pdf_reader.metadata if hasattr(pdf_reader, 'metadata') else {}
                }
                
                for page_num, page in enumerate(pdf_reader.pages):
                    text = page.extract_text()
                    text_content.append(text)
            
            return PDFContent(
                text="\n\n".join(text_content),
                tables=[],  # PyPDF2 doesn't extract tables
                metadata=metadata,
                extraction_method="pypdf2",
                pages=metadata.get('pages', 0),
                errors=[]
            )
        except Exception as e:
            logger.error(f"PyPDF2 extraction error: {e}")
            raise
    
    def _extract_with_ocr(self, pdf_path: str) -> PDFContent:
        """Extract using OCR (for scanned PDFs)"""
        if not OCR_AVAILABLE:
            raise ImportError("OCR libraries not available")
        
        text_content = []
        
        try:
            # Convert PDF to images
            images = pdf2image.convert_from_path(pdf_path)
            
            for page_num, image in enumerate(images):
                # Extract text using OCR
                page_text = pytesseract.image_to_string(image)
                text_content.append(page_text)
                
                logger.info(f"OCR extracted {len(page_text)} characters from page {page_num + 1}")
            
            return PDFContent(
                text="\n\n".join(text_content),
                tables=[],  # OCR doesn't preserve table structure
                metadata={'pages': len(images)},
                extraction_method="ocr",
                pages=len(images),
                errors=[]
            )
            
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            raise
    
    def validate_pdf(self, pdf_path: str) -> Tuple[bool, str]:
        """Validate PDF file exists and is readable"""
        # Check file exists
        if not os.path.exists(pdf_path):
            return False, f"File not found: {pdf_path}"
        
        # Check extension
        if not pdf_path.lower().endswith('.pdf'):
            return False, f"Not a PDF file: {pdf_path}"
        
        # Check file size
        if os.path.getsize(pdf_path) == 0:
            return False, f"Empty file: {pdf_path}"
        
        # Try to open with pdfplumber to verify it's a valid PDF
        if PDFPLUMBER_AVAILABLE:
            try:
                with pdfplumber.open(pdf_path) as pdf:
                    _ = len(pdf.pages)
                return True, "Valid PDF"
            except Exception as e:
                return False, f"Invalid PDF: {str(e)}"
        
        return True, "PDF validation passed"