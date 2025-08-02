"""
Analytics and insights for pricing decisions
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import statistics

logger = logging.getLogger(__name__)

class PricingAnalytics:
    """Generate pricing analytics and insights"""
    
    def __init__(self, database_connection):
        self.db = database_connection
    
    def analyze_pricing_performance(self, product_id: str, 
                                  days: int = 30) -> Dict:
        """Analyze pricing performance for a product"""
        
        # Get historical data
        history = self._get_price_history(product_id, days)
        if not history:
            return {'error': 'No historical data available'}
        
        # Get sales data if available
        sales = self._get_sales_data(product_id, days)
        
        # Calculate metrics
        metrics = {
            'product_id': product_id,
            'analysis_period': f"{days} days",
            'price_metrics': self._calculate_price_metrics(history),
            'margin_analysis': self._analyze_margins(history),
            'price_elasticity': self._estimate_elasticity(history, sales),
            'optimal_price_range': self._suggest_optimal_range(history, sales),
            'recommendations': []
        }
        
        # Generate recommendations
        metrics['recommendations'] = self._generate_recommendations(metrics)
        
        return metrics
    
    def _calculate_price_metrics(self, history: List[Dict]) -> Dict:
        """Calculate price metrics from history"""
        costs = [h['cost'] for h in history]
        prices = [h['selling_price'] for h in history if h.get('selling_price')]
        
        if not prices:
            prices = [c * 1.45 for c in costs]  # Use default markup if no selling prices
        
        return {
            'avg_cost': statistics.mean(costs),
            'avg_selling_price': statistics.mean(prices),
            'cost_volatility': statistics.stdev(costs) if len(costs) > 1 else 0,
            'price_volatility': statistics.stdev(prices) if len(prices) > 1 else 0,
            'min_cost': min(costs),
            'max_cost': max(costs),
            'cost_trend': 'increasing' if costs[-1] > costs[0] else 'decreasing'
        }
    
    def _analyze_margins(self, history: List[Dict]) -> Dict:
        """Analyze profit margins"""
        margins = []
        for h in history:
            if h.get('selling_price') and h.get('cost'):
                margin = ((h['selling_price'] - h['cost']) / h['cost']) * 100
                margins.append(margin)
        
        if not margins:
            return {'status': 'No margin data available'}
        
        return {
            'avg_margin_percentage': statistics.mean(margins),
            'min_margin': min(margins),
            'max_margin': max(margins),
            'margin_consistency': statistics.stdev(margins) if len(margins) > 1 else 0,
            'current_margin': margins[-1] if margins else None
        }
    
    def _estimate_elasticity(self, history: List[Dict], 
                           sales: List[Dict]) -> Dict:
        """Estimate price elasticity of demand"""
        if not sales or len(sales) < 2:
            return {'status': 'Insufficient data for elasticity calculation'}
        
        # Simple elasticity calculation
        price_changes = []
        quantity_changes = []
        
        for i in range(1, len(sales)):
            if sales[i].get('price') and sales[i-1].get('price'):
                price_change = (sales[i]['price'] - sales[i-1]['price']) / sales[i-1]['price']
                quantity_change = (sales[i]['quantity'] - sales[i-1]['quantity']) / sales[i-1]['quantity']
                
                if price_change != 0:
                    elasticity = quantity_change / price_change
                    price_changes.append(price_change)
                    quantity_changes.append(elasticity)
        
        if not quantity_changes:
            return {'status': 'No price changes to analyze'}
        
        avg_elasticity = statistics.mean(quantity_changes)
        
        return {
            'elasticity_coefficient': avg_elasticity,
            'demand_type': 'elastic' if abs(avg_elasticity) > 1 else 'inelastic',
            'interpretation': self._interpret_elasticity(avg_elasticity)
        }
    
    def _interpret_elasticity(self, elasticity: float) -> str:
        """Interpret elasticity coefficient"""
        if elasticity < -1:
            return "Highly elastic - customers very sensitive to price changes"
        elif elasticity < -0.5:
            return "Moderately elastic - some price sensitivity"
        elif elasticity < 0:
            return "Inelastic - customers less sensitive to price"
        else:
            return "Positive elasticity - unusual, may indicate other factors"
    
    def _suggest_optimal_range(self, history: List[Dict], 
                             sales: List[Dict]) -> Dict:
        """Suggest optimal price range"""
        costs = [h['cost'] for h in history]
        current_cost = costs[-1]
        
        # Base calculation on category and performance
        suggested_min = current_cost * 1.25
        suggested_max = current_cost * 1.60
        
        # Adjust based on sales performance if available
        if sales:
            best_performing = max(sales, key=lambda x: x.get('profit', 0))
            if best_performing.get('price'):
                suggested_optimal = best_performing['price']
            else:
                suggested_optimal = current_cost * 1.45
        else:
            suggested_optimal = current_cost * 1.45
        
        return {
            'current_cost': current_cost,
            'suggested_minimum': round(suggested_min, 2),
            'suggested_optimal': round(suggested_optimal, 2),
            'suggested_maximum': round(suggested_max, 2),
            'margin_at_optimal': round((suggested_optimal / current_cost - 1) * 100, 1)
        }
    
    def _get_price_history(self, product_id: str, days: int) -> List[Dict]:
        """Get price history from database"""
        try:
            since_date = (datetime.now() - timedelta(days=days)).date().isoformat()
            
            result = self.db.supabase.table('product_pricing').select(
                'cost_price, suggested_price, pricing_date, markup_percentage'
            ).eq('product_id', product_id).gte(
                'pricing_date', since_date
            ).order('pricing_date').execute()
            
            # Convert to expected format
            history = []
            for item in result.data:
                history.append({
                    'cost': item['cost_price'],
                    'selling_price': item['suggested_price'],
                    'update_date': item['pricing_date'],
                    'markup_percentage': item['markup_percentage']
                })
            
            return history
        except Exception as e:
            logger.error(f"Error getting price history: {e}")
            return []
    
    def _get_sales_data(self, product_id: str, days: int) -> List[Dict]:
        """Get sales data from database"""
        try:
            since_date = (datetime.now() - timedelta(days=days)).date().isoformat()
            
            result = self.db.supabase.table('sales_data').select(
                'date, quantity, price, cost, profit'
            ).eq('product_id', product_id).gte(
                'date', since_date
            ).order('date').execute()
            
            return result.data
        except Exception as e:
            logger.error(f"Error getting sales data: {e}")
            return []
    
    def _generate_recommendations(self, metrics: Dict) -> List[str]:
        """Generate pricing recommendations"""
        recommendations = []
        
        # Check margins
        margin_data = metrics.get('margin_analysis', {})
        if margin_data.get('avg_margin_percentage'):
            avg_margin = margin_data['avg_margin_percentage']
            if avg_margin < 20:
                recommendations.append(
                    f"Low margin ({avg_margin:.1f}%) - consider price increase"
                )
            elif avg_margin > 70:
                recommendations.append(
                    f"Very high margin ({avg_margin:.1f}%) - may be overpriced"
                )
        
        # Check volatility
        price_metrics = metrics.get('price_metrics', {})
        if price_metrics.get('cost_volatility', 0) > 10:
            recommendations.append(
                "High cost volatility - implement dynamic pricing"
            )
        
        # Check elasticity
        elasticity = metrics.get('price_elasticity', {})
        if elasticity.get('demand_type') == 'elastic':
            recommendations.append(
                "Price sensitive product - small changes have big impact"
            )
        
        # Optimal pricing
        optimal_range = metrics.get('optimal_price_range', {})
        if optimal_range.get('margin_at_optimal'):
            recommendations.append(
                f"Target {optimal_range['margin_at_optimal']:.1f}% margin "
                f"at ₹{optimal_range['suggested_optimal']}"
            )
        
        return recommendations

