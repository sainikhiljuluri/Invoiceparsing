"""
Specialized parser for Nikhil Distributors invoices
"""

import re
import logging
from typing import Dict, List, Any, Optional, Tuple

# Fix the import - use absolute import instead of relative
from parsers.base_invoice_parser import BaseInvoiceParser
from parsers.text_cleaner import TextCleaner

logger = logging.getLogger(__name__)


class NikhilParser(BaseInvoiceParser):
    """Parser specifically for Nikhil Distributors invoices"""
    
    def __init__(self):
        super().__init__(
            vendor_key='NIKHIL_DISTRIBUTORS',
            vendor_name='Nikhil Distributors',
            currency='INR'
        )
        
        # Get product configuration
        from config.vendor_rules import VendorRules
        self.product_config = VendorRules.get_product_config('NIKHIL_DISTRIBUTORS')
        self.known_brands = self.product_config.get('known_brands', [])
    
    def _extract_vendor_specific_fields(self, text: str, result: Dict):
        """Extract Nikhil-specific fields"""
        # Customer information
        if 'customer_name' in self.patterns:
            match = re.search(self.patterns['customer_name'], text, re.IGNORECASE | re.MULTILINE)
            if match:
                result['metadata']['customer_name'] = match.group(1).strip()
        
        # Email
        if 'email' in self.patterns:
            match = re.search(self.patterns['email'], text, re.IGNORECASE)
            if match:
                result['metadata']['vendor_email'] = match.group(1)
        
        # Payment terms
        if 'payment_terms' in self.patterns:
            match = re.search(self.patterns['payment_terms'], text, re.IGNORECASE)
            if match:
                result['metadata']['payment_terms'] = match.group(1).strip()
    
    def _parse_product_match(self, match: re.Match, pattern: str) -> Optional[Dict]:
        """Parse product from regex match for Nikhil format"""
        try:
            groups = match.groups()
            
            # Expected groups: (sr_no, product_full, units_per_box, qty, unit_price, total)
            if len(groups) == 6:
                sr_no = int(groups[0])
                product_full = groups[1].strip()
                units_per_box = int(groups[2])
                quantity = int(groups[3])
                unit_price = float(groups[4].replace(',', ''))
                total = float(groups[5].replace(',', ''))
                
                # Parse product details
                product_parts = self._parse_product_name(product_full)
                
                # Calculate cost per unit
                cost_per_unit = unit_price / units_per_box if units_per_box > 0 else unit_price
                
                product = {
                    'sr_no': sr_no,
                    'product_name': product_full,  # Full name
                    'brand': product_parts['brand'],
                    'item_description': product_parts['item_description'],
                    'size': product_parts['size'],
                    'units_per_box': units_per_box,
                    'quantity': quantity,
                    'unit_price': unit_price,
                    'total': total,
                    'cost_per_unit': round(cost_per_unit, 2)
                }
                
                # Validate calculated total
                expected_total = quantity * unit_price
                if abs(expected_total - total) > 0.01:
                    logger.warning(f"Total mismatch for {product_full}: "
                                 f"calculated {expected_total} vs stated {total}")
                
                return product
                
        except (ValueError, IndexError) as e:
            logger.error(f"Failed to parse product match: {e}")
            return None
    
    def _parse_product_name(self, product_full: str) -> Dict[str, str]:
        """
        Parse product name into components
        Format: BRAND ITEM_DESCRIPTION SIZE
        Example: "DEEP CASHEW WHOLE 7OZ" -> 
                 {brand: "DEEP", item_description: "CASHEW WHOLE", size: "7OZ"}
        """
        result = {
            'brand': '',
            'item_description': '',
            'size': ''
        }
        
        # Clean the product name
        product_full = product_full.strip()
        
        # Try to extract brand (first word if it's a known brand)
        words = product_full.split()
        if words:
            # Check if first word is a known brand
            if words[0] in self.known_brands:
                result['brand'] = words[0]
                remaining = ' '.join(words[1:])
            else:
                # Try to find brand in the string
                for brand in self.known_brands:
                    if product_full.startswith(brand):
                        result['brand'] = brand
                        remaining = product_full[len(brand):].strip()
                        break
                else:
                    # No known brand found, assume first word is brand
                    result['brand'] = words[0]
                    remaining = ' '.join(words[1:])
        else:
            return result
        
        # Try to extract size (last part with number+unit)
        size_match = re.search(r'(\d+(?:\.\d+)?)\s*([A-Za-z]+|[Kk][Gg]|[Gg]|[Ll][Bb]|[Oo][Zz])$', remaining)
        if size_match:
            result['size'] = size_match.group(0)
            result['item_description'] = remaining[:size_match.start()].strip()
        else:
            # No clear size found, use the whole remaining as description
            result['item_description'] = remaining
        
        return result
    
    def _extract_products_from_tables(self, tables: List, result: Dict):
        """Extract products from tables for Nikhil format"""
        for table in tables:
            # Look for product table
            headers_lower = [h.lower() for h in table.headers]
            
            # Check if this is the product table
            if any('product' in h for h in headers_lower) and any('qty' in h for h in headers_lower):
                logger.info(f"Found product table with {len(table.rows)} rows")
                
                # Find column indices
                sr_no_idx = next((i for i, h in enumerate(headers_lower) if 's.no' in h or 'sr.no' in h), -1)
                product_idx = next((i for i, h in enumerate(headers_lower) if 'product' in h), 0)
                qty_idx = next((i for i, h in enumerate(headers_lower) if 'qty' in h), -1)
                unit_price_idx = next((i for i, h in enumerate(headers_lower) if 'unit price' in h), -1)
                total_idx = next((i for i, h in enumerate(headers_lower) if 'total' in h), -1)
                
                for row in table.rows:
                    try:
                        # Skip if not enough columns
                        if len(row) < 5:
                            continue
                        
                        # Skip total rows
                        first_cell = str(row[0]).lower()
                        if any(keyword in first_cell for keyword in ['total', 'subtotal', 'tax']):
                            continue
                        
                        # Extract product with units
                        product_text = row[product_idx] if product_idx >= 0 else row[1]
                        
                        # Parse product with units: "DEEP CASHEW WHOLE 7OZ (20)"
                        product_match = re.match(r'(.+?)\s*\((\d+)\)$', product_text)
                        if product_match:
                            product_name = product_match.group(1).strip()
                            units_per_box = int(product_match.group(2))
                        else:
                            product_name = product_text
                            units_per_box = 1
                        
                        # Extract other fields
                        sr_no = int(row[sr_no_idx]) if sr_no_idx >= 0 else None
                        quantity = int(row[qty_idx]) if qty_idx >= 0 else 1
                        
                        # Extract prices
                        unit_price_text = row[unit_price_idx] if unit_price_idx >= 0 else row[-2]
                        total_text = row[total_idx] if total_idx >= 0 else row[-1]
                        
                        unit_price, _ = TextCleaner.extract_amount(unit_price_text)
                        total, _ = TextCleaner.extract_amount(total_text)
                        
                        # Parse product details
                        product_parts = self._parse_product_name(product_name)
                        
                        # Calculate cost per unit
                        cost_per_unit = unit_price / units_per_box if units_per_box > 0 else unit_price
                        
                        product = {
                            'sr_no': sr_no,
                            'product_name': product_name,
                            'brand': product_parts['brand'],
                            'item_description': product_parts['item_description'],
                            'size': product_parts['size'],
                            'units_per_box': units_per_box,
                            'quantity': quantity,
                            'unit_price': unit_price,
                            'total': total,
                            'cost_per_unit': round(cost_per_unit, 2)
                        }
                        
                        result['products'].append(product)
                        logger.info(f"Extracted: {product_name} ({units_per_box} units) "
                                  f"@ ₹{unit_price} = ₹{cost_per_unit}/unit")
                        
                    except (ValueError, IndexError) as e:
                        logger.warning(f"Failed to parse table row: {row} - {e}")
    
    def _post_process(self, result: Dict):
        """Post-process Nikhil invoice results"""
        super()._post_process(result)
        
        # Add summary statistics
        if result['products']:
            result['metadata']['total_items'] = len(result['products'])
            result['metadata']['total_units'] = sum(
                p.get('quantity', 0) * p.get('units_per_box', 1) 
                for p in result['products']
            )
            
            # Brand summary
            brands = {}
            for product in result['products']:
                brand = product.get('brand', 'Unknown')
                if brand not in brands:
                    brands[brand] = 0
                brands[brand] += product.get('quantity', 0)
            
            result['metadata']['brand_summary'] = brands