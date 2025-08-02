#!/usr/bin/env python3
"""
Debug Data Flow from Claude to Price Updater
Track how cost_per_unit flows through the pipeline
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from components.invoice_processing.claude_processor import ClaudeInvoiceProcessor

async def debug_data_flow():
    """Debug the data flow from Claude to price updater"""
    
    print("🔍 Debugging Data Flow: Claude → Pipeline → Price Updater")
    print("=" * 70)
    
    # Step 1: Get Claude's raw output
    processor = ClaudeInvoiceProcessor()
    invoice_path = "uploads/test1.pdf"
    
    print(f"\n📄 Processing: {invoice_path}")
    
    # Extract data with Claude
    result = await processor.process_invoice(invoice_path)
    
    print(f"\n🤖 STEP 1: Claude Component 6 Output")
    print("-" * 50)
    
    for i, product in enumerate(result.products[:3], 1):  # Show first 3 products
        print(f"\nProduct {i}: {product.product_name}")
        print(f"  unit_price: {product.unit_price} (type: {type(product.unit_price)})")
        print(f"  units_per_pack: {product.units_per_pack} (type: {type(product.units_per_pack)})")
        print(f"  cost_per_unit: {product.cost_per_unit} (type: {type(product.cost_per_unit)})")
        
        # Manual calculation check
        if product.units_per_pack and product.unit_price:
            manual_calc = round(product.unit_price / product.units_per_pack, 2)
            print(f"  Manual calc: {product.unit_price} ÷ {product.units_per_pack} = {manual_calc}")
            print(f"  Matches Claude: {abs(product.cost_per_unit - manual_calc) < 0.01}")
    
    print(f"\n🔄 STEP 2: Convert to Pipeline Format")
    print("-" * 50)
    
    # Convert Claude products to pipeline format (simulate what pipeline does)
    pipeline_products = []
    for product in result.products:
        # Convert dataclass to dict (like pipeline does)
        product_dict = {
            'product_name': product.product_name,
            'line_number': product.line_number,
            'quantity': product.quantity,
            'unit_price': product.unit_price,
            'total': product.total,
            'units_per_pack': product.units_per_pack,
            'cost_per_unit': product.cost_per_unit,
            'raw_text': product.raw_text
        }
        pipeline_products.append(product_dict)
    
    for i, product in enumerate(pipeline_products[:3], 1):
        print(f"\nProduct {i}: {product['product_name']}")
        print(f"  unit_price: {product['unit_price']} (type: {type(product['unit_price'])})")
        print(f"  units_per_pack: {product['units_per_pack']} (type: {type(product['units_per_pack'])})")
        print(f"  cost_per_unit: {product['cost_per_unit']} (type: {type(product['cost_per_unit'])})")
    
    print(f"\n🎯 STEP 3: Simulate Product Matching")
    print("-" * 50)
    
    # Simulate what the pipeline orchestrator does
    matched_products = []
    for product in pipeline_products:
        # Simulate a successful match
        matched_product = {
            'original_name': product['product_name'],
            'matched': True,  # Assume matched for debugging
            'product_id': 'test-id-123',
            'product_name': product['product_name'],
            'confidence': 0.95,
            'strategy': 'test',
            'routing': 'auto',
            'unit_price': product.get('unit_price'),
            'units_per_pack': product.get('units_per_pack', 1),
            'cost_per_unit': product.get('cost_per_unit'),
            'currency': 'USD',
            'units': product.get('units', 1),
            'quantity': product.get('quantity', 1)
        }
        matched_products.append(matched_product)
    
    for i, product in enumerate(matched_products[:3], 1):
        print(f"\nMatched Product {i}: {product['product_name']}")
        print(f"  unit_price: {product['unit_price']} (type: {type(product['unit_price'])})")
        print(f"  units_per_pack: {product['units_per_pack']} (type: {type(product['units_per_pack'])})")
        print(f"  cost_per_unit: {product['cost_per_unit']} (type: {type(product['cost_per_unit'])})")
    
    print(f"\n💰 STEP 4: Simulate Price Updater Logic")
    print("-" * 50)
    
    for i, product in enumerate(matched_products[:3], 1):
        print(f"\nPrice Update for Product {i}: {product['product_name']}")
        
        # Simulate current price updater logic
        new_cost = product.get('cost_per_unit')
        
        print(f"  Price updater receives cost_per_unit: {new_cost} (type: {type(new_cost)})")
        
        if not new_cost:
            print("  ❌ cost_per_unit is None/empty - would use fallback calculation")
            unit_price = product.get('unit_price')
            units_per_pack = product.get('units_per_pack', 1)
            if unit_price and units_per_pack > 0:
                new_cost = round(unit_price / units_per_pack, 2)
                print(f"  Fallback calculation: {unit_price} ÷ {units_per_pack} = {new_cost}")
        else:
            print(f"  ✅ Using Claude's cost_per_unit: {new_cost}")
    
    print(f"\n🎯 CONCLUSION:")
    print("-" * 50)
    print("Check the output above to see where cost_per_unit gets lost or corrupted!")

if __name__ == "__main__":
    asyncio.run(debug_data_flow())
