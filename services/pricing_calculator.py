"""
Service to calculate suggested selling prices
"""

import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from config.pricing_rules import PricingRules

logger = logging.getLogger(__name__)

class PriceCalculator:
    """Calculate suggested selling prices based on various factors"""
    
    def __init__(self, database_connection=None):
        self.db = database_connection
        self.pricing_rules = PricingRules()
    
    def calculate_suggested_price(self, product_info: Dict) -> Dict:
        """
        Calculate suggested selling price for a product
        
        Args:
            product_info: Dict containing:
                - product_name: str
                - cost_per_unit: float
                - brand: str (optional)
                - category: str (optional)
                - size: str (optional)
                - units: int (optional)
                - special_attributes: List[str] (optional)
        
        Returns:
            Dict with pricing suggestions
        """
        cost = product_info.get('cost_per_unit', 0)
        if cost <= 0:
            return self._error_response("Invalid cost price")
        
        # Determine category
        category = product_info.get('category') or self._detect_category(product_info['product_name'])
        
        # Get base markup rules (try database first, fallback to config)
        markup_rules = self._get_pricing_rules_from_db(category) or PricingRules.get_category_rules(category)
        
        # Calculate base markup
        base_markup = markup_rules['target_markup']
        
        # Apply adjustments
        total_adjustment = 0
        adjustments = []
        
        # Brand adjustment
        brand = product_info.get('brand', '')
        brand_premium = PricingRules.get_brand_premium(brand)
        if brand_premium:
            total_adjustment += brand_premium
            adjustments.append(f"Brand {brand}: +{brand_premium}%")
        
        # Size adjustment
        size_category = self._categorize_size(product_info)
        size_adj = PricingRules.SIZE_ADJUSTMENTS.get(size_category, 0)
        if size_adj:
            total_adjustment += size_adj
            adjustments.append(f"Size {size_category}: {size_adj:+}%")
        
        # Special attributes
        special_attrs = product_info.get('special_attributes', [])
        for attr in special_attrs:
            if attr.lower() in PricingRules.SPECIAL_CONDITIONS:
                adj = PricingRules.SPECIAL_CONDITIONS[attr.lower()]
                total_adjustment += adj
                adjustments.append(f"{attr}: {adj:+}%")
        
        # Calculate final markup
        final_markup = base_markup + total_adjustment
        
        # Ensure within bounds
        final_markup = max(markup_rules['min_markup'], 
                          min(final_markup, markup_rules['max_markup']))
        
        # Calculate prices
        suggested_price = cost * (1 + final_markup / 100)
        min_price = cost * (1 + markup_rules['min_markup'] / 100)
        max_price = cost * (1 + markup_rules['max_markup'] / 100)
        
        # Round to appropriate decimals
        suggested_price = self._round_price(suggested_price)
        min_price = self._round_price(min_price)
        max_price = self._round_price(max_price)
        
        # Get competitor prices if available
        competitor_prices = self._get_competitor_prices(product_info) if self.db else []
        
        # Adjust for competition
        if competitor_prices:
            suggested_price = self._adjust_for_competition(
                suggested_price, competitor_prices, markup_rules
            )
        
        return {
            'success': True,
            'product_name': product_info['product_name'],
            'cost_per_unit': cost,
            'suggested_price': suggested_price,
            'min_price': min_price,
            'max_price': max_price,
            'markup_percentage': round((suggested_price / cost - 1) * 100, 1),
            'price_range': f"₹{min_price:.2f} - ₹{max_price:.2f}",
            'category': category,
            'adjustments': adjustments,
            'final_markup': final_markup,
            'competitor_analysis': {
                'competitor_prices': competitor_prices,
                'market_position': self._determine_market_position(suggested_price, competitor_prices)
            },
            'pricing_strategy': self._suggest_strategy(product_info, final_markup),
            'confidence': self._calculate_confidence(adjustments, competitor_prices)
        }
    
    def calculate_bulk_prices(self, products: List[Dict]) -> List[Dict]:
        """Calculate prices for multiple products"""
        results = []
        for product in products:
            result = self.calculate_suggested_price(product)
            results.append(result)
        return results
    
    def _detect_category(self, product_name: str) -> str:
        """Detect product category from name"""
        name_lower = product_name.lower()
        
        # Category keywords
        category_keywords = {
            'RICE': ['rice', 'basmati', 'sona masuri', 'idli rice'],
            'FLOUR': ['flour', 'atta', 'besan', 'maida', 'powder'],
            'SNACKS': ['chips', 'namkeen', 'mixture', 'bhujia', 'samosa', 'kachori'],
            'SPICES': ['masala', 'spice', 'chili', 'turmeric', 'cumin', 'coriander'],
            'FROZEN': ['frozen', 'ice cream', 'kulfi'],
            'SWEETS': ['sweet', 'mithai', 'ladoo', 'barfi', 'halwa', 'rasgulla'],
            'LENTILS': ['dal', 'lentil', 'moong', 'toor', 'chana', 'urad'],
            'READY_TO_EAT': ['ready to eat', 'instant', 'rte', 'heat and eat'],
            'BEVERAGES': ['juice', 'drink', 'beverage', 'tea', 'coffee']
        }
        
        for category, keywords in category_keywords.items():
            if any(keyword in name_lower for keyword in keywords):
                return category
        
        return 'DEFAULT'
    
    def _categorize_size(self, product_info: Dict) -> str:
        """Categorize product by size"""
        # Extract size from product name or use provided size
        size_str = product_info.get('size', '')
        if not size_str:
            # Try to extract from product name
            import re
            name = product_info.get('product_name', '')
            size_match = re.search(r'(\d+(?:\.\d+)?)\s*(g|kg|ml|l|oz|lb)', name, re.IGNORECASE)
            if size_match:
                size_str = size_match.group(0)
        
        if not size_str:
            return 'medium'
        
        # Convert to grams for comparison
        size_in_grams = self._convert_to_grams(size_str)
        
        if size_in_grams < 200:
            return 'small'
        elif size_in_grams < 500:
            return 'medium'
        elif size_in_grams < 1000:
            return 'large'
        else:
            return 'bulk'
    
    def _convert_to_grams(self, size_str: str) -> float:
        """Convert size string to grams"""
        import re
        match = re.search(r'(\d+(?:\.\d+)?)\s*(g|kg|ml|l|oz|lb)', size_str, re.IGNORECASE)
        if not match:
            return 250  # Default medium size
        
        value = float(match.group(1))
        unit = match.group(2).lower()
        
        conversions = {
            'g': 1,
            'kg': 1000,
            'ml': 1,  # Approximate
            'l': 1000,
            'oz': 28.35,
            'lb': 453.59
        }
        
        return value * conversions.get(unit, 1)
    
    def _round_price(self, price: float) -> float:
        """Round price to appropriate decimal"""
        if price < 10:
            return round(price, 2)
        elif price < 100:
            return round(price / 0.5) * 0.5  # Round to nearest 0.50
        else:
            return round(price)  # Round to nearest rupee
    
    def _get_competitor_prices(self, product_info: Dict) -> List[float]:
        """Get competitor prices from database"""
        if not self.db:
            return []
        
        try:
            # Query for similar products from competitors using Supabase
            result = self.db.supabase.table('competitor_prices').select(
                'competitor_price'
            ).ilike('product_name', f'%{product_info["product_name"]}%').eq(
                'active', True
            ).order('last_updated', desc=True).limit(5).execute()
            
            return [item['competitor_price'] for item in result.data]
        except Exception as e:
            logger.warning(f"Error getting competitor prices: {e}")
            return []
    
    def _adjust_for_competition(self, suggested_price: float, 
                               competitor_prices: List[float], 
                               markup_rules: Dict) -> float:
        """Adjust price based on competition"""
        if not competitor_prices:
            return suggested_price
        
        avg_competitor = sum(competitor_prices) / len(competitor_prices)
        
        # If we're significantly higher, adjust down
        if suggested_price > avg_competitor * 1.1:
            # Don't go below minimum markup
            min_competitive = avg_competitor * 0.98  # 2% below average
            min_allowed = suggested_price * (1 + markup_rules['min_markup'] / 100)
            return max(min_competitive, min_allowed)
        
        return suggested_price
    
    def _determine_market_position(self, our_price: float, 
                                  competitor_prices: List[float]) -> str:
        """Determine our market position"""
        if not competitor_prices:
            return "No competitor data"
        
        avg_price = sum(competitor_prices) / len(competitor_prices)
        ratio = our_price / avg_price
        
        if ratio < 0.9:
            return "Value leader"
        elif ratio < 0.98:
            return "Competitive"
        elif ratio < 1.02:
            return "Market average"
        elif ratio < 1.1:
            return "Premium"
        else:
            return "Luxury positioning"
    
    def _suggest_strategy(self, product_info: Dict, markup: float) -> str:
        """Suggest pricing strategy"""
        category = product_info.get('category', 'DEFAULT')
        
        strategies = {
            'RICE': "Volume-based pricing - lower margins, higher turnover",
            'SPICES': "Premium pricing - emphasize quality and authenticity",
            'SNACKS': "Competitive pricing with promotions",
            'FROZEN': "Factor in storage costs, price for quick turnover",
            'SWEETS': "Seasonal pricing - increase during festivals",
            'DEFAULT': "Balanced pricing - competitive with fair margins"
        }
        
        base_strategy = strategies.get(category, strategies['DEFAULT'])
        
        if markup > 60:
            return f"{base_strategy}. Consider bundling for value perception."
        elif markup < 25:
            return f"{base_strategy}. Monitor for profitability."
        
        return base_strategy
    
    def _calculate_confidence(self, adjustments: List[str], 
                            competitor_prices: List[float]) -> str:
        """Calculate confidence in pricing suggestion"""
        confidence_score = 70  # Base confidence
        
        # More adjustments = more factors considered
        confidence_score += len(adjustments) * 5
        
        # Competitor data increases confidence
        if competitor_prices:
            confidence_score += min(len(competitor_prices) * 5, 20)
        
        confidence_score = min(confidence_score, 95)
        
        if confidence_score >= 85:
            return "High"
        elif confidence_score >= 70:
            return "Medium"
        else:
            return "Low"
    
    def _get_pricing_rules_from_db(self, category: str) -> Dict:
        """Get pricing rules from database"""
        if not self.db:
            return None
        
        try:
            result = self.db.supabase.table('pricing_rules').select(
                'min_markup, target_markup, max_markup, factors'
            ).eq('category', category).execute()
            
            if result.data:
                rule = result.data[0]
                return {
                    'min_markup': float(rule['min_markup']),
                    'target_markup': float(rule['target_markup']),
                    'max_markup': float(rule['max_markup']),
                    'factors': rule.get('factors', {})
                }
            return None
        except Exception as e:
            logger.warning(f"Error getting pricing rules for {category}: {e}")
            return None
    
    def store_pricing_recommendation(self, product_info: Dict, pricing_result: Dict, invoice_id: str = None) -> bool:
        """Store pricing recommendation in database"""
        if not self.db or not pricing_result.get('success'):
            return False
        
        try:
            # Store in product_pricing table
            pricing_data = {
                'product_id': product_info.get('product_id'),
                'cost_price': pricing_result['cost_per_unit'],
                'suggested_price': pricing_result['suggested_price'],
                'min_price': pricing_result['min_price'],
                'max_price': pricing_result['max_price'],
                'markup_percentage': pricing_result['markup_percentage'],
                'adjustments': pricing_result.get('adjustments', []),
                'pricing_date': datetime.now().date().isoformat()
            }
            
            self.db.supabase.table('product_pricing').insert(pricing_data).execute()
            
            # Update products table with latest selling price
            if product_info.get('product_id'):
                self.db.supabase.table('products').update({
                    'selling_price': pricing_result['suggested_price'],
                    'last_price_update': datetime.now().isoformat()
                }).eq('id', product_info['product_id']).execute()
            
            return True
            
        except Exception as e:
            logger.error(f"Error storing pricing recommendation: {e}")
            return False
    
    def get_pricing_history(self, product_id: str, days: int = 30) -> List[Dict]:
        """Get pricing history for a product"""
        if not self.db:
            return []
        
        try:
            from datetime import timedelta
            since_date = (datetime.now() - timedelta(days=days)).date().isoformat()
            
            result = self.db.supabase.table('product_pricing').select(
                'cost_price, suggested_price, markup_percentage, pricing_date, adjustments'
            ).eq('product_id', product_id).gte(
                'pricing_date', since_date
            ).order('pricing_date', desc=True).execute()
            
            return result.data
            
        except Exception as e:
            logger.error(f"Error getting pricing history: {e}")
            return []
    
    def _error_response(self, message: str) -> Dict:
        """Return error response"""
        return {
            'success': False,
            'error': message,
            'suggested_price': 0,
            'markup_percentage': 0
        }


