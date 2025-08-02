"""
Vendor-specific parsing rules and patterns
"""

from typing import Dict, List, Any, Optional
import re

class VendorRules:
    """Container for vendor-specific parsing rules"""
    
    # Invoice field patterns by vendor
    INVOICE_PATTERNS: Dict[str, Dict[str, str]] = {
        'NIKHIL_DISTRIBUTORS': {
            'invoice_number': r'Invoice\s*#?:?\s*(INV-\d{4}-\d{4})',
            'date': r'Date:\s*([A-Za-z]+\s+\d{1,2},\s+\d{4})',
            'total': r'Grand\s*Total:?\s*[₹%]?\s*([\d,]+\.?\d*)',
            'subtotal': r'Subtotal:?\s*[₹%]?\s*([\d,]+\.?\d*)',
            'tax': r'Tax\s*\((\d+)%\s*(?:GST)?\):?\s*[₹%]?\s*([\d,]+\.?\d*)',
            'customer_name': r'Customer\s+Name\s*\n\s*([^\n]+)',
            'bill_to': r'Bill\s+To:\s*\n([^S]+?)(?=Ship\s+From:|$)',
            'ship_from': r'Ship\s+From:\s*\n([^\n]+(?:\n[^\n]+)*?)(?=\n\s*\n|S\.No)',
            'phone': r'Phone:\s*([+\d\s\-]+)',
            'email': r'Email:\s*([\w\.\-]+@[\w\.\-]+)',
            'payment_terms': r'Payment\s+terms:\s*([^\n]+)',
        },
        
        'CHETAK_SAN_FRANCISCO': {
            'invoice_number': r'Invoice\s*(?:No|#|Number)?:?\s*(CHK\d+)',
            'date': r'Date:\s*(\d{1,2}/\d{1,2}/\d{4})',
            'total': r'Total\s*(?:Amount)?:?\s*\$?\s*([\d,]+\.?\d*)',
            'subtotal': r'Sub\s*total:?\s*\$?\s*([\d,]+\.?\d*)',
            'tax': r'Sales\s*Tax\s*\(?([\d.]+)%?\)?:?\s*\$?\s*([\d,]+\.?\d*)',
            'po_number': r'P\.?O\.?\s*(?:Number|#)?:?\s*(\w+)',
        },
        
        'RAJA_FOODS': {
            'invoice_number': r'Invoice\s*#:?\s*(RF\d+)',
            'date': r'Date:\s*(\d{1,2}/\d{1,2}/\d{4})',
            'total': r'Total:?\s*\$?\s*([\d,]+\.?\d*)',
            'subtotal': r'Subtotal:?\s*\$?\s*([\d,]+\.?\d*)',
            'tax': r'Tax:?\s*\$?\s*([\d,]+\.?\d*)',
            'due_date': r'Due\s*Date:\s*(\d{1,2}/\d{1,2}/\d{4})',
        },
        
        'FYVE_ELEMENTS': {
            'order_number': r'Order\s*#\s*([S]\d+)',
            'date': r'Date\s*\n?\s*(\d{2}/\d{2}/\d{4})',
            'total': r'Total:\s*\$?([\d,]+\.?\d*)',
            'subtotal': r'Subtotal:\s*\$?([\d,]+\.?\d*)',
            'sales_tax': r'Sales\s*Tax:\s*\$?([\d,]+\.?\d*)',
        },
        
        'GENERIC': {
            'invoice_number': r'Invoice\s*(?:No|#|Number)?:?\s*(\S+)',
            'date': r'Date:?\s*([^\n]+)',
            'total': r'Total:?\s*[$₹]?\s*([\d,]+\.?\d*)',
            'subtotal': r'Sub\s*total:?\s*[$₹]?\s*([\d,]+\.?\d*)',
            'tax': r'Tax:?\s*[$₹]?\s*([\d,]+\.?\d*)',
        }
    }
    
    # Product line patterns by vendor
    PRODUCT_PATTERNS: Dict[str, List[str]] = {
        'NIKHIL_DISTRIBUTORS': [
            # Pattern for: "1  DEEP CASHEW WHOLE 7OZ (20)  1  ₹30.00  ₹30.00"
            # Groups: (sr_no, product_full, units_per_box, qty, unit_price, total)
            r'^(\d+)\s+(.+?)\s+\((\d+)\)\s+(\d+)\s+₹?([\d,]+\.?\d*)\s+₹?([\d,]+\.?\d*)$',
            
            # Alternative pattern with different spacing
            r'^(\d+)\s+(.+?)\s*\((\d+)\)\s*(\d+)\s*₹?([\d,]+\.?\d*)\s*₹?([\d,]+\.?\d*)$',
            
            # For OCR variations where ₹ might be read as %
            r'^(\d+)\s+(.+?)\s+\((\d+)\)\s+(\d+)\s+[₹%]?([\d,]+\.?\d*)\s+[₹%]?([\d,]+\.?\d*)$',
        ],
        
        'CHETAK_SAN_FRANCISCO': [
            # Abbreviated format: "MTR Rava Idli Mix 500g  5  $3.99  $19.95"
            r'^(.+?)\s+(\d+(?:\.\d+)?)\s*([gG]|[kK][gG]|[lL][bB]|[oO][zZ])?\s+(\d+)\s+\$?([\d,]+\.?\d*)\s+\$?([\d,]+\.?\d*)$',
            # Standard format
            r'^(\d+)\s+(.+?)\s+(\d+)\s+\$?([\d,]+\.?\d*)\s+\$?([\d,]+\.?\d*)$',
        ],
        
        'FYVE_ELEMENTS': [
            r'^\d+\s+Sale\s+\w+\s+(.+?)\s+\$?([\d.]+)\s+\d+\s*[a-z]*\d*\s+\$\s*([\d,]+\.?\d*)$',
            r'^\d+\s+\w+\s+(\w+)\s+(.+?)\s+\$?([\d.]+)\s+(\d+)\s+\$\s*([\d,]+\.?\d*)$',
        ],
        
        'GENERIC': [
            # Try to match common patterns
            r'^(.+?)\s+(\d+)\s+[$₹]?([\d,]+\.?\d*)\s+[$₹]?([\d,]+\.?\d*)$',
            r'^(\d+)\s+(.+?)\s+(\d+)\s+[$₹]?([\d,]+\.?\d*)\s+[$₹]?([\d,]+\.?\d*)$',
        ]
    }
    
    # Product parsing configuration
    PRODUCT_CONFIG: Dict[str, Dict] = {
        'NIKHIL_DISTRIBUTORS': {
            'format': 'brand_item_size_units',
            'brand_position': 'first_word',
            'size_pattern': r'(\d+(?:\.\d+)?)\s*([A-Za-z]+|[Kk][Gg]|[Gg]|[Ll][Bb]|[Oo][Zz])',
            'known_brands': [
                'DEEP', 'Haldiram', "Haldiram's", 'Anand', 'Deccan', 
                'Vadilal', 'Britannia', 'Parle', 'MTR', 'Gits', 
                'Swad', 'Laxmi', 'Shan', 'MDH'
            ],
            'calculate_cost_per_unit': True,
        },
        
        'CHETAK_SAN_FRANCISCO': {
            'format': 'flexible',
            'abbreviation_expansion': True,
            'calculate_cost_per_unit': False,
        },
        
        'FYVE_ELEMENTS': {
            'format': '24m_organic',
            'brand_conversion': {'24M': '24 Mantra'},
            'calculate_cost_per_unit': True,
        },
        
        'GENERIC': {
            'format': 'standard',
            'calculate_cost_per_unit': False,
        }
    }
    
    @classmethod
    def get_invoice_patterns(cls, vendor_key: str) -> Dict[str, str]:
        """Get invoice field patterns for vendor"""
        return cls.INVOICE_PATTERNS.get(vendor_key, cls.INVOICE_PATTERNS['GENERIC'])
    
    @classmethod
    def get_product_patterns(cls, vendor_key: str) -> List[str]:
        """Get product line patterns for vendor"""
        return cls.PRODUCT_PATTERNS.get(vendor_key, cls.PRODUCT_PATTERNS['GENERIC'])
    
    @classmethod
    def get_product_config(cls, vendor_key: str) -> Dict:
        """Get product parsing configuration for vendor"""
        return cls.PRODUCT_CONFIG.get(vendor_key, cls.PRODUCT_CONFIG['GENERIC'])
    
    @classmethod
    def get_rules_for_vendor(cls, vendor_id: str):
        """Get parsing rules for a specific vendor"""
        # This is a simplified implementation - in a full system this would
        # return the complete VendorRules object for the vendor
        if vendor_id.lower() in ['nikhil_distributors', 'nikhil']:
            return type('MockRules', (), {
                'field_rules': [
                    type('FieldRule', (), {
                        'field_name': 'invoice_number',
                        'patterns': [r'Invoice\s*#?\s*:?\s*(INV-\d{4}-\d+)'],
                        'required': True
                    }),
                    type('FieldRule', (), {
                        'field_name': 'date',
                        'patterns': [r'Date\s*:?\s*(\w+\s+\d{1,2},?\s+\d{4})'],
                        'required': True
                    }),
                    type('FieldRule', (), {
                        'field_name': 'subtotal',
                        'patterns': [r'Subtotal\s*:?\s*₹?\s*([\d,]+\.?\d*)'],
                        'required': False
                    }),
                    type('FieldRule', (), {
                        'field_name': 'tax',
                        'patterns': [r'Tax\s*\(?\s*(\d+\.?\d*)%?\s*\)?:?\s*[₹$]?\s*([\d,]+\.?\d*)'],
                        'required': False
                    }),
                    type('FieldRule', (), {
                        'field_name': 'total',
                        'patterns': [r'Total\s*Amount?\s*:?\s*₹?\s*([\d,]+\.?\d*)'],
                        'required': True
                    })
                ]
            })()
        return type('MockRules', (), {'field_rules': []})()
    
    @classmethod
    def is_field_required(cls, vendor_id: str, field_name: str) -> bool:
        """Check if a field is required for a vendor"""
        rules = cls.get_rules_for_vendor(vendor_id)
        for field_rule in rules.field_rules:
            if field_rule.field_name == field_name:
                return field_rule.required
        return False
    
    @classmethod
    def get_invoice_patterns(cls, vendor_id: str) -> Dict[str, str]:
        """Get all invoice patterns for a vendor"""
        rules = cls.get_rules_for_vendor(vendor_id)
        patterns = {}
        for field_rule in rules.field_rules:
            if field_rule.patterns:
                # Return the first pattern as a string (not a list)
                patterns[field_rule.field_name] = field_rule.patterns[0]
        return patterns
    
    @classmethod
    def get_validation_rules(cls, vendor_key: str) -> Dict[str, Any]:
        """Get validation rules for vendor"""
        # Default validation rules
        default_rules = {
            'max_price_increase': 50.0,  # 50% max increase
            'max_price_decrease': 30.0,  # 30% max decrease
            'min_product_price': 0.01,
            'max_product_price': 10000.00,
            'min_quantity': 1,
            'max_quantity': 10000,
        }
        
        # Vendor-specific overrides
        vendor_rules = {
            'NIKHIL_DISTRIBUTORS': {
                'max_product_price': 10000.00,  # ₹10,000
                'require_gst': True,
                'gst_rate': 18.0,
            },
            'CHETAK_SAN_FRANCISCO': {
                'max_product_price': 1000.00,   # $1,000
                'require_sales_tax': True,
                'tax_rate_range': (7.0, 10.0),  # CA sales tax range
            },
        }
        
        rules = default_rules.copy()
        if vendor_key in vendor_rules:
            rules.update(vendor_rules[vendor_key])
        
        return rules