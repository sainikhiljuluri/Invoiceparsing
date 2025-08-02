"""
Processing queue management
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime
from supabase import Client

logger = logging.getLogger(__name__)


class ProcessingQueue:
    """Manage invoice processing queue"""
    
    def __init__(self, supabase_client: Client):
        self.client = supabase_client
    
    def add_to_queue(self, item: Dict) -> Dict:
        """Add invoice to processing queue"""
        queue_item = {
            'invoice_id': item['id'],
            'filename': item['filename'],
            'file_path': item['file_path'],
            'priority': item.get('priority', 5),
            'status': 'queued'
        }
        
        # Add file_size if provided
        if 'file_size' in item:
            queue_item['file_size'] = item['file_size']
        
        result = self.client.table('processing_queue').insert(queue_item).execute()
        if result.data:
            return result.data[0]
        else:
            raise Exception(f"Failed to insert to queue: {result}")
    
    def get_next_item(self) -> Optional[Dict]:
        """Get next item to process based on priority"""
        result = self.client.table('processing_queue').select('*').eq(
            'status', 'queued'
        ).order('priority').order('created_at').limit(1).execute()
        
        if result.data:
            item = result.data[0]
            
            # Update status to processing
            self.client.table('processing_queue').update({
                'status': 'processing',
                'started_at': datetime.now().isoformat()
            }).eq('id', item['id']).execute()
            
            return item
        
        return None
    
    def get_queue_position(self, invoice_id: str) -> int:
        """Get position in queue"""
        result = self.client.table('processing_queue').select('id').eq(
            'status', 'queued'
        ).order('priority').order('created_at').execute()
        
        for i, item in enumerate(result.data):
            if item['id'] == invoice_id:
                return i + 1
        
        return 0
    
    def mark_completed(self, invoice_id: str):
        """Mark item as completed"""
        self.client.table('processing_queue').update({
            'status': 'completed',
            'completed_at': datetime.now().isoformat()
        }).eq('invoice_id', invoice_id).execute()
    
    async def mark_failed(self, invoice_id: str, error: str):
        """Mark item as failed"""
        await self.client.table('processing_queue').update({
            'status': 'failed',
            'error_message': error,
            'failed_at': datetime.now().isoformat()
        }).eq('invoice_id', invoice_id).execute()