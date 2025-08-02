#!/usr/bin/env python3
"""
WebSocket server for RAG chat functionality
Run this separately from the main FastAPI server
"""

import asyncio
import logging
import websockets
from api.websocket.chat_handler import websocket_endpoint

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    """Start WebSocket server"""
    
    host = "0.0.0.0"
    port = 8001
    
    logger.info(f"Starting WebSocket server on {host}:{port}")
    
    # Start WebSocket server
    server = await websockets.serve(
        websocket_endpoint,
        host,
        port,
        ping_interval=20,
        ping_timeout=10
    )
    
    logger.info("WebSocket server started successfully")
    logger.info("Chat interface available at: ws://localhost:8001/chat")
    
    # Keep server running
    await server.wait_closed()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("WebSocket server stopped")
    except Exception as e:
        logger.error(f"Server error: {e}")
