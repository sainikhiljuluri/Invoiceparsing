#!/usr/bin/env python3
"""
Verify Cost Per Unit Calculations
Check that the system is correctly calculating and storing cost per unit values
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from database.database_connection import DatabaseConnection

async def verify_cost_calculations():
    """Verify that cost per unit calculations are correct"""
    
    # Initialize database connection
    db = DatabaseConnection()
    
    print("🔍 Verifying Cost Per Unit Calculations")
    print("=" * 60)
    
    # Get recent invoice items with cost calculations
    invoice_items = db.supabase.table('invoice_items').select(
        'product_name, unit_price, cost_per_unit, units, quantity'
    ).order('created_at', desc=True).limit(10).execute()
    
    if invoice_items.data:
        print("\n📋 Recent Invoice Items:")
        print("-" * 60)
        for item in invoice_items.data:
            product_name = item.get('product_name', 'Unknown')
            unit_price = item.get('unit_price', 0)
            cost_per_unit = item.get('cost_per_unit', 0)
            units = item.get('units', 1)
            
            # Calculate expected cost per unit
            expected_cost_per_unit = round(unit_price / units, 2) if units > 0 else unit_price
            
            print(f"Product: {product_name}")
            print(f"  Unit Price: ${unit_price:.2f}")
            print(f"  Units: {units}")
            print(f"  Stored Cost/Unit: ${cost_per_unit:.2f}")
            print(f"  Expected Cost/Unit: ${expected_cost_per_unit:.2f}")
            
            if abs(cost_per_unit - expected_cost_per_unit) < 0.01:
                print(f"  ✅ Calculation: CORRECT")
            else:
                print(f"  ❌ Calculation: INCORRECT")
            print()
    
    # Get recent price history entries
    price_history = db.supabase.table('price_history').select(
        'product_id, old_cost, new_cost, invoice_number, created_at'
    ).order('created_at', desc=True).limit(5).execute()
    
    if price_history.data:
        print("\n📈 Recent Price History:")
        print("-" * 60)
        for entry in price_history.data:
            print(f"Product ID: {entry.get('product_id', 'Unknown')}")
            print(f"  Old Cost: ${entry.get('old_cost', 0):.2f}")
            print(f"  New Cost: ${entry.get('new_cost', 0):.2f}")
            print(f"  Invoice: {entry.get('invoice_number', 'Unknown')}")
            print(f"  Date: {entry.get('created_at', 'Unknown')}")
            print()
    
    # Get current product costs
    products = db.supabase.table('products').select(
        'id, name, cost, last_invoice_number'
    ).not_.is_('cost', 'null').order('last_update_date', desc=True).limit(5).execute()
    
    if products.data:
        print("\n💰 Current Product Costs:")
        print("-" * 60)
        for product in products.data:
            print(f"Product: {product.get('name', 'Unknown')}")
            print(f"  Current Cost: ${product.get('cost', 0):.2f}")
            print(f"  Last Invoice: {product.get('last_invoice_number', 'Unknown')}")
            print()
    
    print("✅ Cost verification completed!")

if __name__ == "__main__":
    asyncio.run(verify_cost_calculations())
