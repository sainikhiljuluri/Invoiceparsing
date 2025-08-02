"""
Updated Fyve Elements parser with specific requirements:
- Order # as invoice number
- Date as invoice date  
- Product name: Brand (24 Mantra) + Item + Size
- Units: digit after x or /
- Cost per unit: unit price / units
"""

import re
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from parsers.base_invoice_parser import BaseInvoiceParser
from parsers.text_cleaner import TextCleaner

logger = logging.getLogger(__name__)


class FyveElementsParser(BaseInvoiceParser):
    """Parser specifically for Fyve Elements LLC invoices"""
    
    def __init__(self):
        super().__init__(
            vendor_key='FYVE_ELEMENTS',
            vendor_name='Fyve Elements LLC',
            currency='USD'
        )
        
        # Brand mapping
        self.brand_mapping = {
            '24M': '24 Mantra',
            '24 M': '24 Mantra'
        }
        
    def _extract_vendor_specific_fields(self, text: str, result: Dict):
        """Extract Fyve Elements specific fields"""
        # Order number (this is the invoice number)
        order_pattern = r'Order\s*#\s*([S]\d+)'
        match = re.search(order_pattern, text, re.IGNORECASE)
        if match:
            result['invoice_number'] = match.group(1)
            result['order_number'] = match.group(1)
            logger.info(f"Found invoice/order number: {result['invoice_number']}")
        else:
            result['errors'].append("Order number not found")
        
        # Date (invoice date)
        date_pattern = r'Date\s*\n?\s*(\d{2}/\d{2}/\d{4})'
        match = re.search(date_pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            result['invoice_date'] = match.group(1)
            logger.info(f"Found invoice date: {result['invoice_date']}")
        else:
            result['errors'].append("Invoice date not found")
            
        # Extract totals
        total_pattern = r'Total:\s*\$?([\d,]+\.?\d*)'
        match = re.search(total_pattern, text, re.IGNORECASE)
        if match:
            amount_str = match.group(1).replace(',', '')
            try:
                result['total_amount'] = float(amount_str)
                logger.info(f"Found total: ${result['total_amount']}")
            except ValueError:
                result['errors'].append(f"Invalid total amount: {amount_str}")
        
        # Subtotal
        subtotal_pattern = r'Subtotal:\s*\$?([\d,]+\.?\d*)'
        match = re.search(subtotal_pattern, text, re.IGNORECASE)
        if match:
            amount_str = match.group(1).replace(',', '')
            try:
                result['subtotal'] = float(amount_str)
            except ValueError:
                pass
    
    def _parse_product_description(self, description: str) -> Dict[str, Any]:
        """
        Parse product description to extract brand, item, size, and units
        Example: "24M Organic Sona Masuri White Rice 10Lb x 4"
        """
        result = {
            'brand': '',
            'item_description': '',
            'size': '',
            'units': 1,
            'full_product_name': ''
        }
        
        # Extract units (number after x or /)
        units_pattern = r'[x/]\s*(\d+)$'
        units_match = re.search(units_pattern, description)
        if units_match:
            result['units'] = int(units_match.group(1))
            # Remove units part from description
            description = description[:units_match.start()].strip()
        
        # Extract brand and convert
        brand_found = False
        for old_brand, new_brand in self.brand_mapping.items():
            if description.startswith(old_brand):
                result['brand'] = new_brand
                # Remove brand from description
                remaining = description[len(old_brand):].strip()
                brand_found = True
                break
        
        if not brand_found:
            # If no known brand, check for generic pattern
            if description.startswith('24M'):
                result['brand'] = '24 Mantra'
                remaining = description[3:].strip()
            else:
                remaining = description
        
        # Extract size (last part with number+unit)
        size_pattern = r'(\d+(?:\.\d+)?)\s*([A-Za-z]+)$'
        size_match = re.search(size_pattern, remaining)
        if size_match:
            result['size'] = size_match.group(0)
            result['item_description'] = remaining[:size_match.start()].strip()
        else:
            result['item_description'] = remaining
        
        # Build full product name
        parts = []
        if result['brand']:
            parts.append(result['brand'])
        if result['item_description']:
            parts.append(result['item_description'])
        if result['size']:
            parts.append(result['size'])
        
        result['full_product_name'] = ' '.join(parts)
        
        return result
    
    def _extract_products_from_tables(self, tables: List, result: Dict):
        """Extract products from Fyve Elements table format"""
        for table in tables:
            # Check if this is the product table
            headers_lower = [h.lower() for h in table.headers]
            
            if any('description' in h for h in headers_lower) and any('unit price' in h for h in headers_lower):
                logger.info(f"Found product table with {len(table.rows)} rows")
                
                # Find column indices
                desc_idx = next((i for i, h in enumerate(headers_lower) if 'description' in h), 3)
                price_idx = next((i for i, h in enumerate(headers_lower) if 'unit price' in h), 4)
                qty_idx = next((i for i, h in enumerate(headers_lower) if 'qty' in h), 5)
                total_idx = next((i for i, h in enumerate(headers_lower) if 'total' in h), 6)
                
                for row in table.rows:
                    try:
                        # Skip if not enough columns or not a sale row
                        if len(row) < 7 or (len(row) > 1 and row[1].lower() != 'sale'):
                            continue
                        
                        # Extract product description
                        product_description = row[desc_idx]
                        
                        # Parse product details
                        product_info = self._parse_product_description(product_description)
                        
                        # Extract prices
                        unit_price, _ = TextCleaner.extract_amount(row[price_idx])
                        total, _ = TextCleaner.extract_amount(row[total_idx])
                        
                        # Calculate cost per unit
                        cost_per_unit = unit_price / product_info['units'] if product_info['units'] > 0 else unit_price
                        
                        product = {
                            'product_name': product_info['full_product_name'],  # Brand + Item + Size combined
                            'units': product_info['units'],
                            'unit_price': unit_price,  # This is the box price
                            'total': total,
                            'cost_per_unit': round(cost_per_unit, 2)
                        }
                        
                        result['products'].append(product)
                        logger.info(f"Extracted: {product['product_name']} - Units: {product['units']} - Cost/unit: ${product['cost_per_unit']}")
                        
                    except (ValueError, IndexError) as e:
                        logger.warning(f"Failed to parse table row: {row} - {e}")
    
    def _extract_products_from_text(self, text: str, result: Dict):
        """Extract products from text for Fyve Elements format"""
        lines = text.split('\n')
        
        # Pattern for product lines
        # Example: "1  Sale  TM0213  24M Organic Sona Masuri White Rice 10Lb x 4  $52.80  5 c4  $ 264.00"
        product_pattern = r'^\d+\s+Sale\s+\w+\s+(.+?)\s+\$?([\d.]+)\s+\d+\s*[a-z]*\d*\s+\$\s*([\d,]+\.?\d*)$'
        
        for line in lines:
            line = line.strip()
            match = re.match(product_pattern, line)
            
            if match:
                try:
                    product_description = match.group(1).strip()
                    unit_price = float(match.group(2))
                    total = float(match.group(3).replace(',', ''))
                    
                    # Parse product details
                    product_info = self._parse_product_description(product_description)
                    
                    # Calculate cost per unit
                    cost_per_unit = unit_price / product_info['units'] if product_info['units'] > 0 else unit_price
                    
                    product = {
                        'product_name': product_info['full_product_name'],  # Brand + Item + Size combined
                        'units': product_info['units'],
                        'unit_price': unit_price,
                        'total': total,
                        'cost_per_unit': round(cost_per_unit, 2)
                    }
                    
                    result['products'].append(product)
                    
                except (ValueError, IndexError) as e:
                    logger.warning(f"Failed to parse product line: {line} - {e}")
    
    def _post_process(self, result: Dict):
        """Post-process Fyve Elements invoice results"""
        super()._post_process(result)
        
        # Add summary statistics
        if result['products']:
            # Count 24 Mantra products
            mantra_count = sum(1 for p in result['products'] 
                              if '24 Mantra' in p.get('product_name', ''))
            result['metadata']['24_mantra_products'] = mantra_count
            
            # Calculate total units
            total_units = sum(p.get('units', 0) for p in result['products'])
            result['metadata']['total_units'] = total_units
            
            # Calculate average cost per unit
            costs = [p.get('cost_per_unit', 0) for p in result['products'] if p.get('cost_per_unit', 0) > 0]
            if costs:
                result['metadata']['average_cost_per_unit'] = round(sum(costs) / len(costs), 2)
    
    def _parse_product_match(self, match, pattern: str):
        """Parse product from regex match for Fyve Elements format"""
        try:
            if len(match.groups()) >= 3:
                product_description = match.group(1).strip()
                unit_price = float(match.group(2))
                total = float(match.group(3).replace(',', ''))
                
                # Parse product details
                product_info = self._parse_product_description(product_description)
                
                # Calculate cost per unit
                cost_per_unit = unit_price / product_info['units'] if product_info['units'] > 0 else unit_price
                
                return {
                    'product_name': product_info['full_product_name'],
                    'units': product_info['units'],
                    'unit_price': unit_price,
                    'total': total,
                    'cost_per_unit': round(cost_per_unit, 2)
                }
        except (ValueError, IndexError) as e:
            logger.warning(f"Failed to parse product match: {match.groups()} - {e}")
            return None