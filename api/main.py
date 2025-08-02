"""
Main FastAPI application - Component 9
Integrates all components into a complete pipeline
"""

import os
import json
import logging
from typing import List, Optional
from datetime import datetime
from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import aiofiles
import uuid

from database.connection import DatabaseConnection
from api.routes import invoices, products, analytics, human_review
from api.routes import rag_endpoints, pricing
from api import pricing_endpoints
from services.pipeline_orchestrator import PipelineOrchestrator
from services.processing_queue import ProcessingQueue

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Invoice Processing System",
    description="AI-powered invoice processing with Claude",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for frontend
app.mount("/static", StaticFiles(directory="frontend"), name="static")

# Global instances
db = None
pipeline = None
queue = None

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global db, pipeline, queue
    
    logger.info("Starting Invoice Processing System...")
    
    # Initialize database
    db = DatabaseConnection()
    
    # Initialize processing queue
    queue = ProcessingQueue(db.supabase)
    
    # Initialize pipeline orchestrator
    pipeline = PipelineOrchestrator(db)
    
    logger.info("System initialized successfully!")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    if db:
        await db.close()
    logger.info("System shutdown complete")

# Include routers
app.include_router(invoices.router, prefix="/api/v1/invoices", tags=["invoices"])
app.include_router(products.router, prefix="/api/v1/products", tags=["products"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["analytics"])
app.include_router(rag_endpoints.router, tags=["RAG System"])
app.include_router(human_review.router, tags=["human_review"])
app.include_router(pricing.router, tags=["pricing"])
app.include_router(pricing_endpoints.router, tags=["pricing-enhanced"])

# WebSocket endpoint for RAG chat
@app.websocket("/ws/chat")
async def websocket_chat_endpoint(websocket: WebSocket):
    """WebSocket endpoint for RAG chat"""
    from api.websocket.chat_handler import websocket_endpoint
    await websocket_endpoint(websocket, "/chat")



@app.get("/")
async def root():
    """Serve the main invoice upload interface"""
    return FileResponse('frontend/index.html')

@app.get("/chat/")
async def chat_interface():
    """Serve the RAG analytics chat interface"""
    return FileResponse('frontend/chat/index.html')

@app.get("/chat/chat.js")
async def chat_js():
    """Serve the chat JavaScript file"""
    return FileResponse('frontend/chat/chat.js')

@app.get("/app.js")
async def app_js():
    """Serve the main app JavaScript file"""
    return FileResponse('frontend/app.js')

@app.get("/api/")
async def api_root():
    """API root endpoint"""
    return {
        "message": "Invoice Processing System API",
        "version": "1.0.0",
        "endpoints": {
            "upload": "/api/v1/invoices/upload",
            "status": "/api/v1/invoices/{id}/status",
            "products": "/api/v1/products/search",
            "analytics": "/api/v1/analytics/dashboard",
            "rag": "/api/rag/query",
            "docs": "/docs"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check database connection
        db_status = db.supabase.table('vendors').select('id').limit(1).execute()
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "services": {
                "database": "connected" if db_status else "disconnected",
                "pipeline": "ready" if pipeline else "not initialized",
                "queue": "ready" if queue else "not initialized"
            }
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e)
            }
        )