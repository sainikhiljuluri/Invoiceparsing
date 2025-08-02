"""
Repository for price-related database operations
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
from supabase import Client

logger = logging.getLogger(__name__)


class PriceRepository:
    """Handle all price and cost-related database operations"""
    
    def __init__(self, supabase_client: Client):
        self.client = supabase_client
    
    def get_current_product_cost(self, product_id: str) -> Optional[Dict]:
        """Get current cost information for a product"""
        try:
            response = self.client.table('products').select(
                'id, name, cost, currency, last_update_date, last_invoice_number'
            ).eq('id', product_id).execute()
            
            if response.data:
                return response.data[0]
            return None
            
        except Exception as e:
            logger.error(f"Error getting product cost: {e}")
            return None
    
    def update_product_cost(self, product_id: str, cost_data: Dict) -> bool:
        """Update product cost in database"""
        try:
            update_data = {
                'cost': cost_data['cost'],
                'currency': cost_data['currency'],
                'last_update_date': datetime.now().isoformat(),
                'last_invoice_number': cost_data['invoice_number'],
                'last_vendor_id': cost_data.get('vendor_id')
            }
            
            response = self.client.table('products').update(
                update_data
            ).eq('id', product_id).execute()
            
            return bool(response.data)
            
        except Exception as e:
            logger.error(f"Error updating product cost: {e}")
            return False
    
    def create_price_history_entry(self, history_data: Dict) -> bool:
        """Create a price history record"""
        try:
            entry = {
                'product_id': history_data['product_id'],
                'old_cost': history_data.get('old_cost'),
                'new_cost': history_data['new_cost'],
                'currency': history_data['currency'],
                'change_percentage': history_data.get('change_percentage'),
                'invoice_id': history_data['invoice_id'],
                'invoice_number': history_data['invoice_number'],
                'vendor_id': history_data.get('vendor_id'),
                'change_reason': history_data.get('change_reason', 'invoice_update'),
                'created_at': datetime.now().isoformat(),
                'created_by': history_data.get('created_by', 'system')
            }
            
            response = self.client.table('price_history').insert(entry).execute()
            return bool(response.data)
            
        except Exception as e:
            logger.error(f"Error creating price history: {e}")
            return False
    
    def get_price_history(self, product_id: str, days: int = 90) -> List[Dict]:
        """Get price history for a product"""
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            # Try with vendor join first, fallback to without if FK doesn't exist
            try:
                response = self.client.table('price_history').select(
                    '*, vendors(name)'
                ).eq(
                    'product_id', product_id
                ).gte(
                    'created_at', cutoff_date
                ).order(
                    'created_at', desc=True
                ).execute()
            except Exception as e:
                logger.warning(f"Vendor FK not available, querying without vendor join: {e}")
                response = self.client.table('price_history').select(
                    '*'
                ).eq(
                    'product_id', product_id
                ).gte(
                    'created_at', cutoff_date
                ).order(
                    'created_at', desc=True
                ).execute()
            
            return response.data or []
            
        except Exception as e:
            logger.error(f"Error getting price history: {e}")
            return []
    
    def get_price_trends(self, product_id: str) -> Dict:
        """Calculate price trends for a product"""
        try:
            # Get last 90 days of history
            history = self.get_price_history(product_id, 90)
            
            if not history:
                return {
                    'trend': 'stable',
                    'average_change': 0.0,
                    'volatility': 'low',
                    'data_points': 0
                }
            
            # Calculate metrics
            changes = [h['change_percentage'] for h in history if h.get('change_percentage')]
            
            if not changes:
                return {
                    'trend': 'stable',
                    'average_change': 0.0,
                    'volatility': 'low',
                    'data_points': len(history)
                }
            
            avg_change = sum(changes) / len(changes)
            
            # Determine trend
            if avg_change > 5:
                trend = 'increasing'
            elif avg_change < -5:
                trend = 'decreasing'
            else:
                trend = 'stable'
            
            # Calculate volatility
            if changes:
                variance = sum((x - avg_change) ** 2 for x in changes) / len(changes)
                std_dev = variance ** 0.5
                
                if std_dev > 15:
                    volatility = 'high'
                elif std_dev > 5:
                    volatility = 'medium'
                else:
                    volatility = 'low'
            else:
                volatility = 'low'
            
            return {
                'trend': trend,
                'average_change': round(avg_change, 2),
                'volatility': volatility,
                'data_points': len(history),
                'last_change': changes[0] if changes else 0.0
            }
            
        except Exception as e:
            logger.error(f"Error calculating price trends: {e}")
            return {
                'trend': 'unknown',
                'average_change': 0.0,
                'volatility': 'unknown',
                'data_points': 0
            }
    
    def get_vendor_price_comparison(self, product_id: str) -> List[Dict]:
        """Get price comparison across vendors for a product"""
        try:
            # Get recent prices from different vendors
            try:
                response = self.client.table('price_history').select(
                    'vendor_id, new_cost, currency, created_at, vendors(name)'
                ).eq(
                    'product_id', product_id
                ).gte(
                    'created_at', 
                    (datetime.now() - timedelta(days=30)).isoformat()
                ).order(
                    'created_at', desc=True
                ).execute()
            except Exception as e:
                logger.warning(f"Vendor FK not available for comparison, querying without vendor join: {e}")
                response = self.client.table('price_history').select(
                    'vendor_id, new_cost, currency, created_at'
                ).eq(
                    'product_id', product_id
                ).gte(
                    'created_at', 
                    (datetime.now() - timedelta(days=30)).isoformat()
                ).order(
                    'created_at', desc=True
                ).execute()
            
            if not response.data:
                return []
            
            # Group by vendor and get latest price
            vendor_prices = {}
            for entry in response.data:
                vendor_id = entry['vendor_id']
                if vendor_id not in vendor_prices:
                    # Handle vendor name - may not be available if FK doesn't exist
                    vendor_name = 'Unknown'
                    if entry.get('vendors') and isinstance(entry['vendors'], dict):
                        vendor_name = entry['vendors'].get('name', 'Unknown')
                    elif vendor_id:
                        vendor_name = f'Vendor {vendor_id}'
                    
                    vendor_prices[vendor_id] = {
                        'vendor_id': vendor_id,
                        'vendor_name': vendor_name,
                        'latest_cost': entry['new_cost'],
                        'currency': entry['currency'],
                        'last_update': entry['created_at']
                    }
            
            return list(vendor_prices.values())
            
        except Exception as e:
            logger.error(f"Error getting vendor price comparison: {e}")
            return []