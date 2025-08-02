"""
Human Review API Endpoints
Handles the review queue for low-confidence product matches
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Optional
from pydantic import BaseModel
import json
from datetime import datetime
from config.database import get_supabase_client

router = APIRouter(prefix="/api/v1/review", tags=["human_review"])

# Pydantic models for request/response
class ReviewDecision(BaseModel):
    product_id: str
    create_mapping: bool = True
    confidence_override: Optional[float] = None

class RejectDecision(BaseModel):
    reason: str
    correct_product_id: Optional[str] = None
    create_mapping: bool = False

class NewProductData(BaseModel):
    name: str
    brand: str
    category: str
    unit_type: str
    cost_per_unit: float
    vendor_key: str

@router.get("/queue")
async def get_review_queue(
    priority: Optional[int] = None,
    limit: int = 20,
    status: str = "pending"
) -> List[Dict]:
    """Get items pending human review"""
    try:
        supabase = get_supabase_client()
        
        # Build query with filters
        query = supabase.table("human_review_queue").select("*")
        
        if priority:
            query = query.eq("priority", priority)
        
        query = query.eq("status", status)
        query = query.order("priority", desc=False)  # High priority first
        query = query.order("created_at", desc=False)  # Oldest first
        query = query.limit(limit)
        
        result = query.execute()
        
        # Parse product_info JSON for each item
        items = []
        for item in result.data:
            item_data = item.copy()
            if item_data.get('product_info'):
                item_data['product_info'] = json.loads(item_data['product_info'])
            items.append(item_data)
        
        return items
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch review queue: {str(e)}")

@router.get("/item/{review_id}")
async def get_review_item(review_id: str) -> Dict:
    """Get detailed item for review with suggestions"""
    try:
        supabase = get_supabase_client()
        
        # Get the review item
        result = supabase.table("human_review_queue").select("*").eq("id", review_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Review item not found")
        
        item = result.data[0]
        item['product_info'] = json.loads(item['product_info'])
        
        # Get suggested products if available
        product_info = item['product_info']
        suggestions = product_info.get('suggested_matches', [])
        
        # Enrich suggestions with full product details
        if suggestions:
            product_ids = [s.get('product_id') for s in suggestions if s.get('product_id')]
            if product_ids:
                products_result = supabase.table("products").select("*").in_("id", product_ids).execute()
                products_map = {p['id']: p for p in products_result.data}
                
                # Merge product details with suggestions
                for suggestion in suggestions:
                    if suggestion.get('product_id') in products_map:
                        suggestion['product_details'] = products_map[suggestion['product_id']]
        
        return {
            "review_item": item,
            "suggestions": suggestions,
            "invoice_context": {
                "invoice_id": item['invoice_id'],
                "vendor": product_info.get('vendor', 'Unknown')
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch review item: {str(e)}")

@router.post("/approve/{review_id}")
async def approve_match(
    review_id: str,
    decision: ReviewDecision
) -> Dict:
    """Approve a product match and optionally create mapping"""
    try:
        supabase = get_supabase_client()
        
        # Get the review item
        result = supabase.table("human_review_queue").select("*").eq("id", review_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Review item not found")
        
        item = result.data[0]
        product_info = json.loads(item['product_info'])
        
        # Update review item status
        review_decision = {
            "action": "approved",
            "product_id": decision.product_id,
            "create_mapping": decision.create_mapping,
            "timestamp": datetime.now().isoformat()
        }
        
        supabase.table("human_review_queue").update({
            "status": "approved",
            "reviewed_by": "human_reviewer",  # TODO: Add actual user authentication
            "reviewed_at": datetime.now().isoformat(),
            "review_decision": json.dumps(review_decision)
        }).eq("id", review_id).execute()
        
        # Create product mapping if requested
        if decision.create_mapping:
            mapping_data = {
                "original_name": product_info.get('product_name', ''),
                "mapped_product_id": decision.product_id,
                "vendor_key": product_info.get('vendor', ''),
                "confidence": decision.confidence_override or 1.0,
                "mapping_source": "human",
                "created_by": "human_reviewer"
            }
            
            # Use upsert to handle duplicates
            supabase.table("product_mappings").upsert(mapping_data).execute()
        
        # Update the original invoice item with the approved product
        if item.get('invoice_item_id'):
            supabase.table("invoice_items").update({
                "matched_product_id": decision.product_id,
                "match_confidence": decision.confidence_override or 1.0,
                "match_status": "human_approved"
            }).eq("id", item['invoice_item_id']).execute()
        
        return {
            "status": "success",
            "message": "Match approved successfully",
            "review_id": review_id,
            "product_id": decision.product_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to approve match: {str(e)}")

@router.post("/reject/{review_id}")
async def reject_match(
    review_id: str,
    decision: RejectDecision
) -> Dict:
    """Reject a match and provide correct mapping"""
    try:
        supabase = get_supabase_client()
        
        # Get the review item
        result = supabase.table("human_review_queue").select("*").eq("id", review_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Review item not found")
        
        item = result.data[0]
        product_info = json.loads(item['product_info'])
        
        # Update review item status
        review_decision = {
            "action": "rejected",
            "reason": decision.reason,
            "correct_product_id": decision.correct_product_id,
            "timestamp": datetime.now().isoformat()
        }
        
        supabase.table("human_review_queue").update({
            "status": "rejected",
            "reviewed_by": "human_reviewer",
            "reviewed_at": datetime.now().isoformat(),
            "review_decision": json.dumps(review_decision)
        }).eq("id", review_id).execute()
        
        # Create correct mapping if provided
        if decision.correct_product_id and decision.create_mapping:
            mapping_data = {
                "original_name": product_info.get('product_name', ''),
                "mapped_product_id": decision.correct_product_id,
                "vendor_key": product_info.get('vendor', ''),
                "confidence": 1.0,
                "mapping_source": "human",
                "created_by": "human_reviewer"
            }
            
            supabase.table("product_mappings").upsert(mapping_data).execute()
            
            # Update invoice item with correct product
            if item.get('invoice_item_id'):
                supabase.table("invoice_items").update({
                    "matched_product_id": decision.correct_product_id,
                    "match_confidence": 1.0,
                    "match_status": "human_corrected"
                }).eq("id", item['invoice_item_id']).execute()
        
        return {
            "status": "success",
            "message": "Match rejected successfully",
            "review_id": review_id,
            "correct_product_id": decision.correct_product_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reject match: {str(e)}")

@router.post("/create-product/{review_id}")
async def create_new_product(
    review_id: str,
    product_data: NewProductData
) -> Dict:
    """Create new product when no match exists"""
    try:
        supabase = get_supabase_client()
        
        # Get the review item
        result = supabase.table("human_review_queue").select("*").eq("id", review_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Review item not found")
        
        item = result.data[0]
        product_info = json.loads(item['product_info'])
        
        # Create new product
        new_product = {
            "name": product_data.name,
            "brand": product_data.brand,
            "category": product_data.category,
            "unit_type": product_data.unit_type,
            "cost_per_unit": product_data.cost_per_unit,
            "created_at": datetime.now().isoformat(),
            "created_by": "human_reviewer"
        }
        
        product_result = supabase.table("products").insert(new_product).execute()
        
        if not product_result.data:
            raise HTTPException(status_code=500, detail="Failed to create new product")
        
        new_product_id = product_result.data[0]['id']
        
        # Create mapping for the new product
        mapping_data = {
            "original_name": product_info.get('product_name', ''),
            "mapped_product_id": new_product_id,
            "vendor_key": product_data.vendor_key,
            "confidence": 1.0,
            "mapping_source": "human",
            "created_by": "human_reviewer"
        }
        
        supabase.table("product_mappings").insert(mapping_data).execute()
        
        # Update review item
        review_decision = {
            "action": "created_new_product",
            "new_product_id": new_product_id,
            "timestamp": datetime.now().isoformat()
        }
        
        supabase.table("human_review_queue").update({
            "status": "approved",
            "reviewed_by": "human_reviewer",
            "reviewed_at": datetime.now().isoformat(),
            "review_decision": json.dumps(review_decision)
        }).eq("id", review_id).execute()
        
        # Update invoice item
        if item.get('invoice_item_id'):
            supabase.table("invoice_items").update({
                "matched_product_id": new_product_id,
                "match_confidence": 1.0,
                "match_status": "human_created"
            }).eq("id", item['invoice_item_id']).execute()
        
        return {
            "status": "success",
            "message": "New product created successfully",
            "review_id": review_id,
            "new_product_id": new_product_id,
            "product": new_product
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create new product: {str(e)}")

@router.get("/stats")
async def get_review_stats() -> Dict:
    """Get review queue statistics"""
    try:
        supabase = get_supabase_client()
        
        # Get counts by status
        pending_result = supabase.table("human_review_queue").select("id", count="exact").eq("status", "pending").execute()
        approved_result = supabase.table("human_review_queue").select("id", count="exact").eq("status", "approved").execute()
        rejected_result = supabase.table("human_review_queue").select("id", count="exact").eq("status", "rejected").execute()
        
        # Get priority breakdown
        high_priority = supabase.table("human_review_queue").select("id", count="exact").eq("status", "pending").eq("priority", 1).execute()
        medium_priority = supabase.table("human_review_queue").select("id", count="exact").eq("status", "pending").eq("priority", 2).execute()
        
        return {
            "queue_stats": {
                "pending": pending_result.count or 0,
                "approved": approved_result.count or 0,
                "rejected": rejected_result.count or 0,
                "high_priority": high_priority.count or 0,
                "medium_priority": medium_priority.count or 0
            },
            "total_mappings": supabase.table("product_mappings").select("id", count="exact").execute().count or 0
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch stats: {str(e)}")

@router.delete("/item/{review_id}")
async def skip_review_item(review_id: str) -> Dict:
    """Skip/remove an item from the review queue"""
    try:
        supabase = get_supabase_client()
        
        supabase.table("human_review_queue").update({
            "status": "skipped",
            "reviewed_by": "human_reviewer",
            "reviewed_at": datetime.now().isoformat()
        }).eq("id", review_id).execute()
        
        return {
            "status": "success",
            "message": "Item skipped successfully",
            "review_id": review_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to skip item: {str(e)}")
