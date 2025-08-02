"""
Manage human review queue for uncertain matches
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime
from supabase import Client

logger = logging.getLogger(__name__)


class HumanReviewManager:
    """Manage the human review queue for product matching"""
    
    def __init__(self, supabase_client: Client):
        self.client = supabase_client
    
    def add_to_review_queue(self, review_item: Dict) -> Optional[str]:
        """Add an item to the human review queue"""
        try:
            review_data = {
                'invoice_id': review_item['invoice_id'],
                'invoice_product_name': review_item['invoice_product_name'],
                'suggested_product_id': review_item.get('suggested_product_id'),
                'confidence_score': review_item['confidence_score'],
                'match_strategy': review_item['match_strategy'],
                'priority': review_item['priority'],
                'alternatives': review_item.get('alternatives', []),
                'status': 'pending',
                'created_at': datetime.now().isoformat()
            }
            
            response = self.client.table('human_review_queue').insert(review_data).execute()
            
            if response.data:
                return response.data[0]['id']
            return None
            
        except Exception as e:
            logger.error(f"Error adding to review queue: {e}")
            return None
    
    def get_pending_reviews(self, priority: Optional[int] = None) -> List[Dict]:
        """Get pending review items"""
        try:
            query = self.client.table('human_review_queue').select('*').eq('status', 'pending')
            
            if priority:
                query = query.eq('priority', priority)
            
            response = query.order('created_at', desc=False).execute()
            return response.data or []
            
        except Exception as e:
            logger.error(f"Error getting pending reviews: {e}")
            return []
    
    def approve_match(self, review_id: str, product_id: str, user_id: str) -> bool:
        """Approve a product match from review"""
        try:
            # Update review status
            response = self.client.table('human_review_queue').update({
                'status': 'approved',
                'approved_product_id': product_id,
                'reviewed_by': user_id,
                'reviewed_at': datetime.now().isoformat()
            }).eq('id', review_id).execute()
            
            if not response.data:
                return False
            
            review_item = response.data[0]
            
            # Create product mapping for future use
            mapping_data = {
                'invoice_product_name': review_item['invoice_product_name'],
                'product_id': product_id,
                'confidence_score': 1.0,  # Human approved = 100% confidence
                'match_strategy': 'human_approved',
                'created_by': user_id
            }
            
            mapping_response = self.client.table('product_mappings').insert(mapping_data).execute()
            
            return bool(mapping_response.data)
            
        except Exception as e:
            logger.error(f"Error approving match: {e}")
            return False
    
    def reject_match(self, review_id: str, user_id: str, reason: Optional[str] = None) -> bool:
        """Reject a match and mark for product creation"""
        try:
            response = self.client.table('human_review_queue').update({
                'status': 'rejected',
                'rejection_reason': reason,
                'reviewed_by': user_id,
                'reviewed_at': datetime.now().isoformat()
            }).eq('id', review_id).execute()
            
            return bool(response.data)
            
        except Exception as e:
            logger.error(f"Error rejecting match: {e}")
            return False