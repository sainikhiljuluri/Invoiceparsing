"""
Conversation memory management
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)


class ConversationMemory:
    """Manage conversation context and memory"""
    
    def __init__(self, supabase_client):
        self.client = supabase_client
    
    async def add_turn(self, session_id: str, user_query: str, 
                      assistant_response: str, intent: str, 
                      entities: Dict, user_id: Optional[str] = None):
        """Add conversation turn to memory"""
        
        try:
            self.client.table('conversation_memory').insert({
                'session_id': session_id,
                'user_id': user_id,
                'user_query': user_query,
                'assistant_response': assistant_response,
                'intent': intent,
                'entities': json.dumps(entities),
                'timestamp': datetime.now().isoformat()
            }).execute()
            
        except Exception as e:
            logger.error(f"Error adding conversation turn: {e}")
    
    async def get_context(self, session_id: str, limit: int = 5) -> List[Dict]:
        """Get recent conversation context"""
        
        try:
            result = self.client.table('conversation_memory').select(
                '*'
            ).eq('session_id', session_id).order(
                'timestamp', desc=True
            ).limit(limit).execute()
            
            # Reverse to get chronological order
            context = list(reversed(result.data))
            
            # Parse entities JSON
            for turn in context:
                try:
                    turn['entities'] = json.loads(turn['entities'])
                except (json.JSONDecodeError, TypeError):
                    turn['entities'] = {}
            
            return context
            
        except Exception as e:
            logger.error(f"Error getting conversation context: {e}")
            return []
    
    async def clear_session(self, session_id: str):
        """Clear conversation memory for session"""
        
        try:
            self.client.table('conversation_memory').delete().eq(
                'session_id', session_id
            ).execute()
            
        except Exception as e:
            logger.error(f"Error clearing session: {e}")
    
    async def cleanup_old_conversations(self, days: int = 30):
        """Clean up old conversation data"""
        
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            self.client.table('conversation_memory').delete().lt(
                'timestamp', cutoff_date.isoformat()
            ).execute()
            
            logger.info(f"Cleaned up conversations older than {days} days")
            
        except Exception as e:
            logger.error(f"Error cleaning up conversations: {e}")
