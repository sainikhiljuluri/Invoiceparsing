"""
Rule management for vendor-specific processing
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

from config.vendor_rules import VendorRules
from config.vendor_patterns import get_vendor_abbreviations

logger = logging.getLogger(__name__)


class RuleManager:
    """Manage and apply vendor-specific parsing rules"""
    
    def __init__(self, rules_dir: Optional[str] = None):
        self.rules_dir = Path(rules_dir) if rules_dir else Path("config/learned_rules")
        self.rules_dir.mkdir(exist_ok=True)
        self.learned_rules = self._load_learned_rules()
        
    def get_parsing_rules(self, vendor_key: str) -> Dict[str, Any]:
        """Get complete parsing rules for a vendor"""
        # Base rules from configuration
        rules = {
            'vendor_key': vendor_key,
            'invoice_patterns': VendorRules.get_invoice_patterns(vendor_key),
            'product_patterns': VendorRules.get_product_patterns(vendor_key),
            'validation_rules': VendorRules.get_validation_rules(vendor_key),
            'abbreviations': get_vendor_abbreviations(),
            'product_config': VendorRules.get_product_config(vendor_key),
        }
        
        # Add learned rules if available
        if vendor_key in self.learned_rules:
            rules['learned_patterns'] = self.learned_rules[vendor_key]
        
        return rules
    
    def learn_pattern(self, vendor_key: str, pattern_type: str, 
                     pattern: str, confidence: float = 0.80):
        """Learn a new pattern from successful parsing"""
        if vendor_key not in self.learned_rules:
            self.learned_rules[vendor_key] = {
                'patterns': {},
                'last_updated': None
            }
        
        if pattern_type not in self.learned_rules[vendor_key]['patterns']:
            self.learned_rules[vendor_key]['patterns'][pattern_type] = []
        
        # Add pattern if not already present
        patterns = self.learned_rules[vendor_key]['patterns'][pattern_type]
        
        # Check if pattern already exists
        for existing in patterns:
            if existing['pattern'] == pattern:
                # Update confidence if higher
                if confidence > existing['confidence']:
                    existing['confidence'] = confidence
                    existing['last_seen'] = datetime.now().isoformat()
                return
        
        # Add new pattern
        patterns.append({
            'pattern': pattern,
            'confidence': confidence,
            'first_seen': datetime.now().isoformat(),
            'last_seen': datetime.now().isoformat(),
            'usage_count': 1
        })
        
        self.learned_rules[vendor_key]['last_updated'] = datetime.now().isoformat()
        self._save_learned_rules()
        
        logger.info(f"Learned new {pattern_type} pattern for {vendor_key}: {pattern}")
    
    def update_pattern_success(self, vendor_key: str, pattern_type: str, pattern: str):
        """Update pattern success count"""
        if (vendor_key in self.learned_rules and 
            pattern_type in self.learned_rules[vendor_key]['patterns']):
            
            patterns = self.learned_rules[vendor_key]['patterns'][pattern_type]
            for p in patterns:
                if p['pattern'] == pattern:
                    p['usage_count'] = p.get('usage_count', 0) + 1
                    p['last_seen'] = datetime.now().isoformat()
                    
                    # Increase confidence based on usage
                    if p['usage_count'] > 10 and p['confidence'] < 0.95:
                        p['confidence'] = min(0.95, p['confidence'] + 0.05)
                    
                    self._save_learned_rules()
                    break
    
    def get_learned_patterns(self, vendor_key: str, pattern_type: str) -> List[Dict]:
        """Get learned patterns for a vendor"""
        if (vendor_key in self.learned_rules and 
            pattern_type in self.learned_rules[vendor_key]['patterns']):
            
            patterns = self.learned_rules[vendor_key]['patterns'][pattern_type]
            # Sort by confidence and usage
            return sorted(patterns, 
                         key=lambda x: (x['confidence'], x.get('usage_count', 0)), 
                         reverse=True)
        
        return []
    
    def _load_learned_rules(self) -> Dict:
        """Load learned rules from disk"""
        rules_file = self.rules_dir / "learned_rules.json"
        
        if rules_file.exists():
            try:
                with open(rules_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load learned rules: {e}")
        
        return {}
    
    def _save_learned_rules(self):
        """Save learned rules to disk"""
        rules_file = self.rules_dir / "learned_rules.json"
        
        try:
            with open(rules_file, 'w') as f:
                json.dump(self.learned_rules, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save learned rules: {e}")
    
    def export_rules(self, vendor_key: str) -> Dict:
        """Export all rules for a vendor"""
        rules = self.get_parsing_rules(vendor_key)
        
        # Add statistics
        if vendor_key in self.learned_rules:
            learned = self.learned_rules[vendor_key]
            rules['statistics'] = {
                'last_updated': learned.get('last_updated'),
                'pattern_counts': {
                    ptype: len(patterns) 
                    for ptype, patterns in learned.get('patterns', {}).items()
                }
            }
        
        return rules