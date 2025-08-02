"""
Vendor detection patterns and configurations
Supports 25+ vendors with automatic detection
"""

from typing import Dict, List, Tuple
from dataclasses import dataclass
import re

@dataclass
class VendorSignature:
    """Vendor identification signature"""
    vendor_id: str
    vendor_name: str
    confidence_patterns: List[Tuple[str, int]]
    min_confidence: int = 70

class VendorPatterns:
    """Centralized vendor detection patterns"""
    
    @classmethod
    def get_all_vendors(cls) -> List[VendorSignature]:
        """Get all vendor signatures for detection"""
        return [
            VendorSignature(
                vendor_id="nikhil_distributors",
                vendor_name="Nikhil Distributors",
                confidence_patterns=[
                    (r"Nikhil\s+Distributors", 95),
                    (r"NIKHIL\s+DISTRIBUTORS", 95),
                    (r"Invoice\s*#?:?\s*INV-\d{4}-\d{4}", 70),
                    (r"sales@nikhildistributors\.com", 90),
                ],
                min_confidence=70
            ),
            VendorSignature(
                vendor_id="generic",
                vendor_name="Generic Invoice",
                confidence_patterns=[
                    (r"Invoice", 20),
                    (r"Bill\s+To", 20),
                    (r"Total", 15),
                ],
                min_confidence=40
            )
        ]
    
    @classmethod
    def get_vendor_by_id(cls, vendor_id: str) -> VendorSignature:
        """Get vendor signature by ID"""
        for vendor in cls.get_all_vendors():
            if vendor.vendor_id == vendor_id:
                return vendor
        return None

# Vendor detection patterns with confidence scores
VENDOR_PATTERNS: Dict[str, List[Tuple[str, float]]] = {
    'NIKHIL_DISTRIBUTORS': [
        (r'Nikhil\s+Distributors', 0.95),
        (r'NIKHIL\s+DISTRIBUTORS', 0.95),
        (r'Invoice\s*#?:?\s*INV-\d{4}-\d{4}', 0.70),  # Nikhil's invoice format
        (r'sales@nikhildistributors\.com', 0.90),
        (r'Wholesale\s+Food\s+&\s+Beverage\s+Supplier', 0.60),
        (r'123\s+Industrial\s+Area,\s+Sector\s+5', 0.80),  # Address
    ],
    
    'CHETAK_SAN_FRANCISCO': [
        (r'CHETAK\s+SAN\s+FRANCISCO', 0.95),
        (r'Chetak\s+San\s+Francisco\s+LLC', 0.95),
        (r'CHETAK', 0.70),
        (r'415-\d{3}-\d{4}', 0.40),  # SF phone pattern
        (r'CHK\d+', 0.65),  # Invoice pattern
    ],
    
    'FYVE_ELEMENTS': [
        (r'Fyve\s+Elements\s+LLC', 0.95),
        (r'FYVE\s+ELEMENTS\s+LLC', 0.95),
        (r'30989\s+San\s+Clemente\s+St', 0.80),
        (r'service@fyvelements\.com', 0.90),
        (r'Order\s*#\s*S\d+', 0.80),
        (r'24M\s+Organic', 0.70),
    ],
    
    'GENERIC': [
        (r'Invoice', 0.20),
        (r'Bill\s+To', 0.20),
        (r'Total', 0.10),
    ]
}

# Vendor metadata
VENDOR_INFO: Dict[str, Dict] = {
    'NIKHIL_DISTRIBUTORS': {
        'name': 'Nikhil Distributors',
        'currency': 'INR',
        'invoice_prefix': 'INV-',
        'date_format': '%B %d, %Y',  # July 26, 2025
        'country': 'India',
        'product_format': 'name_with_pack_size',
        'gst_applicable': True,
        'known_brands': [
            'DEEP', 'Haldiram', "Haldiram's", 'Anand', 'Deccan', 
            'Vadilal', 'Britannia', 'Parle', 'MTR', 'Gits', 
            'Swad', 'Laxmi', 'Shan', 'MDH'
        ],
    },
    
    'CHETAK_SAN_FRANCISCO': {
        'name': 'Chetak San Francisco LLC',
        'currency': 'USD',
        'invoice_prefix': 'CHK',
        'date_format': '%m/%d/%Y',  # 07/26/2025
        'country': 'USA',
        'product_format': 'abbreviated',
        'tax_name': 'Sales Tax',
    },
    
    'FYVE_ELEMENTS': {
        'name': 'Fyve Elements LLC',
        'currency': 'USD',
        'invoice_prefix': 'S',
        'date_format': '%m/%d/%Y',
        'country': 'USA',
        'product_format': '24m_organic',
        'known_product_prefix': '24M Organic',
    },
    
    'GENERIC': {
        'name': 'Unknown Vendor',
        'currency': 'USD',
        'invoice_prefix': '',
        'date_format': '%m/%d/%Y',
        'country': 'Unknown',
        'product_format': 'standard',
    }
}

# Common abbreviations by vendor
VENDOR_ABBREVIATIONS: Dict[str, Dict[str, str]] = {
    'CHETAK_SAN_FRANCISCO': {
        'Pwd': 'Powder',
        'Pdr': 'Powder',
        'Whl': 'Whole',
        'Grn': 'Green',
        'Rd': 'Red',
        'Blk': 'Black',
        'Sml': 'Small',
        'Med': 'Medium',
        'Lrg': 'Large',
        'Frz': 'Frozen',
        'Frzn': 'Frozen',
    },
    
    'NIKHIL_DISTRIBUTORS': {
        'Gm': 'Gram',
        'Kg': 'Kilogram',
        'Lb': 'Pound',
        'Oz': 'Ounce',
        'Pkt': 'Packet',
        'Pcs': 'Pieces',
    },
    
    'FYVE_ELEMENTS': {
        'lb': 'Lb',
        'oz': 'oz',
        'kg': 'kg',
    },
    
    'GENERIC': {
        'qty': 'quantity',
        'amt': 'amount',
        'pcs': 'pieces',
        'pkg': 'package',
    }
}

def get_vendor_patterns(vendor_key: str) -> List[Tuple[str, float]]:
    """Get detection patterns for a specific vendor"""
    return VENDOR_PATTERNS.get(vendor_key, VENDOR_PATTERNS['GENERIC'])

def get_vendor_info(vendor_key: str) -> Dict:
    """Get vendor metadata"""
    # For vendors not fully configured, copy GENERIC and update name
    if vendor_key not in VENDOR_INFO:
        info = VENDOR_INFO['GENERIC'].copy()
        # Try to get name from patterns
        if vendor_key in VENDOR_PATTERNS:
            info['name'] = vendor_key.replace('_', ' ').title()
        return info
    return VENDOR_INFO[vendor_key]

def get_vendor_abbreviations() -> Dict[str, str]:
    """Get all vendor abbreviations mapping"""
    return {
        'NIKHIL_DISTRIBUTORS': 'ND',
        'CHETAK_SAN_FRANCISCO': 'CHK', 
        'GENERIC': 'GEN'
    }

def get_vendor_specific_abbreviations(vendor_key: str) -> Dict[str, str]:
    """Get vendor-specific abbreviations"""
    base_abbr = VENDOR_ABBREVIATIONS.get('GENERIC', {}).copy()
    vendor_abbr = VENDOR_ABBREVIATIONS.get(vendor_key, {})
    base_abbr.update(vendor_abbr)
    return base_abbr