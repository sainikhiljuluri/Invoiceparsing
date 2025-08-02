"""
Human review queue routes
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()

class ReviewApprovalRequest(BaseModel):
    product_id: str
    user_id: str

@router.get("/queue")
async def get_review_queue(priority: Optional[int] = None):
    """Get items pending human review"""
    from api.main import db
    
    try:
        query = db.supabase.table('human_review_queue').select(
            '*, invoice_items(invoice_product_name)'
        ).eq('status', 'pending')
        
        if priority:
            query = query.eq('priority', priority)
        
        result = await query.order('created_at').execute()
        
        return {
            "items": result.data,
            "total": len(result.data)
        }
        
    except Exception as e:
        logger.error(f"Review queue error: {e}")
        raise HTTPException(500, f"Failed to get review queue: {str(e)}")

@router.post("/{review_id}/approve")
async def approve_match(review_id: str, request: ReviewApprovalRequest):
    """Approve a product match"""
    from api.main import db
    from services.human_review_manager import HumanReviewManager
    
    try:
        manager = HumanReviewManager(db.supabase)
        success = await manager.approve_match(
            review_id,
            request.product_id,
            request.user_id
        )
        
        if success:
            return {"message": "Match approved successfully"}
        else:
            raise HTTPException(400, "Failed to approve match")
            
    except Exception as e:
        logger.error(f"Approval error: {e}")
        raise HTTPException(500, f"Approval failed: {str(e)}")