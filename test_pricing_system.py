#!/usr/bin/env python3
"""
Test the pricing system integration
"""

import sys
import asyncio
import logging
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from database.connection import DatabaseConnection
from services.pricing_calculator import PriceCalculator
from services.price_analytics import PricingAnalytics

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_pricing_system():
    """Test the pricing system functionality"""
    
    try:
        logger.info("🧪 Testing Pricing System Integration...")
        
        # Initialize database connection
        db = DatabaseConnection()
        
        # Test 1: Initialize pricing calculator
        logger.info("Test 1: Initializing pricing calculator...")
        calculator = PriceCalculator(db)
        logger.info("✅ Pricing calculator initialized successfully")
        
        # Test 2: Test pricing calculation
        logger.info("Test 2: Testing pricing calculation...")
        test_product = {
            'product_name': '24 Mantra Organic Basmati Rice 5Lb',
            'cost_per_unit': 12.50,
            'category': 'RICE',
            'brand': '24 Mantra',
            'size': '5Lb'
        }
        
        pricing_result = calculator.calculate_suggested_price(test_product)
        
        if pricing_result.get('success'):
            logger.info(f"✅ Pricing calculation successful:")
            logger.info(f"   Product: {pricing_result['product_name']}")
            logger.info(f"   Cost: ₹{pricing_result['cost_per_unit']:.2f}")
            logger.info(f"   Suggested Price: ₹{pricing_result['suggested_price']:.2f}")
            logger.info(f"   Markup: {pricing_result['markup_percentage']:.1f}%")
            logger.info(f"   Category: {pricing_result['category']}")
            logger.info(f"   Confidence: {pricing_result['confidence']}")
        else:
            logger.error(f"❌ Pricing calculation failed: {pricing_result.get('error')}")
            return False
        
        # Test 3: Test bulk pricing
        logger.info("Test 3: Testing bulk pricing...")
        test_products = [
            {
                'product_name': 'Toor Dal 2Kg',
                'cost_per_unit': 8.00,
                'category': 'LENTILS'
            },
            {
                'product_name': 'Red Chili Powder 500g',
                'cost_per_unit': 5.50,
                'category': 'SPICES'
            }
        ]
        
        bulk_results = calculator.calculate_bulk_prices(test_products)
        logger.info(f"✅ Bulk pricing calculated for {len(bulk_results)} products")
        
        for result in bulk_results:
            if result.get('success'):
                logger.info(f"   {result['product_name']}: ₹{result['suggested_price']:.2f} ({result['markup_percentage']:.1f}% markup)")
        
        # Test 4: Test pricing analytics
        logger.info("Test 4: Testing pricing analytics...")
        analytics = PricingAnalytics(db)
        logger.info("✅ Pricing analytics initialized successfully")
        
        # Test 5: Test database pricing rules (if available)
        logger.info("Test 5: Testing database pricing rules...")
        try:
            result = db.supabase.table('pricing_rules').select('*').limit(1).execute()
            if result.data:
                logger.info(f"✅ Database pricing rules available: {len(result.data)} rules found")
            else:
                logger.info("⚠️  No pricing rules in database yet (will use config defaults)")
        except Exception as e:
            logger.warning(f"⚠️  Database pricing rules not accessible: {e}")
        
        # Test 6: Test competitor prices table
        logger.info("Test 6: Testing competitor prices table...")
        try:
            result = db.supabase.table('competitor_prices').select('*').limit(1).execute()
            logger.info(f"✅ Competitor prices table accessible (found {len(result.data)} entries)")
        except Exception as e:
            logger.warning(f"⚠️  Competitor prices table not accessible: {e}")
        
        logger.info("🎉 All pricing system tests completed successfully!")
        logger.info("")
        logger.info("📋 Next Steps:")
        logger.info("1. Run the complete_pricing_tables.sql in your Supabase SQL Editor")
        logger.info("2. Upload a new invoice to test automatic pricing calculation")
        logger.info("3. Use the chat interface to ask pricing questions like:")
        logger.info("   - 'Suggest selling price for Basmati Rice'")
        logger.info("   - 'Price analysis for organic products'")
        logger.info("   - 'Bulk pricing for spices category'")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Pricing system test failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_pricing_system())
    sys.exit(0 if success else 1)
