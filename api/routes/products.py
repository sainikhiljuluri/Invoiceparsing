"""
Product management routes
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()

class ProductSearchRequest(BaseModel):
    query: str
    limit: int = 10

class ProductResponse(BaseModel):
    id: str
    name: str
    brand: Optional[str]
    category: Optional[str]
    cost: Optional[float]
    currency: str

@router.post("/search", response_model=List[ProductResponse])
async def search_products(request: ProductSearchRequest):
    """Search for products"""
    from api.main import db
    
    try:
        result = db.supabase.table('products').select(
            'id, name, brand, category, cost, currency'
        ).ilike('name', f'%{request.query}%').limit(request.limit).execute()
        
        return result.data
        
    except Exception as e:
        logger.error(f"Product search error: {e}")
        raise HTTPException(500, f"Search failed: {str(e)}")

@router.get("/{product_id}/history")
async def get_product_price_history(
    product_id: str,
    days: int = Query(default=90, ge=1, le=365)
):
    """Get price history for a product"""
    from api.main import db
    from datetime import datetime, timedelta
    
    try:
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        result = db.supabase.table('price_history').select(
            '*, vendors(name)'
        ).eq('product_id', product_id).gte(
            'created_at', cutoff_date
        ).order('created_at', desc=True).execute()
        
        return {
            "product_id": product_id,
            "history": result.data,
            "days": days
        }
        
    except Exception as e:
        logger.error(f"Price history error: {e}")
        raise HTTPException(500, f"Failed to get history: {str(e)}")