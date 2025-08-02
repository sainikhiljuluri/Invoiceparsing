"""
Pricing API Routes - Suggested Selling Price Feature
Provides endpoints for pricing recommendations and analysis
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional, Dict
from pydantic import BaseModel
import logging

from services.pricing_calculator import PriceCalculator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/pricing", tags=["pricing"])

# Pydantic models for API responses
class PricingRecommendationResponse(BaseModel):
    product_id: str
    product_name: str
    cost_price: float
    suggested_price: float
    min_price: float
    max_price: float
    markup_percentage: float
    confidence_score: float
    reasoning: List[str]
    last_updated: str

class BulkPricingRequest(BaseModel):
    products: List[Dict]

class PricingAnalysisResponse(BaseModel):
    total_products: int
    avg_markup: float
    high_margin_products: List[str]
    low_margin_products: List[str]
    recommendations: List[PricingRecommendationResponse]

# Dependency to get pricing calculator
def get_pricing_calculator():
    from api.main import db  # Import from main app
    return PriceCalculator(db)

@router.post("/calculate", response_model=PricingRecommendationResponse)
async def calculate_product_price(
    product_data: Dict,
    calculator: PriceCalculator = Depends(get_pricing_calculator)
):
    """
    Calculate suggested selling price for a single product
    
    Example request:
    {
        "product_name": "24 Mantra Organic Basmati Rice 5Lb",
        "cost_per_unit": 12.50,
        "category": "RICE",
        "units": 4
    }
    """
    try:
        recommendation = calculator.calculate_suggested_price(product_data)
        
        return PricingRecommendationResponse(
            product_id=recommendation.product_id,
            product_name=recommendation.product_name,
            cost_price=recommendation.cost_price,
            suggested_price=recommendation.suggested_price,
            min_price=recommendation.min_price,
            max_price=recommendation.max_price,
            markup_percentage=recommendation.markup_percentage,
            confidence_score=recommendation.confidence_score,
            reasoning=recommendation.reasoning,
            last_updated=recommendation.last_updated.isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error calculating price: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/calculate-bulk", response_model=List[PricingRecommendationResponse])
async def calculate_bulk_prices(
    request: BulkPricingRequest,
    calculator: PriceCalculator = Depends(get_pricing_calculator)
):
    """Calculate suggested prices for multiple products"""
    try:
        recommendations = calculator.bulk_calculate_prices(request.products)
        
        return [
            PricingRecommendationResponse(
                product_id=rec.product_id,
                product_name=rec.product_name,
                cost_price=rec.cost_price,
                suggested_price=rec.suggested_price,
                min_price=rec.min_price,
                max_price=rec.max_price,
                markup_percentage=rec.markup_percentage,
                confidence_score=rec.confidence_score,
                reasoning=rec.reasoning,
                last_updated=rec.last_updated.isoformat()
            )
            for rec in recommendations
        ]
        
    except Exception as e:
        logger.error(f"Error calculating bulk prices: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/update-from-invoice/{invoice_id}")
async def update_pricing_from_invoice(
    invoice_id: str,
    calculator: PriceCalculator = Depends(get_pricing_calculator)
):
    """
    Update pricing recommendations based on new invoice data
    This automatically calculates suggested prices for all products in an invoice
    """
    try:
        recommendations = calculator.update_pricing_from_invoice(invoice_id)
        
        return {
            "message": f"Updated pricing for {len(recommendations)} products",
            "invoice_id": invoice_id,
            "recommendations_count": len(recommendations),
            "recommendations": [
                {
                    "product_name": rec.product_name,
                    "cost_price": rec.cost_price,
                    "suggested_price": rec.suggested_price,
                    "markup_percentage": rec.markup_percentage
                }
                for rec in recommendations
            ]
        }
        
    except Exception as e:
        logger.error(f"Error updating pricing from invoice {invoice_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/recommendations", response_model=List[PricingRecommendationResponse])
async def get_pricing_recommendations(
    limit: int = Query(50, le=100),
    category: Optional[str] = None,
    min_confidence: Optional[float] = Query(None, ge=0, le=1),
    calculator: PriceCalculator = Depends(get_pricing_calculator)
):
    """Get stored pricing recommendations with optional filters"""
    try:
        # Build query
        query = calculator.db.supabase.table('pricing_recommendations').select('*')
        
        if category:
            # This would require joining with products table or storing category in recommendations
            pass
        
        if min_confidence:
            query = query.gte('confidence_score', min_confidence)
        
        query = query.eq('is_active', True).order('created_at', desc=True).limit(limit)
        
        result = query.execute()
        
        recommendations = []
        for item in result.data:
            recommendations.append(PricingRecommendationResponse(
                product_id=item['product_id'] or '',
                product_name=item['product_name'],
                cost_price=item['cost_price'],
                suggested_price=item['suggested_price'],
                min_price=item['min_price'],
                max_price=item['max_price'],
                markup_percentage=item['markup_percentage'],
                confidence_score=item['confidence_score'],
                reasoning=item['reasoning'] or [],
                last_updated=item['created_at']
            ))
        
        return recommendations
        
    except Exception as e:
        logger.error(f"Error getting pricing recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analysis", response_model=PricingAnalysisResponse)
async def get_pricing_analysis(
    calculator: PriceCalculator = Depends(get_pricing_calculator)
):
    """Get pricing analysis and insights"""
    try:
        # Get recent pricing recommendations
        result = calculator.db.supabase.table('pricing_recommendations').select('*').eq(
            'is_active', True
        ).order('created_at', desc=True).limit(100).execute()
        
        recommendations = result.data
        
        if not recommendations:
            return PricingAnalysisResponse(
                total_products=0,
                avg_markup=0,
                high_margin_products=[],
                low_margin_products=[],
                recommendations=[]
            )
        
        # Calculate analytics
        markups = [rec['markup_percentage'] for rec in recommendations]
        avg_markup = sum(markups) / len(markups)
        
        # High margin products (>60% markup)
        high_margin = [rec['product_name'] for rec in recommendations if rec['markup_percentage'] > 60]
        
        # Low margin products (<30% markup)
        low_margin = [rec['product_name'] for rec in recommendations if rec['markup_percentage'] < 30]
        
        # Convert to response format
        rec_responses = [
            PricingRecommendationResponse(
                product_id=rec['product_id'] or '',
                product_name=rec['product_name'],
                cost_price=rec['cost_price'],
                suggested_price=rec['suggested_price'],
                min_price=rec['min_price'],
                max_price=rec['max_price'],
                markup_percentage=rec['markup_percentage'],
                confidence_score=rec['confidence_score'],
                reasoning=rec['reasoning'] or [],
                last_updated=rec['created_at']
            )
            for rec in recommendations[:20]  # Limit to top 20
        ]
        
        return PricingAnalysisResponse(
            total_products=len(recommendations),
            avg_markup=round(avg_markup, 2),
            high_margin_products=high_margin[:10],
            low_margin_products=low_margin[:10],
            recommendations=rec_responses
        )
        
    except Exception as e:
        logger.error(f"Error getting pricing analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/{product_id}")
async def get_pricing_history(
    product_id: str,
    calculator: PriceCalculator = Depends(get_pricing_calculator)
):
    """Get pricing history for a specific product"""
    try:
        history = calculator.get_pricing_history(product_id)
        
        return {
            "product_id": product_id,
            "history_count": len(history),
            "pricing_history": history
        }
        
    except Exception as e:
        logger.error(f"Error getting pricing history for {product_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/rules")
async def get_pricing_rules():
    """Get current pricing rules and markup configurations"""
    from config.pricing_rules import PricingRules
    
    return {
        "category_markups": PricingRules.CATEGORY_MARKUPS,
        "brand_premiums": PricingRules.BRAND_PREMIUMS,
        "size_adjustments": PricingRules.SIZE_ADJUSTMENTS,
        "special_conditions": PricingRules.SPECIAL_CONDITIONS,
        "competitive_rules": PricingRules.get_competitive_pricing_rules()
    }
