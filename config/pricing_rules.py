"""
Pricing rules and markup configuration for different products
"""

from typing import Dict, List, Tuple, Optional
import re

class PricingRules:
    """Centralized pricing and markup rules"""
    
    # Default markup percentages by category
    CATEGORY_MARKUPS = {
        # Food categories
        'SNACKS': {
            'min_markup': 35,
            'target_markup': 45,
            'max_markup': 60,
            'factors': ['brand_premium', 'shelf_life', 'demand']
        },
        'RICE': {
            'min_markup': 25,
            'target_markup': 35,
            'max_markup': 45,
            'factors': ['brand', 'quality', 'package_size']
        },
        'FLOUR': {
            'min_markup': 30,
            'target_markup': 40,
            'max_markup': 50,
            'factors': ['brand', 'organic', 'specialty']
        },
        'SPICES': {
            'min_markup': 40,
            'target_markup': 55,
            'max_markup': 80,
            'factors': ['rarity', 'brand', 'package_size']
        },
        'FROZEN': {
            'min_markup': 30,
            'target_markup': 40,
            'max_markup': 55,
            'factors': ['brand', 'convenience', 'storage_cost']
        },
        'SWEETS': {
            'min_markup': 35,
            'target_markup': 50,
            'max_markup': 70,
            'factors': ['brand', 'festive_demand', 'freshness']
        },
        'LENTILS': {
            'min_markup': 25,
            'target_markup': 35,
            'max_markup': 45,
            'factors': ['quality', 'organic', 'package_size']
        },
        'READY_TO_EAT': {
            'min_markup': 40,
            'target_markup': 55,
            'max_markup': 75,
            'factors': ['convenience', 'brand', 'shelf_life']
        },
        'BEVERAGES': {
            'min_markup': 35,
            'target_markup': 45,
            'max_markup': 60,
            'factors': ['brand', 'type', 'size']
        },
        'DEFAULT': {
            'min_markup': 30,
            'target_markup': 45,
            'max_markup': 60,
            'factors': []
        }
    }
    
    # Brand premium adjustments (percentage points)
    BRAND_PREMIUMS = {
        # Premium brands
        'DEEP': 5,
        'Haldiram': 8,
        "Haldiram's": 8,
        'MTR': 6,
        'Britannia': 7,
        'Amul': 5,
        
        # Mid-tier brands
        'Anand': 3,
        'Deccan': 2,
        'Vadilal': 4,
        'Gits': 3,
        'Shan': 3,
        'MDH': 4,
        
        # Budget brands
        'Swad': 0,
        'Laxmi': 0,
        'Generic': -5
    }
    
    # Size-based adjustments
    SIZE_ADJUSTMENTS = {
        'small': 5,    # < 200g/ml
        'medium': 0,   # 200-500g/ml
        'large': -3,   # 500g-1kg
        'bulk': -5     # > 1kg
    }
    
    # Special conditions
    SPECIAL_CONDITIONS = {
        'organic': 10,
        'gluten_free': 8,
        'sugar_free': 5,
        'premium': 10,
        'imported': 12,
        'local': -3,
        'seasonal': 15,
        'clearance': -20
    }
    
    @classmethod
    def get_category_rules(cls, category: str) -> Dict:
        """Get markup rules for a category"""
        return cls.CATEGORY_MARKUPS.get(category.upper(), cls.CATEGORY_MARKUPS['DEFAULT'])
    
    @classmethod
    def get_brand_premium(cls, brand: str) -> int:
        """Get brand premium adjustment"""
        return cls.BRAND_PREMIUMS.get(brand, 0)
    
    @classmethod
    def get_competitive_pricing_rules(cls) -> Dict:
        """Get rules for competitive pricing"""
        return {
            'price_match_threshold': 5,  # % difference to trigger price match
            'undercut_percentage': 2,    # % to undercut competitor
            'premium_justification': 10, # % premium needs justification
            'loss_leader_products': ['rice', 'oil', 'sugar'],  # Common loss leaders
            'high_margin_products': ['spices', 'snacks', 'sweets']  # High margin items
        }


