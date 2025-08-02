"""
Additional pricing API endpoints for enhanced functionality
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Optional
from pydantic import BaseModel
import logging

from services.pricing_calculator import PriceCalculator
from services.price_analytics import PricingAnalytics
from database.connection import DatabaseConnection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/pricing", tags=["pricing"])

# Pydantic models
class ProductInfo(BaseModel):
    product_name: str
    cost_per_unit: float
    category: Optional[str] = None
    brand: Optional[str] = None
    size: Optional[str] = None
    units: Optional[int] = 1

class BulkProductsRequest(BaseModel):
    products: List[ProductInfo]

class PriceUpdateRequest(BaseModel):
    product_id: str
    selling_price: float
    reason: Optional[str] = None

# Dependency to get database connection
def get_db():
    return DatabaseConnection()

@router.post("/suggest")
async def suggest_price(product_info: ProductInfo, db: DatabaseConnection = Depends(get_db)):
    """Get suggested selling price for a product"""
    try:
        calculator = PriceCalculator(db)
        result = calculator.calculate_suggested_price(product_info.dict())
        
        if not result.get('success'):
            raise HTTPException(status_code=400, detail=result.get('error', 'Pricing calculation failed'))
        
        return {
            "success": True,
            "product_name": result['product_name'],
            "cost_per_unit": result['cost_per_unit'],
            "suggested_price": result['suggested_price'],
            "min_price": result['min_price'],
            "max_price": result['max_price'],
            "markup_percentage": result['markup_percentage'],
            "category": result['category'],
            "confidence": result['confidence'],
            "pricing_strategy": result['pricing_strategy'],
            "adjustments": result.get('adjustments', []),
            "market_position": result['competitor_analysis']['market_position']
        }
        
    except Exception as e:
        logger.error(f"Error in suggest_price: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/bulk-suggest")
async def bulk_suggest_prices(request: BulkProductsRequest, db: DatabaseConnection = Depends(get_db)):
    """Get suggested prices for multiple products"""
    try:
        calculator = PriceCalculator(db)
        products_data = [product.dict() for product in request.products]
        results = calculator.calculate_bulk_prices(products_data)
        
        return {
            "success": True,
            "total_products": len(results),
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error in bulk_suggest_prices: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics/{product_id}")
async def get_pricing_analytics(product_id: str, days: int = 30, db: DatabaseConnection = Depends(get_db)):
    """Get pricing analytics for a product"""
    try:
        analytics = PricingAnalytics(db)
        analysis = analytics.analyze_pricing_performance(product_id, days)
        
        if 'error' in analysis:
            raise HTTPException(status_code=404, detail=analysis['error'])
        
        return {
            "success": True,
            "product_id": product_id,
            "analysis_period_days": days,
            "analytics": analysis
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_pricing_analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/update-selling-price")
async def update_selling_price(request: PriceUpdateRequest, db: DatabaseConnection = Depends(get_db)):
    """Update selling price for a product"""
    try:
        # Get current product info
        product_result = db.supabase.table('products').select(
            'id, name, cost, category'
        ).eq('id', request.product_id).execute()
        
        if not product_result.data:
            raise HTTPException(status_code=404, detail="Product not found")
        
        product = product_result.data[0]
        current_cost = product.get('cost', 0)
        
        # Update selling price in products table
        update_result = db.supabase.table('products').update({
            'selling_price': request.selling_price,
            'last_price_update': 'now()'
        }).eq('id', request.product_id).execute()
        
        # Calculate markup percentage
        markup_percentage = 0
        if current_cost > 0:
            markup_percentage = ((request.selling_price / current_cost) - 1) * 100
        
        # Log the price change in product_pricing table
        pricing_log = {
            'product_id': request.product_id,
            'cost_price': current_cost,
            'suggested_price': request.selling_price,
            'min_price': current_cost * 1.25,  # 25% minimum markup
            'max_price': current_cost * 1.60,  # 60% maximum markup
            'markup_percentage': markup_percentage,
            'adjustments': {
                'reason': request.reason or 'Manual price update',
                'updated_by': 'manual',
                'previous_price': product.get('selling_price')
            }
        }
        
        db.supabase.table('product_pricing').insert(pricing_log).execute()
        
        return {
            "success": True,
            "status": "updated",
            "product_id": request.product_id,
            "product_name": product['name'],
            "new_price": request.selling_price,
            "markup_percentage": round(markup_percentage, 2),
            "reason": request.reason
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating selling price: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/market-comparison/{product_name}")
async def get_market_comparison(product_name: str, db: DatabaseConnection = Depends(get_db)):
    """Get market price comparison for a product"""
    try:
        # Get competitor prices
        competitor_result = db.supabase.table('competitor_prices').select(
            'competitor_name, competitor_price, currency, last_updated'
        ).ilike('product_name', f'%{product_name}%').eq('active', True).execute()
        
        # Get our current price
        our_price_result = db.supabase.table('products').select(
            'selling_price, cost'
        ).ilike('name', f'%{product_name}%').execute()
        
        our_price = None
        our_cost = None
        if our_price_result.data:
            our_price = our_price_result.data[0].get('selling_price')
            our_cost = our_price_result.data[0].get('cost')
        
        competitor_prices = competitor_result.data
        
        # Calculate market position
        market_analysis = {}
        if competitor_prices and our_price:
            competitor_price_values = [cp['competitor_price'] for cp in competitor_prices]
            avg_competitor_price = sum(competitor_price_values) / len(competitor_price_values)
            min_competitor_price = min(competitor_price_values)
            max_competitor_price = max(competitor_price_values)
            
            market_analysis = {
                'our_price': our_price,
                'our_cost': our_cost,
                'our_margin': ((our_price / our_cost) - 1) * 100 if our_cost else None,
                'avg_competitor_price': avg_competitor_price,
                'min_competitor_price': min_competitor_price,
                'max_competitor_price': max_competitor_price,
                'price_position': 'competitive' if abs(our_price - avg_competitor_price) / avg_competitor_price < 0.1 else 
                               'premium' if our_price > avg_competitor_price else 'value',
                'price_difference_from_avg': our_price - avg_competitor_price,
                'price_difference_percentage': ((our_price / avg_competitor_price) - 1) * 100
            }
        
        return {
            "success": True,
            "product_name": product_name,
            "competitor_prices": competitor_prices,
            "market_analysis": market_analysis,
            "total_competitors": len(competitor_prices)
        }
        
    except Exception as e:
        logger.error(f"Error in market comparison: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/category-performance/{category}")
async def get_category_performance(category: str, db: DatabaseConnection = Depends(get_db)):
    """Get pricing performance for a product category"""
    try:
        # Get products in category with pricing data
        products_result = db.supabase.table('products').select(
            'id, name, cost, selling_price'
        ).eq('category', category).execute()
        
        if not products_result.data:
            raise HTTPException(status_code=404, detail=f"No products found in category: {category}")
        
        products = products_result.data
        
        # Calculate category metrics
        total_products = len(products)
        products_with_prices = [p for p in products if p.get('selling_price') and p.get('cost')]
        
        if products_with_prices:
            margins = [((p['selling_price'] / p['cost']) - 1) * 100 for p in products_with_prices]
            avg_margin = sum(margins) / len(margins)
            min_margin = min(margins)
            max_margin = max(margins)
            
            # Get pricing rules for category
            rules_result = db.supabase.table('pricing_rules').select(
                'min_markup, target_markup, max_markup'
            ).eq('category', category).execute()
            
            target_markup = None
            if rules_result.data:
                target_markup = rules_result.data[0]['target_markup']
        else:
            avg_margin = min_margin = max_margin = 0
            target_markup = None
        
        return {
            "success": True,
            "category": category,
            "total_products": total_products,
            "products_with_pricing": len(products_with_prices),
            "average_margin": round(avg_margin, 2) if products_with_prices else 0,
            "min_margin": round(min_margin, 2) if products_with_prices else 0,
            "max_margin": round(max_margin, 2) if products_with_prices else 0,
            "target_markup": target_markup,
            "performance_vs_target": round(avg_margin - target_markup, 2) if target_markup and products_with_prices else None,
            "products": products_with_prices[:10]  # Return top 10 products
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in category performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))
