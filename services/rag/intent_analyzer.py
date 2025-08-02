"""
Intent detection for user queries
"""

from typing import Dict, List
import re


class IntentAnalyzer:
    """Analyze user intent from queries"""
    
    def __init__(self):
        self.intent_patterns = {
            'cost_query': {
                'keywords': ['cost', 'price', 'how much', 'pay', 'expense'],
                'patterns': [
                    r'what.{0,10}cost',
                    r'how much.{0,10}pay',
                    r'price of',
                    r'cost.{0,10}for'
                ],
                'weight': 1.0
            },
            'trend_analysis': {
                'keywords': ['trend', 'change', 'increase', 'decrease', 'history', 'recent', 'recently', 'latest', 'new'],
                'patterns': [
                    r'trend.{0,10}(month|week|year)',
                    r'(increas|decreas).{0,10}price',
                    r'price.{0,10}history',
                    r'recent.{0,15}(price|product|upload)',
                    r'recently.{0,15}(had|upload|add)',
                    r'latest.{0,10}(price|product)',
                    r'what.{0,15}products.{0,15}recent',
                    r'products.{0,15}recently.{0,15}(price|had)'
                ],
                'weight': 0.9
            },
            'anomaly_check': {
                'keywords': ['anomaly', 'unusual', 'strange', 'weird', 'wrong'],
                'patterns': [
                    r'any.{0,10}(anomal|unusual)',
                    r'something.{0,10}wrong',
                    r'check.{0,10}(issue|problem)'
                ],
                'weight': 0.95
            },
            'pricing_query': {
                'keywords': ['suggest price', 'selling price', 'recommend price', 'price suggestion', 'markup', 'profit margin', 'sell it for', 'price can I sell'],
                'patterns': [
                    r'suggest.{0,10}price',
                    r'selling.{0,10}price',
                    r'recommend.{0,10}price',
                    r'price.{0,10}suggest',
                    r'what.{0,10}should.{0,10}sell',
                    r'how.{0,10}much.{0,10}sell',
                    r'markup.{0,10}for',
                    r'profit.{0,10}margin',
                    r'price.{0,10}can.{0,10}I.{0,10}sell',
                    r'sell.{0,10}it.{0,10}for',
                    r'what.{0,10}price.{0,10}sell',
                    r'selling.{0,10}recommendation',
                    r'price.{0,10}recommendation'
                ],
                'weight': 1.0
            },
            'pricing_analysis': {
                'keywords': ['price analysis', 'pricing performance', 'margin analysis', 'pricing trends'],
                'patterns': [
                    r'price.{0,10}analysis',
                    r'pricing.{0,10}performance',
                    r'margin.{0,10}analysis',
                    r'pricing.{0,10}trend',
                    r'analyze.{0,10}pricing',
                    r'pricing.{0,10}history'
                ],
                'weight': 0.95
            },
            'bulk_pricing': {
                'keywords': ['bulk pricing', 'category pricing', 'price all', 'pricing for category'],
                'patterns': [
                    r'bulk.{0,10}pricing',
                    r'category.{0,10}pricing',
                    r'price.{0,10}all',
                    r'pricing.{0,10}for.{0,10}category',
                    r'all.{0,10}products.{0,10}price'
                ],
                'weight': 0.9
            },
            'vendor_comparison': {
                'keywords': ['compare', 'versus', 'better', 'cheaper', 'vendor'],
                'patterns': [
                    r'compar.{0,10}vendor',
                    r'which.{0,10}better',
                    r'versus|vs\.?'
                ],
                'weight': 0.85
            },
            'product_details': {
                'keywords': ['barcode', 'brand', 'category', 'details', 'information', 'specs', 'specification'],
                'patterns': [
                    r'barcode.{0,10}(of|for)',
                    r'what.{0,10}(is|are).{0,10}(barcode|brand|category)',
                    r'(show|get|find).{0,10}(barcode|brand|category|details)',
                    r'product.{0,10}(information|details|specs)',
                    r'(brand|category|barcode).{0,10}(of|for)'
                ],
                'weight': 0.95
            }
        }
    
    async def analyze(self, query: str) -> Dict[str, any]:
        """Analyze query intent"""
        query_lower = query.lower()
        
        best_intent = 'general'
        best_score = 0.0
        
        for intent_type, config in self.intent_patterns.items():
            score = self._calculate_score(query_lower, config)
            
            if score > best_score:
                best_score = score
                best_intent = intent_type
        
        return {
            'type': best_intent,
            'confidence': best_score,
            'query': query
        }
    
    def _calculate_score(self, query: str, config: Dict) -> float:
        """Calculate intent score"""
        score = 0.0
        
        # Check keywords
        for keyword in config['keywords']:
            if keyword in query:
                score += 0.5
        
        # Check patterns
        for pattern in config.get('patterns', []):
            if re.search(pattern, query):
                score += 1.0
        
        # Apply weight
        score *= config.get('weight', 1.0)
        
        # Normalize to 0-1
        return min(score / 2.0, 1.0)
