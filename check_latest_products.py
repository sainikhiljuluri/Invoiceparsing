#!/usr/bin/env python3
"""
Check Latest Updated Products
Show the most recently updated products in the products table
"""

import os
from supabase import create_client, Client
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

def main():
    # Initialize Supabase client
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    supabase: Client = create_client(url, key)
    
    print("🔍 Latest Updated Products in Products Table")
    print("=" * 80)
    
    # Get the most recently updated products (last 20)
    products = supabase.table('products').select(
        'id, name, cost, currency, last_invoice_number, last_update_date, brand, category'
    ).order('last_update_date', desc=True).limit(20).execute()
    
    if not products.data:
        print("No products found in the database.")
        return
    
    print(f"\n📦 Last 20 Updated Products (Most Recent First):")
    print("-" * 120)
    print(f"{'#':<3} | {'Product Name':<45} | {'Cost':<8} | {'Last Invoice':<15} | {'Updated':<19} | {'Brand':<12}")
    print("-" * 120)
    
    for i, product in enumerate(products.data, 1):
        name = product.get('name', 'Unknown')[:43]
        cost = product.get('cost', 0)
        cost_str = f"${cost:.2f}" if cost else "NULL"
        invoice = product.get('last_invoice_number') or 'None'
        invoice = invoice[:13] if invoice != 'None' else 'None'
        updated = product.get('last_update_date', '')
        brand = product.get('brand') or ''
        brand = brand[:10] if brand else ''
        
        # Format the date
        if updated:
            try:
                dt = datetime.fromisoformat(updated.replace('Z', '+00:00'))
                updated_str = dt.strftime('%Y-%m-%d %H:%M')
            except:
                updated_str = updated[:16]
        else:
            updated_str = "Never"
        
        print(f"{i:<3} | {name:<45} | {cost_str:<8} | {invoice:<15} | {updated_str:<19} | {brand:<12}")
    
    # Show products updated by the latest invoice specifically
    print(f"\n💰 Products Updated by Latest Invoice (INV-2025-0087):")
    print("-" * 80)
    
    latest_products = supabase.table('products').select(
        'name, cost, last_update_date'
    ).eq('last_invoice_number', 'INV-2025-0087').order('last_update_date', desc=True).execute()
    
    if latest_products.data:
        print(f"Total products updated by INV-2025-0087: {len(latest_products.data)}")
        print("-" * 60)
        print(f"{'Product Name':<45} | {'Cost':<8} | {'Updated'}")
        print("-" * 60)
        
        for product in latest_products.data[:10]:  # Show first 10
            name = product.get('name', 'Unknown')[:43]
            cost = product.get('cost', 0)
            cost_str = f"${cost:.2f}" if cost else "NULL"
            updated = product.get('last_update_date', '')
            
            if updated:
                try:
                    dt = datetime.fromisoformat(updated.replace('Z', '+00:00'))
                    updated_str = dt.strftime('%Y-%m-%d %H:%M')
                except:
                    updated_str = updated[:16]
            else:
                updated_str = "Never"
            
            print(f"{name:<45} | {cost_str:<8} | {updated_str}")
        
        if len(latest_products.data) > 10:
            print(f"... and {len(latest_products.data) - 10} more products")
    else:
        print("No products found for INV-2025-0087")

if __name__ == "__main__":
    main()
