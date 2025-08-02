#!/usr/bin/env python3
"""
Simple Cost Verification Script
Check the latest cost calculations in the database
"""

import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

def main():
    # Initialize Supabase client
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    supabase: Client = create_client(url, key)
    
    print("🔍 Cost Per Unit Verification")
    print("=" * 50)
    
    # Check recent invoice items
    print("\n📋 Recent Invoice Items (showing cost calculations):")
    print("-" * 50)
    
    items = supabase.table('invoice_items').select(
        'product_name, unit_price, cost_per_unit, units, quantity'
    ).order('created_at', desc=True).limit(8).execute()
    
    if items.data:
        for item in items.data:
            name = item.get('product_name', 'Unknown')[:30]
            unit_price = item.get('unit_price', 0)
            cost_per_unit = item.get('cost_per_unit', 0)
            units = item.get('units', 1)
            
            # Calculate what cost per unit should be
            expected = round(unit_price / units, 2) if units > 0 else unit_price
            
            status = "✅" if abs(cost_per_unit - expected) < 0.01 else "❌"
            
            print(f"{name:<30} | Unit: ${unit_price:>6.2f} | Units: {units:>2} | Cost/Unit: ${cost_per_unit:>6.2f} | Expected: ${expected:>6.2f} {status}")
    
    # Check recent price history
    print("\n📈 Recent Price History:")
    print("-" * 50)
    
    history = supabase.table('price_history').select(
        'old_cost, new_cost, invoice_number'
    ).order('created_at', desc=True).limit(5).execute()
    
    if history.data:
        for entry in history.data:
            old = entry.get('old_cost') or 0
            new = entry.get('new_cost') or 0
            invoice = entry.get('invoice_number', 'Unknown')[:15]
            
            print(f"Invoice {invoice:<15} | Old: ${old:>6.2f} → New: ${new:>6.2f}")
    
    # Check current product costs
    print("\n💰 Current Product Costs:")
    print("-" * 50)
    
    products = supabase.table('products').select(
        'name, cost, last_invoice_number'
    ).not_.is_('cost', 'null').order('last_update_date', desc=True).limit(5).execute()
    
    if products.data:
        for product in products.data:
            name = product.get('name', 'Unknown')[:30]
            cost = product.get('cost', 0)
            invoice = product.get('last_invoice_number', 'Unknown')[:15]
            
            print(f"{name:<30} | Cost: ${cost:>6.2f} | Last Invoice: {invoice}")
    
    print("\n✅ Verification completed!")

if __name__ == "__main__":
    main()
