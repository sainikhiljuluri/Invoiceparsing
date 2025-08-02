"""
Vendor detection engine - automatically identifies vendors from invoice content
"""

import re
import logging
from typing import Dict, List, Tuple, Optional, Any
from collections import defaultdict
from dataclasses import dataclass

@dataclass
class VendorDetectionResult:
    """Result of vendor detection"""
    detected: bool
    vendor_key: str
    vendor_name: str
    confidence: float
    currency: str
    country: str
    matches: List[Dict] = None
    reason: str = None
    all_scores: Dict[str, float] = None

from config.vendor_patterns import (
    VENDOR_PATTERNS, 
    get_vendor_info,
    get_vendor_patterns
)

logger = logging.getLogger(__name__)


class VendorDetector:
    """Detect vendor from invoice text using pattern matching"""
    
    def __init__(self):
        self.vendors = list(VENDOR_PATTERNS.keys())
        self.min_confidence = 0.60  # Minimum confidence for detection
        self.generic_penalty = 0.30  # Penalty for generic patterns
        
    def detect_vendor(self, text: str, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Detect vendor from invoice text
        
        Args:
            text: Invoice text content
            metadata: Optional metadata (filename, headers, etc.)
            
        Returns:
            Dict with vendor detection results
        """
        if not text:
            return self._no_vendor_result("No text provided")
        
        # Clean text for matching
        text_upper = text.upper()
        text_lower = text.lower()
        
        # Score each vendor
        vendor_scores = defaultdict(float)
        vendor_matches = defaultdict(list)
        
        for vendor_key in self.vendors:
            if vendor_key == 'GENERIC':
                continue
                
            patterns = get_vendor_patterns(vendor_key)
            
            for pattern, weight in patterns:
                # Try both upper and lower case matching
                for test_text in [text, text_upper, text_lower]:
                    matches = re.findall(pattern, test_text, re.IGNORECASE)
                    if matches:
                        vendor_scores[vendor_key] += weight
                        vendor_matches[vendor_key].append({
                            'pattern': pattern,
                            'matches': matches,
                            'weight': weight
                        })
                        break
        
        # Apply metadata boosts if available
        if metadata:
            self._apply_metadata_boost(vendor_scores, metadata)
        
        # Find best match
        if vendor_scores:
            best_vendor = max(vendor_scores.items(), key=lambda x: x[1])
            vendor_key, confidence = best_vendor
            
            # Apply generic pattern penalty
            if self._has_only_generic_patterns(vendor_matches[vendor_key]):
                confidence *= (1 - self.generic_penalty)
            
            # Check if confidence meets threshold
            if confidence >= self.min_confidence:
                vendor_info = get_vendor_info(vendor_key)
                
                return {
                    'detected': True,
                    'vendor_key': vendor_key,
                    'vendor_name': vendor_info['name'],
                    'confidence': round(confidence, 2),
                    'currency': vendor_info['currency'],
                    'country': vendor_info['country'],
                    'matches': vendor_matches[vendor_key],
                    'all_scores': dict(vendor_scores)
                }
        
        # No confident match - try to determine currency at least
        currency = self._detect_currency(text)
        
        return {
            'detected': False,
            'vendor_key': 'GENERIC',
            'vendor_name': 'Unknown Vendor',
            'confidence': 0.0,
            'currency': currency,
            'country': 'Unknown',
            'reason': 'No vendor patterns matched with sufficient confidence',
            'all_scores': dict(vendor_scores)
        }
    
    def _apply_metadata_boost(self, scores: Dict[str, float], metadata: Dict):
        """Apply confidence boost based on metadata"""
        # Filename hints
        filename = metadata.get('filename', '').lower()
        
        vendor_filename_hints = {
            'NIKHIL_DISTRIBUTORS': ['nikhil', 'nd_invoice'],
            'CHETAK_SAN_FRANCISCO': ['chetak', 'chk_', 'chetak_invoice'],
            'RAJA_FOODS': ['raja', 'rf_invoice'],
            'BOMBAY_BAZAAR': ['bombay', 'bb_invoice'],
            'PATEL_BROTHERS': ['patel', 'pb_invoice'],
        }
        
        for vendor_key, hints in vendor_filename_hints.items():
            for hint in hints:
                if hint in filename:
                    scores[vendor_key] += 0.20
                    logger.info(f"Filename boost for {vendor_key}: {hint} in {filename}")
    
    def _has_only_generic_patterns(self, matches: List[Dict]) -> bool:
        """Check if matches contain only generic patterns"""
        generic_patterns = ['invoice', 'bill to', 'total', 'date']
        
        for match in matches:
            pattern_lower = match['pattern'].lower()
            if not any(generic in pattern_lower for generic in generic_patterns):
                return False
        
        return True
    
    def _detect_currency(self, text: str) -> str:
        """Detect currency from text"""
        currency_patterns = [
            (r'₹|Rs\.?|INR', 'INR'),
            (r'\$|USD|Dollar', 'USD'),
            (r'€|EUR|Euro', 'EUR'),
            (r'£|GBP|Pound', 'GBP'),
        ]
        
        for pattern, currency in currency_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return currency
        
        return 'USD'  # Default
    
    def _no_vendor_result(self, reason: str) -> Dict[str, Any]:
        """Return result when no vendor detected"""
        return {
            'detected': False,
            'vendor_key': 'GENERIC',
            'vendor_name': 'Unknown Vendor',
            'confidence': 0.0,
            'currency': 'USD',
            'country': 'Unknown',
            'reason': reason,
            'all_scores': {}
        }
    
    def get_supported_vendors(self) -> List[Dict[str, str]]:
        """Get list of supported vendors"""
        supported = []
        
        for vendor_key in self.vendors:
            if vendor_key == 'GENERIC':
                continue
                
            vendor_info = get_vendor_info(vendor_key)
            supported.append({
                'key': vendor_key,
                'name': vendor_info['name'],
                'currency': vendor_info['currency'],
                'country': vendor_info['country']
            })
        
        return sorted(supported, key=lambda x: x['name'])