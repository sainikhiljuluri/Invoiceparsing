"""
Alert Manager Service
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime
from supabase import Client

logger = logging.getLogger(__name__)


class AlertManager:
    """Manage price alerts and notifications"""
    
    def __init__(self, supabase_client: Client):
        self.client = supabase_client
    
    def create_price_alert(
        self, 
        product_id: str, 
        alert_type: str, 
        message: str, 
        priority: str = "medium",
        invoice_id: Optional[str] = None
    ) -> Dict:
        """Create a price alert"""
        alert_data = {
            'product_id': product_id,
            'alert_type': alert_type,
            'alert_message': message,
            'priority': priority,
            'status': 'pending',
            'created_at': datetime.now().isoformat()
        }
        
        if invoice_id:
            alert_data['invoice_id'] = invoice_id
        
        try:
            result = self.client.table('price_alerts').insert(alert_data).execute()
            return result.data[0]
        except Exception as e:
            logger.error(f"Failed to create alert: {e}")
            return {}
    
    def get_pending_alerts(self, limit: int = 50) -> List[Dict]:
        """Get pending alerts"""
        try:
            result = self.client.table('price_alerts').select(
                '*, products(name)'
            ).eq('status', 'pending').order(
                'created_at', desc=True
            ).limit(limit).execute()
            
            return result.data
        except Exception as e:
            logger.error(f"Failed to get alerts: {e}")
            return []
    
    def mark_alert_resolved(self, alert_id: str, resolved_by: str = "system") -> bool:
        """Mark alert as resolved"""
        try:
            self.client.table('price_alerts').update({
                'status': 'resolved',
                'resolved_by': resolved_by,
                'resolved_at': datetime.now().isoformat()
            }).eq('id', alert_id).execute()
            
            return True
        except Exception as e:
            logger.error(f"Failed to resolve alert: {e}")
            return False
