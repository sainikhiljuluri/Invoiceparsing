"""
RAG System REST API endpoints
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from services.rag.rag_system import AdvancedRAGSystem
from services.analytics.analytics_engine import AnalyticsEngine
from config.database import get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/rag", tags=["RAG System"])

# Initialize RAG system
rag_system = AdvancedRAGSystem()
analytics_engine = AnalyticsEngine(get_supabase_client())


class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None


class QueryResponse(BaseModel):
    answer: str
    suggestions: List[str]
    intent: str
    confidence: float
    session_id: str
    success: bool


@router.post("/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    """Process user query through RAG system"""
    
    try:
        # Generate session ID if not provided
        session_id = request.session_id or str(uuid.uuid4())
        
        # Process query
        result = await rag_system.process_query(
            query=request.query,
            session_id=session_id,
            user_id=request.user_id
        )
        
        return QueryResponse(
            answer=result['answer'],
            suggestions=result.get('suggestions', []),
            intent=result.get('intent', 'general'),
            confidence=result.get('confidence', 0.0),
            session_id=session_id,
            success=result.get('success', True)
        )
        
    except Exception as e:
        logger.error(f"Query processing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/suggestions")
async def get_query_suggestions():
    """Get example queries for users"""
    
    suggestions = [
        "What's the cost of paper towels?",
        "Show me price trends for cleaning supplies",
        "Are there any pricing anomalies this week?",
        "Compare vendor performance this month",
        "What products had the biggest price changes?",
        "Show me recent invoice summary"
    ]
    
    return {"suggestions": suggestions}


@router.get("/analytics/summary")
async def get_analytics_summary():
    """Get analytics summary"""
    
    try:
        # Get recent anomalies
        anomalies = await analytics_engine.detect_anomalies('last_week')
        
        # Get vendor performance
        vendor_performance = await analytics_engine.get_vendor_performance(30)
        
        # Get cost trends
        trends = await analytics_engine.get_cost_trends(days=30)
        
        return {
            "anomalies": len(anomalies),
            "high_severity_anomalies": len([a for a in anomalies if a['severity'] == 'high']),
            "vendor_count": len(vendor_performance),
            "price_changes": trends['summary'].get('total_changes', 0),
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Analytics summary error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/anomalies")
async def get_anomalies(period: str = Query("last_week", description="Time period")):
    """Get detected anomalies"""
    
    try:
        anomalies = await analytics_engine.detect_anomalies(period)
        return {"anomalies": anomalies, "count": len(anomalies)}
        
    except Exception as e:
        logger.error(f"Anomaly retrieval error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/trends")
async def get_trends(days: int = Query(30, description="Number of days")):
    """Get cost trends"""
    
    try:
        trends = await analytics_engine.get_cost_trends(days=days)
        return trends
        
    except Exception as e:
        logger.error(f"Trends retrieval error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/vendors")
async def get_vendor_performance(days: int = Query(30, description="Number of days")):
    """Get vendor performance analysis"""
    
    try:
        performance = await analytics_engine.get_vendor_performance(days)
        return {"vendors": performance, "count": len(performance)}
        
    except Exception as e:
        logger.error(f"Vendor performance error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/insights")
async def get_insights():
    """Get generated business insights"""
    
    try:
        insights = await analytics_engine.generate_insights()
        return {"insights": insights, "count": len(insights)}
        
    except Exception as e:
        logger.error(f"Insights retrieval error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/invoice-items")
async def get_invoice_items_analytics(days: int = Query(30, description="Number of days")):
    """Get detailed invoice items analytics"""
    
    try:
        analytics = await analytics_engine.get_invoice_items_analytics(days)
        return analytics
        
    except Exception as e:
        logger.error(f"Invoice items analytics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch-query")
async def process_batch_queries(queries: List[str], session_id: Optional[str] = None):
    """Process multiple queries in batch"""
    
    try:
        session_id = session_id or str(uuid.uuid4())
        results = []
        
        for query in queries:
            result = await rag_system.process_query(
                query=query,
                session_id=session_id
            )
            results.append({
                "query": query,
                "answer": result['answer'],
                "intent": result.get('intent', 'general'),
                "success": result.get('success', True)
            })
        
        return {
            "results": results,
            "session_id": session_id,
            "processed": len(results)
        }
        
    except Exception as e:
        logger.error(f"Batch query error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    
    try:
        # Test RAG system
        test_result = await rag_system.process_query(
            "test", str(uuid.uuid4())
        )
        
        return {
            "status": "healthy",
            "rag_system": "operational",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
