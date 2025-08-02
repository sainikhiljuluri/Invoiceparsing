#!/usr/bin/env python3
"""
Check Product Matching Results
Verify which products in the database got matched to our invoice items
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
    
    print("🔍 Product Matching Verification")
    print("=" * 60)
    
    # Get the latest invoice items to see what got matched
    invoice_items = supabase.table('invoice_items').select(
        'product_name, product_id, match_strategy, match_confidence, cost_per_unit'
    ).eq('invoice_id', 'fc468c2a-7271-4836-ac9a-7bf5f505a73c').execute()
    
    print(f"\n📦 Invoice Items and Their Matches:")
    print("-" * 100)
    print(f"{'Invoice Product':<35} | {'Matched To':<35} | {'Strategy':<15} | {'Confidence':<10} | {'Cost'}")
    print("-" * 100)
    
    for item in invoice_items.data:
        invoice_name = item.get('product_name', 'Unknown')[:33]
        product_id = item.get('product_id')
        strategy = item.get('match_strategy', 'None')[:13]
        confidence = item.get('match_confidence', 0)
        cost = item.get('cost_per_unit', 0)
        
        # Get the actual product name from products table
        if product_id:
            product = supabase.table('products').select('name, cost').eq('id', product_id).execute()
            if product.data:
                matched_name = product.data[0].get('name', 'Unknown')[:33]
                db_cost = product.data[0].get('cost', 0)
            else:
                matched_name = "NOT FOUND"
                db_cost = 0
        else:
            matched_name = "NO MATCH"
            db_cost = 0
        
        print(f"{invoice_name:<35} | {matched_name:<35} | {strategy:<15} | {confidence:<10.2f} | ${cost:.2f}")
        if product_id and db_cost != cost:
            print(f"  ⚠️  Database cost: ${db_cost:.2f} (expected: ${cost:.2f})")
        print()
    
    # Show the products that got updated with their costs
    print(f"\n💰 Products That Got Cost Updates:")
    print("-" * 80)
    print(f"{'Product Name':<50} | {'New Cost':<10} | {'Last Invoice'}")
    print("-" * 80)
    
    # Get products updated by this invoice
    products = supabase.table('products').select(
        'name, cost, last_invoice_number'
    ).eq('last_invoice_number', 'INV-2025-0087').execute()
    
    for product in products.data:
        name = product.get('name', 'Unknown')[:48]
        cost = product.get('cost', 0)
        invoice = product.get('last_invoice_number', 'None')
        
        print(f"{name:<50} | ${cost:<9.2f} | {invoice}")

if __name__ == "__main__":
    main()
