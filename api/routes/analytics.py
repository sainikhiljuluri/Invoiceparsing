"""
Analytics and dashboard routes
"""

import logging
from fastapi import APIRouter, HTTPException
from typing import Dict

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/dashboard")
async def get_dashboard_data():
    """Get dashboard analytics data"""
    from api.main import db
    
    try:
        # Get processing stats
        processing_stats = db.supabase.rpc('get_processing_stats').execute()
        
        # Get recent alerts
        alerts = db.supabase.table('price_alerts').select(
            '*, products(name)'
        ).eq('status', 'pending').order(
            'created_at', desc=True
        ).limit(10).execute()
        
        # Get recent invoices
        recent_invoices = db.supabase.table('invoices').select(
            'id, invoice_number, vendor_name, total_amount, processing_status, created_at'
        ).order('created_at', desc=True).limit(10).execute()
        
        return {
            "stats": processing_stats.data,
            "recent_alerts": alerts.data,
            "recent_invoices": recent_invoices.data
        }
        
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        raise HTTPException(500, f"Failed to get dashboard data: {str(e)}")

@router.get("/insights")
async def get_business_insights():
    """Get business insights and trends"""
    from api.main import db
    
    try:
        # Price trend analysis
        trends = db.supabase.rpc('analyze_price_trends').execute()
        
        # Vendor performance
        vendor_stats = db.supabase.rpc('get_vendor_statistics').execute()
        
        return {
            "price_trends": trends.data,
            "vendor_performance": vendor_stats.data
        }
        
    except Exception as e:
        logger.error(f"Insights error: {e}")
        raise HTTPException(500, f"Failed to get insights: {str(e)}")