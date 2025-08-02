#!/usr/bin/env python3
"""
Check Latest Invoice Data
Verify the most recent invoice items to see if our fixes are working
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
    
    print("🔍 Latest Invoice Data Check")
    print("=" * 50)
    
    # Get the most recent invoice
    recent_invoice = supabase.table('invoices').select(
        'id, invoice_number, created_at'
    ).order('created_at', desc=True).limit(1).execute()
    
    if recent_invoice.data:
        latest_invoice = recent_invoice.data[0]
        invoice_id = latest_invoice['id']
        invoice_number = latest_invoice['invoice_number']
        
        print(f"\n📋 Latest Invoice: {invoice_number}")
        print(f"Invoice ID: {invoice_id}")
        print(f"Created: {latest_invoice['created_at']}")
        
        # Get invoice items for this specific invoice
        items = supabase.table('invoice_items').select(
            'product_name, unit_price, cost_per_unit, units, quantity'
        ).eq('invoice_id', invoice_id).execute()
        
        if items.data:
            print(f"\n📦 Invoice Items ({len(items.data)} items):")
            print("-" * 80)
            print(f"{'Product Name':<30} | {'Unit Price':<10} | {'Units':<6} | {'Cost/Unit':<10} | {'Expected':<10} | {'Status'}")
            print("-" * 80)
            
            for item in items.data:
                name = item.get('product_name', 'Unknown')[:28]
                unit_price = item.get('unit_price', 0)
                cost_per_unit = item.get('cost_per_unit', 0)
                units = item.get('units', 1)
                
                # Calculate what cost per unit should be
                expected = round(unit_price / units, 2) if units > 0 else unit_price
                
                status = "✅ CORRECT" if abs(cost_per_unit - expected) < 0.01 else "❌ WRONG"
                
                print(f"{name:<30} | ${unit_price:>8.2f} | {units:>4} | ${cost_per_unit:>8.2f} | ${expected:>8.2f} | {status}")
        
        # Check price history for this invoice
        history = supabase.table('price_history').select(
            'product_id, old_cost, new_cost'
        ).eq('invoice_number', invoice_number).execute()
        
        if history.data:
            print(f"\n📈 Price History for {invoice_number} ({len(history.data)} entries):")
            print("-" * 50)
            for entry in history.data:
                old = entry.get('old_cost') or 0
                new = entry.get('new_cost') or 0
                product_id = entry.get('product_id', 'Unknown')[:20]
                
                print(f"Product {product_id}: ${old:.2f} → ${new:.2f}")
    
    else:
        print("❌ No invoices found in database")

if __name__ == "__main__":
    main()
