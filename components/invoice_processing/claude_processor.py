"""
Component 6: Claude AI Integration for Invoice Processing
Processes any vendor invoice format using Claude Sonnet
"""

import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import os
from anthropic import Anthropic
from supabase import create_client, Client
from dotenv import load_dotenv

# Import from existing components
from parsers.pdf_extractor import PDFExtractor
from services.vendor_detector import VendorDetector
from config.vendor_rules import VendorRules

load_dotenv()
logger = logging.getLogger(__name__)


@dataclass
class InvoiceProduct:
    """Product extracted from invoice"""
    line_number: int
    product_name: str
    quantity: int
    unit_price: float
    total: float
    units_per_pack: Optional[int] = None
    cost_per_unit: Optional[float] = None
    raw_text: Optional[str] = None


# Alias for backward compatibility
InvoiceItem = InvoiceProduct

@dataclass
class ProcessedInvoice:
    """Processed invoice data"""
    vendor_key: str
    vendor_name: str
    invoice_number: str
    invoice_date: str
    subtotal: float
    tax_amount: float
    total_amount: float
    currency: str
    products: List[InvoiceProduct]
    metadata: Dict[str, Any]
    confidence: float
    processing_method: str


class ClaudeInvoiceProcessor:
    """Process invoices using Claude AI"""
    
    def __init__(self):
        # Initialize clients
        self.anthropic = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        self.supabase = create_client(
            os.getenv('SUPABASE_URL'),
            os.getenv('SUPABASE_SERVICE_KEY')
        )
        
        # Initialize components
        self.pdf_extractor = PDFExtractor()
        self.vendor_detector = VendorDetector()
        
        # Claude model from environment variable
        self.claude_model = os.getenv('CLAUDE_MODEL', 'claude-2.1')
        
        # Processing stats
        self.stats = {
            'invoices_processed': 0,
            'products_extracted': 0,
            'errors': 0
        }
    
    def build_claude_prompt(self, vendor_info: Dict, pdf_text: str) -> str:
        """Build vendor-specific prompt for Claude"""
        
        # Get vendor-specific rules
        vendor_key = vendor_info['vendor_key']
        rules = VendorRules.get_product_config(vendor_key)
        
        prompt = f"""You are processing an invoice from {vendor_info['vendor_name']}.

VENDOR INFORMATION:
- Name: {vendor_info['vendor_name']}
- Currency: {vendor_info['currency']}
- Country: {vendor_info['country']}

EXTRACTION REQUIREMENTS:
1. Extract the invoice number and date
2. Extract all products from the invoice
3. Calculate totals and verify math
4. Return structured JSON data

CRITICAL RULES FOR THIS VENDOR:
"""
        
        # Add vendor-specific rules
        if vendor_key == 'NIKHIL_DISTRIBUTORS':
            prompt += """
- Products have format: "PRODUCT NAME (UNITS_PER_PACK)"
- Example: "DEEP CASHEW WHOLE 7OZ (20)" means 20 units per pack
- Extract the number in parentheses as units_per_pack
- Calculate: cost_per_unit = unit_price / units_per_pack
- Currency is INR (₹)
- Invoice format: INV-YYYY-XXXX

CRITICAL PRICE EXTRACTION RULES:
- Look for table columns: S.No | Product Name | Qty | Unit Price | Total
- Unit Price column contains the price per single unit (e.g., ₹30.00)
- Total column contains quantity × unit price (e.g., ₹30.00)
- DO NOT confuse Unit Price with Total - they are different columns
- Verify: quantity × unit_price should equal total
- If unit_price seems too high, double-check you're reading the Unit Price column, not Total
"""
        elif vendor_key == 'CHETAK_SAN_FRANCISCO':
            prompt += """
- Products may have abbreviated names
- Expand: Pwd→Powder, Whl→Whole, Grn→Green
- Currency is USD ($)
- Invoice format: CHK followed by numbers
"""
        elif vendor_key == 'FYVE_ELEMENTS':
            prompt += """
- Invoice number is the Order Number (format: S#### like S61972)
- Look for "Order #" or "Order Number" followed by S and numbers
- Products have format: "Brand Item Size x Units" (e.g., "24M Organic Rice 10Lb x 4")
- Convert "24M" to "24 Mantra" in product names
- Extract units from "x 4" patterns and calculate cost_per_unit = unit_price / units
- Currency is USD ($)
- Date format: MM/DD/YYYY
"""
        else:
            prompt += """
- Extract product names exactly as shown
- Look for quantity, unit price, and total columns
- Verify that quantity × unit_price = total
"""
        
        prompt += f"""

INVOICE TEXT:
{pdf_text}

REQUIRED OUTPUT FORMAT:
Return ONLY valid JSON with this exact structure:
{{
    "invoice_number": "string",
    "invoice_date": "string",
    "subtotal": float,
    "tax_amount": float,
    "total_amount": float,
    "products": [
        {{
            "line_number": int,
            "product_name": "string",
            "quantity": int,
            "unit_price": float,
            "total": float,
            "units_per_pack": int or null,
            "cost_per_unit": float or null,
            "raw_text": "original line from invoice"
        }}
    ],
    "metadata": {{
        "customer_name": "string or null",
        "payment_terms": "string or null",
        "notes": "string or null"
    }}
}}

IMPORTANT:
- Extract ALL products, don't skip any
- For Nikhil: always extract units from parentheses and calculate cost_per_unit
- Verify math: subtotal should equal sum of all product totals
- Return ONLY the JSON, no explanations
"""
        
        return prompt
    
    async def process_invoice(self, pdf_path: str, vendor_rules: Optional[str] = None) -> ProcessedInvoice:
        """Process a single invoice using Claude"""
        logger.info(f"Processing invoice: {pdf_path}")
        
        try:
            # Extract PDF text
            pdf_content = self.pdf_extractor.extract_text_from_pdf(pdf_path)
            
            if not pdf_content.text:
                raise ValueError("No text extracted from PDF")
            
            # Detect vendor
            vendor_info = self.vendor_detector.detect_vendor(
                pdf_content.text,
                metadata={'filename': os.path.basename(pdf_path)}
            )
            
            if not vendor_info['detected']:
                logger.warning(f"Unknown vendor for {pdf_path}")
                vendor_info['vendor_name'] = 'Unknown Vendor'
                vendor_info['vendor_key'] = 'GENERIC'
            
            logger.info(f"Detected vendor: {vendor_info['vendor_name']} (confidence: {vendor_info['confidence']})")
            
            # Build Claude prompt
            prompt = self.build_claude_prompt(vendor_info, pdf_content.text)
            
            # Call Claude API using Messages API
            logger.info("Calling Claude API...")
            response = self.anthropic.messages.create(
                model=self.claude_model,
                max_tokens=4000,
                temperature=0.0,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            # Parse Claude response
            claude_text = response.content[0].text
            logger.debug(f"Claude response: {claude_text[:200]}...")
            
            # Extract JSON from response
            invoice_data = self._parse_claude_response(claude_text)
            
            # Validate and correct extraction errors
            invoice_data = self._validate_extraction(invoice_data)
            
            # Create ProcessedInvoice object
            products = []
            for prod_data in invoice_data.get('products', []):
                product = InvoiceProduct(
                    line_number=prod_data.get('line_number', 0),
                    product_name=prod_data['product_name'],
                    quantity=prod_data['quantity'],
                    unit_price=prod_data['unit_price'],
                    total=prod_data['total'],
                    units_per_pack=prod_data.get('units_per_pack'),
                    cost_per_unit=prod_data.get('cost_per_unit'),
                    raw_text=prod_data.get('raw_text')
                )
                products.append(product)
            
            processed_invoice = ProcessedInvoice(
                vendor_key=vendor_info['vendor_key'],
                vendor_name=vendor_info['vendor_name'],
                invoice_number=invoice_data['invoice_number'],
                invoice_date=invoice_data['invoice_date'],
                subtotal=invoice_data.get('subtotal', 0),
                tax_amount=invoice_data.get('tax_amount', 0),
                total_amount=invoice_data['total_amount'],
                currency=vendor_info['currency'],
                products=products,
                metadata=invoice_data.get('metadata', {}),
                confidence=vendor_info['confidence'],
                processing_method='claude'
            )
            
            # Update stats
            self.stats['invoices_processed'] += 1
            self.stats['products_extracted'] += len(products)
            
            logger.info(f"Successfully processed invoice {invoice_data['invoice_number']} with {len(products)} products")
            
            return processed_invoice
            
        except Exception as e:
            logger.error(f"Error processing invoice {pdf_path}: {e}")
            self.stats['errors'] += 1
            raise
    
    def _parse_claude_response(self, response_text: str) -> Dict:
        """Parse JSON from Claude response with robust error handling"""
        # Clean response
        cleaned = response_text.strip()
        
        # Remove markdown code blocks if present
        if cleaned.startswith('```'):
            lines = cleaned.split('\n')
            # Find the actual JSON content
            start_idx = 1
            end_idx = len(lines) - 1
            for i, line in enumerate(lines):
                if line.strip().startswith('{'):
                    start_idx = i
                    break
            for i in range(len(lines) - 1, -1, -1):
                if lines[i].strip().endswith('}'):
                    end_idx = i + 1
                    break
            cleaned = '\n'.join(lines[start_idx:end_idx])
        
        # Remove 'json' prefix if present
        if cleaned.startswith('json'):
            cleaned = cleaned[4:].strip()
        
        # Try multiple parsing strategies
        parsing_attempts = [
            lambda: json.loads(cleaned),
            lambda: self._fix_common_json_errors(cleaned),
            lambda: self._extract_json_with_regex(cleaned)
        ]
        
        for attempt in parsing_attempts:
            try:
                result = attempt()
                if result and isinstance(result, dict):
                    return result
            except Exception as e:
                logger.debug(f"JSON parsing attempt failed: {e}")
                continue
        
        # Log the problematic response for debugging
        logger.error(f"Failed to parse Claude response. Response text: {response_text[:500]}...")
        raise ValueError(f"Could not parse JSON from Claude response after multiple attempts")
    
    def _fix_common_json_errors(self, text: str) -> Dict:
        """Fix common JSON formatting errors"""
        import re
        
        # Fix trailing commas
        text = re.sub(r',\s*}', '}', text)
        text = re.sub(r',\s*]', ']', text)
        
        # Fix missing quotes around keys
        text = re.sub(r'(\w+):', r'"\1":', text)
        
        # Fix single quotes to double quotes
        text = text.replace("'", '"')
        
        # Remove any trailing content after the last }
        last_brace = text.rfind('}')
        if last_brace != -1:
            text = text[:last_brace + 1]
        
        return json.loads(text)
    
    def _extract_json_with_regex(self, text: str) -> Dict:
        """Extract JSON using regex as last resort"""
        import re
        
        # Find the main JSON object
        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
        if json_match:
            json_text = json_match.group()
            return json.loads(json_text)
        
        raise ValueError("No valid JSON found in response")
    
    def _validate_extraction(self, invoice_data: Dict) -> Dict:
        """Validate and correct extraction errors"""
        logger.info("Validating extraction accuracy...")
        
        products = invoice_data.get('products', [])
        corrected_products = []
        
        for product in products:
            # Validate quantity × unit_price = total calculation
            quantity = product.get('quantity', 1)
            unit_price = product.get('unit_price', 0)
            total = product.get('total', 0)
            
            expected_total = quantity * unit_price
            
            # Check if calculation is significantly off (more than 1 rupee difference)
            if abs(expected_total - total) > 1.0:
                logger.warning(f"Price mismatch for {product['product_name']}: "
                             f"qty({quantity}) × unit_price({unit_price}) = {expected_total}, "
                             f"but extracted total = {total}")
                
                # If quantity is 1 and unit_price seems too high, likely confused with total
                if quantity == 1 and unit_price > total and total > 0:
                    logger.info(f"Correcting {product['product_name']}: "
                               f"unit_price {unit_price} → {total}")
                    product['unit_price'] = total
                    
                    # Recalculate cost_per_unit if units_per_pack exists
                    if product.get('units_per_pack'):
                        product['cost_per_unit'] = total / product['units_per_pack']
            
            corrected_products.append(product)
        
        invoice_data['products'] = corrected_products
        return invoice_data
    
    async def save_to_database(self, processed_invoice: ProcessedInvoice) -> Dict:
        """Save processed invoice to database"""
        try:
            # Get or create vendor
            vendor_result = self.supabase.table('vendors').select('id').eq(
                'name', processed_invoice.vendor_name
            ).execute()
            
            if vendor_result.data:
                vendor_id = vendor_result.data[0]['id']
            else:
                # Create new vendor
                new_vendor = {
                    'name': processed_invoice.vendor_name,
                    'detection_keywords': [processed_invoice.vendor_key],
                    'currency': processed_invoice.currency,
                    'created_at': datetime.now().isoformat()
                }
                vendor_result = self.supabase.table('vendors').insert(new_vendor).execute()
                vendor_id = vendor_result.data[0]['id']
            
            # Save invoice
            invoice_data = {
                'vendor_id': vendor_id,
                'invoice_number': processed_invoice.invoice_number,
                'invoice_date': processed_invoice.invoice_date,
                'total_amount': processed_invoice.total_amount,
                'currency': processed_invoice.currency,
                'processing_status': 'processed',
                'processing_method': processed_invoice.processing_method,
                'created_at': datetime.now().isoformat(),
                'processed_at': datetime.now().isoformat()
            }
            
            invoice_result = self.supabase.table('invoices').insert(invoice_data).execute()
            invoice_id = invoice_result.data[0]['id']
            
            # Save invoice items
            for product in processed_invoice.products:
                item_data = {
                    'invoice_id': invoice_id,
                    'product_name': product.product_name,
                    'units': product.quantity,
                    'unit_price': product.unit_price,
                    'cost_per_unit': product.cost_per_unit,
                    'confidence_score': 0.95,  # High confidence from Claude
                    'matching_strategy': 'claude_ai',
                    'created_at': datetime.now().isoformat()
                }
                
                self.supabase.table('invoice_items').insert(item_data).execute()
            
            return {
                'success': True,
                'invoice_id': invoice_id,
                'vendor_id': vendor_id,
                'products_saved': len(processed_invoice.products)
            }
            
        except Exception as e:
            logger.error(f"Error saving to database: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def generate_summary(self, processed_invoice: ProcessedInvoice) -> str:
        """Generate human-readable summary"""
        summary = f"""
INVOICE PROCESSING SUMMARY
========================
Vendor: {processed_invoice.vendor_name}
Invoice #: {processed_invoice.invoice_number}
Date: {processed_invoice.invoice_date}
Currency: {processed_invoice.currency}

TOTALS:
- Subtotal: {processed_invoice.currency} {processed_invoice.subtotal:,.2f}
- Tax: {processed_invoice.currency} {processed_invoice.tax_amount:,.2f}
- Total: {processed_invoice.currency} {processed_invoice.total_amount:,.2f}

PRODUCTS ({len(processed_invoice.products)} items):
"""
        
        for i, product in enumerate(processed_invoice.products, 1):
            summary += f"\n{i}. {product.product_name}"
            summary += f"\n   Qty: {product.quantity}"
            summary += f" × {processed_invoice.currency}{product.unit_price}"
            summary += f" = {processed_invoice.currency}{product.total}"
            
            if product.units_per_pack:
                summary += f"\n   Units/Pack: {product.units_per_pack}"
            if product.cost_per_unit:
                summary += f"\n   Cost/Unit: {processed_invoice.currency}{product.cost_per_unit:.2f}"
        
        return summary


# Main execution
async def process_single_invoice(pdf_path: str):
    """Process a single invoice file"""
    processor = ClaudeInvoiceProcessor()
    
    # Process invoice
    invoice = await processor.process_invoice(pdf_path)
    
    # Print summary
    print(processor.generate_summary(invoice))
    
    # Save to database
    result = await processor.save_to_database(invoice)
    
    if result['success']:
        print(f"\n✅ Saved to database: Invoice ID {result['invoice_id']}")
    else:
        print(f"\n❌ Database error: {result['error']}")
    
    return invoice


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        pdf_file = sys.argv[1]
    else:
        pdf_file = "uploads/Nikhilinvoice.pdf"
    
    if not os.path.exists(pdf_file):
        print(f"Error: File {pdf_file} not found")
        sys.exit(1)
    
    print(f"Processing invoice: {pdf_file}")
    asyncio.run(process_single_invoice(pdf_file))