"""
WebSocket chat handler for real-time RAG interactions
"""

import json
import logging
import asyncio
import uuid
from typing import Dict, Set, Any
from datetime import datetime

from fastapi import WebSocket, WebSocketDisconnect

from services.rag.rag_system import AdvancedRAGSystem
from services.analytics.analytics_engine import AnalyticsEngine
from config.database import get_supabase_client

logger = logging.getLogger(__name__)


class ChatHandler:
    """WebSocket chat handler for RAG system"""
    
    def __init__(self):
        self.connections: Dict[str, WebSocket] = {}
        self.user_sessions: Dict[str, str] = {}  # connection_id -> session_id
        self.rag_system = AdvancedRAGSystem()
        self.analytics_engine = AnalyticsEngine(get_supabase_client())
    
    async def handle_connection(self, websocket, path):
        """Handle new WebSocket connection"""
        
        connection_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())
        
        self.connections[connection_id] = websocket
        self.user_sessions[connection_id] = session_id
        
        logger.info(f"New chat connection: {connection_id}")
        
        try:
            # Accept WebSocket connection
            await websocket.accept()
            
            # Send welcome message
            await self._send_message(websocket, {
                'type': 'welcome',
                'session_id': session_id,
                'message': 'Connected to RAG Chat System',
                'suggestions': [
                    "What's the cost of paper towels?",
                    "Show me price trends",
                    "Any pricing anomalies?"
                ]
            })
            
            # Handle messages
            while True:
                try:
                    message = await websocket.receive_text()
                    await self._handle_message(websocket, connection_id, message)
                except Exception as e:
                    logger.error(f"Message handling error: {e}")
                    break
                
        except WebSocketDisconnect:
            logger.info(f"Connection closed: {connection_id}")
        except Exception as e:
            logger.error(f"Connection error: {e}")
        finally:
            await self._cleanup_connection(connection_id)
    
    async def _handle_message(self, websocket, connection_id: str, message: str):
        """Handle incoming message"""
        
        try:
            data = json.loads(message)
            message_type = data.get('type', 'query')
            
            if message_type == 'query':
                await self._handle_query(websocket, connection_id, data)
            elif message_type == 'typing':
                await self._handle_typing(websocket, connection_id, data)
            elif message_type == 'get_suggestions':
                await self._handle_get_suggestions(websocket)
            elif message_type == 'get_analytics':
                await self._handle_get_analytics(websocket)
            
        except json.JSONDecodeError:
            await self._send_error(websocket, "Invalid JSON format")
        except Exception as e:
            logger.error(f"Message handling error: {e}")
            await self._send_error(websocket, str(e))
    
    async def _handle_query(self, websocket, connection_id: str, data: Dict):
        """Handle user query"""
        
        query = data.get('query', '').strip()
        if not query:
            await self._send_error(websocket, "Empty query")
            return
        
        session_id = self.user_sessions.get(connection_id)
        
        try:
            # Send typing indicator
            await self._send_message(websocket, {
                'type': 'typing',
                'is_typing': True
            })
            
            # Process query
            result = await self.rag_system.process_query(
                query=query,
                session_id=session_id,
                user_id=data.get('user_id')
            )
            
            # Send response
            await self._send_message(websocket, {
                'type': 'response',
                'query': query,
                'answer': result['answer'],
                'suggestions': result.get('suggestions', []),
                'intent': result.get('intent', 'general'),
                'confidence': result.get('confidence', 0.0),
                'timestamp': datetime.now().isoformat(),
                'success': result.get('success', True)
            })
            
            # Stop typing indicator
            await self._send_message(websocket, {
                'type': 'typing',
                'is_typing': False
            })
            
        except Exception as e:
            logger.error(f"Query processing error: {e}")
            await self._send_error(websocket, f"Query processing failed: {str(e)}")
    
    async def _handle_typing(self, websocket, connection_id: str, data: Dict):
        """Handle typing indicator"""
        
        # Echo typing status back (for multi-user scenarios)
        await self._send_message(websocket, {
            'type': 'typing_echo',
            'is_typing': data.get('is_typing', False),
            'user_id': data.get('user_id')
        })
    
    async def _handle_get_suggestions(self, websocket):
        """Handle request for query suggestions"""
        
        suggestions = [
            "What's the cost of paper towels?",
            "Show me price trends for cleaning supplies",
            "Are there any pricing anomalies this week?",
            "Compare vendor performance this month",
            "What products had the biggest price changes?",
            "Show me recent invoice summary"
        ]
        
        await self._send_message(websocket, {
            'type': 'suggestions',
            'suggestions': suggestions
        })
    
    async def _handle_get_analytics(self, websocket):
        """Handle request for analytics summary"""
        
        try:
            # Get analytics summary
            anomalies = await self.analytics_engine.detect_anomalies('last_week')
            vendor_performance = await self.analytics_engine.get_vendor_performance(30)
            trends = await self.analytics_engine.get_cost_trends(days=30)
            
            summary = {
                'anomalies_count': len(anomalies),
                'high_severity_anomalies': len([a for a in anomalies if a['severity'] == 'high']),
                'vendor_count': len(vendor_performance),
                'price_changes': trends['summary'].get('total_changes', 0),
                'top_vendor': vendor_performance[0]['vendor_name'] if vendor_performance else None,
                'last_updated': datetime.now().isoformat()
            }
            
            await self._send_message(websocket, {
                'type': 'analytics',
                'summary': summary
            })
            
        except Exception as e:
            logger.error(f"Analytics retrieval error: {e}")
            await self._send_error(websocket, "Failed to get analytics")
    
    async def _send_message(self, websocket, data: Dict):
        """Send message to WebSocket"""
        
        try:
            message = json.dumps(data)
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Send message error: {e}")
    
    async def _send_error(self, websocket, error_message: str):
        """Send error message"""
        
        await self._send_message(websocket, {
            'type': 'error',
            'error': error_message,
            'timestamp': datetime.now().isoformat()
        })
    
    async def _cleanup_connection(self, connection_id: str):
        """Clean up connection"""
        
        if connection_id in self.connections:
            del self.connections[connection_id]
        
        if connection_id in self.user_sessions:
            del self.user_sessions[connection_id]
        
        logger.info(f"Cleaned up connection: {connection_id}")
    
    async def broadcast_analytics_update(self):
        """Broadcast analytics updates to all connected clients"""
        
        if not self.connections:
            return
        
        try:
            # Get latest analytics
            anomalies = await self.analytics_engine.detect_anomalies('last_week')
            
            update_message = {
                'type': 'analytics_update',
                'anomalies_count': len(anomalies),
                'high_severity': len([a for a in anomalies if a['severity'] == 'high']),
                'timestamp': datetime.now().isoformat()
            }
            
            # Send to all connections
            for websocket in self.connections.values():
                try:
                    await self._send_message(websocket, update_message)
                except Exception as e:
                    logger.error(f"Broadcast error: {e}")
                    
        except Exception as e:
            logger.error(f"Analytics broadcast error: {e}")


# Global chat handler instance
chat_handler = ChatHandler()


async def websocket_endpoint(websocket, path):
    """WebSocket endpoint for chat"""
    await chat_handler.handle_connection(websocket, path)
