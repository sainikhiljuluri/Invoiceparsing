"""
Analytics Engine for invoice data analysis
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import DBSCAN

logger = logging.getLogger(__name__)


class AnalyticsEngine:
    """Analytics engine for invoice insights"""
    
    def __init__(self, supabase_client):
        self.client = supabase_client
        self.scaler = StandardScaler()
    
    async def detect_anomalies(self, time_period: str = 'last_week') -> List[Dict]:
        """Detect pricing anomalies"""
        
        try:
            # Get date range
            end_date = datetime.now()
            if time_period == 'last_week':
                start_date = end_date - timedelta(days=7)
            elif time_period == 'last_month':
                start_date = end_date - timedelta(days=30)
            else:
                start_date = end_date - timedelta(days=7)
            
            # Get price changes in period
            result = self.client.table('price_history').select(
                '*, products(name, category)'
            ).gte('change_date', start_date.isoformat()).execute()
            
            if not result.data:
                return []
            
            # Analyze price changes
            anomalies = []
            for change in result.data:
                old_cost = float(change['old_cost'])
                new_cost = float(change['new_cost'])
                
                if old_cost > 0:
                    change_percent = ((new_cost - old_cost) / old_cost) * 100
                    
                    # Flag significant changes
                    if abs(change_percent) > 20:  # 20% threshold
                        anomalies.append({
                            'type': 'price_spike' if change_percent > 0 else 'price_drop',
                            'product': change['products']['name'],
                            'old_cost': old_cost,
                            'new_cost': new_cost,
                            'change_percent': change_percent,
                            'date': change['change_date'],
                            'severity': 'high' if abs(change_percent) > 50 else 'medium'
                        })
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Anomaly detection error: {e}")
            return []
    
    async def get_cost_trends(self, product_id: Optional[int] = None,
                             days: int = 30) -> Dict[str, Any]:
        """Get cost trend analysis"""
        
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            query = self.client.table('price_history').select(
                '*, products(name, category)'
            ).gte('change_date', start_date.isoformat())
            
            if product_id:
                query = query.eq('product_id', product_id)
            
            result = query.order('change_date').execute()
            
            if not result.data:
                return {'trends': [], 'summary': {}}
            
            # Calculate trends
            trends = []
            total_changes = len(result.data)
            increases = 0
            decreases = 0
            
            for change in result.data:
                old_cost = float(change['old_cost'])
                new_cost = float(change['new_cost'])
                change_percent = ((new_cost - old_cost) / old_cost) * 100 if old_cost > 0 else 0
                
                trends.append({
                    'product': change['products']['name'],
                    'date': change['change_date'],
                    'old_cost': old_cost,
                    'new_cost': new_cost,
                    'change_percent': change_percent
                })
                
                if change_percent > 0:
                    increases += 1
                elif change_percent < 0:
                    decreases += 1
            
            summary = {
                'total_changes': total_changes,
                'increases': increases,
                'decreases': decreases,
                'stable': total_changes - increases - decreases,
                'period_days': days
            }
            
            return {'trends': trends, 'summary': summary}
            
        except Exception as e:
            logger.error(f"Trend analysis error: {e}")
            return {'trends': [], 'summary': {}}
    
    async def get_vendor_performance(self, days: int = 30) -> List[Dict]:
        """Analyze vendor performance using invoice_items"""
        
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            # Get recent invoice items with vendor info
            result = self.client.table('invoice_items').select(
                '*, invoices(vendors(name), invoice_date), products(name, category)'
            ).gte('created_at', start_date.isoformat()).execute()
            
            vendor_stats = {}
            
            for item in result.data:
                vendor_name = item['invoices']['vendors']['name']
                
                if vendor_name not in vendor_stats:
                    vendor_stats[vendor_name] = {
                        'invoice_count': set(),
                        'total_amount': 0,
                        'item_count': 0,
                        'unique_products': set(),
                        'avg_unit_price': 0,
                        'total_quantity': 0
                    }
                
                # Track unique invoices
                vendor_stats[vendor_name]['invoice_count'].add(item['invoice_id'])
                vendor_stats[vendor_name]['item_count'] += 1
                vendor_stats[vendor_name]['total_amount'] += float(item['total_amount'])
                vendor_stats[vendor_name]['total_quantity'] += float(item['quantity'])
                vendor_stats[vendor_name]['unique_products'].add(item['products']['name'])
            
            # Convert to list and calculate metrics
            performance = []
            for vendor, stats in vendor_stats.items():
                invoice_count = len(stats['invoice_count'])
                performance.append({
                    'vendor_name': vendor,
                    'invoice_count': invoice_count,
                    'item_count': stats['item_count'],
                    'total_amount': stats['total_amount'],
                    'total_quantity': stats['total_quantity'],
                    'unique_products': len(stats['unique_products']),
                    'avg_amount_per_invoice': stats['total_amount'] / invoice_count if invoice_count > 0 else 0,
                    'avg_items_per_invoice': stats['item_count'] / invoice_count if invoice_count > 0 else 0,
                    'avg_unit_price': stats['total_amount'] / stats['total_quantity'] if stats['total_quantity'] > 0 else 0
                })
            
            return sorted(performance, key=lambda x: x['total_amount'], reverse=True)
            
        except Exception as e:
            logger.error(f"Vendor performance analysis error: {e}")
            return []
    
    async def generate_insights(self) -> List[Dict]:
        """Generate business insights"""
        
        insights = []
        
        try:
            # Get recent anomalies
            anomalies = await self.detect_anomalies('last_month')
            if anomalies:
                high_severity = [a for a in anomalies if a['severity'] == 'high']
                if high_severity:
                    insights.append({
                        'type': 'alert',
                        'title': 'High Price Volatility Detected',
                        'description': f'{len(high_severity)} products show significant price changes',
                        'priority': 'high',
                        'data': high_severity[:3]
                    })
            
            # Get vendor performance
            vendor_perf = await self.get_vendor_performance()
            if len(vendor_perf) > 1:
                top_vendor = vendor_perf[0]
                insights.append({
                    'type': 'performance',
                    'title': 'Top Performing Vendor',
                    'description': f"{top_vendor['vendor_name']} leads with ₹{top_vendor['total_amount']:.2f} in transactions",
                    'priority': 'medium',
                    'data': top_vendor
                })
            
            # Store insights
            for insight in insights:
                await self._store_insight(insight)
            
            return insights
            
        except Exception as e:
            logger.error(f"Insight generation error: {e}")
            return []
    
    async def get_invoice_items_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Get detailed invoice items analytics"""
        
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            # Get recent invoice items
            result = self.client.table('invoice_items').select(
                '*, invoices(vendors(name), invoice_date), products(name, category)'
            ).gte('created_at', start_date.isoformat()).execute()
            
            if not result.data:
                return {'summary': {}, 'top_products': [], 'category_breakdown': {}}
            
            # Analytics calculations
            total_items = len(result.data)
            total_amount = sum(float(item['total_amount']) for item in result.data)
            total_quantity = sum(float(item['quantity']) for item in result.data)
            
            # Product analytics
            product_stats = {}
            category_stats = {}
            
            for item in result.data:
                product_name = item['products']['name']
                category = item['products']['category']
                amount = float(item['total_amount'])
                quantity = float(item['quantity'])
                
                # Product stats
                if product_name not in product_stats:
                    product_stats[product_name] = {
                        'total_amount': 0,
                        'total_quantity': 0,
                        'purchase_count': 0,
                        'avg_unit_price': 0
                    }
                
                product_stats[product_name]['total_amount'] += amount
                product_stats[product_name]['total_quantity'] += quantity
                product_stats[product_name]['purchase_count'] += 1
                
                # Category stats
                if category not in category_stats:
                    category_stats[category] = {
                        'total_amount': 0,
                        'item_count': 0
                    }
                
                category_stats[category]['total_amount'] += amount
                category_stats[category]['item_count'] += 1
            
            # Calculate averages and sort
            for product, stats in product_stats.items():
                if stats['total_quantity'] > 0:
                    stats['avg_unit_price'] = stats['total_amount'] / stats['total_quantity']
            
            top_products = sorted(
                [{'product': k, **v} for k, v in product_stats.items()],
                key=lambda x: x['total_amount'],
                reverse=True
            )[:10]
            
            return {
                'summary': {
                    'total_items': total_items,
                    'total_amount': total_amount,
                    'total_quantity': total_quantity,
                    'avg_amount_per_item': total_amount / total_items if total_items > 0 else 0,
                    'period_days': days
                },
                'top_products': top_products,
                'category_breakdown': category_stats
            }
            
        except Exception as e:
            logger.error(f"Invoice items analytics error: {e}")
            return {'summary': {}, 'top_products': [], 'category_breakdown': {}}
    
    async def _store_insight(self, insight: Dict):
        """Store insight in database"""
        try:
            self.client.table('generated_insights').insert({
                'type': insight['type'],
                'title': insight['title'],
                'description': insight['description'],
                'priority': insight['priority'],
                'data': insight.get('data', {}),
                'generated_at': datetime.now().isoformat()
            }).execute()
        except Exception as e:
            logger.error(f"Error storing insight: {e}")
