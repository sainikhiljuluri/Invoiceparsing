#!/usr/bin/env python3
"""
Check Products Table
Verify if cost per unit values are being stored in the products table
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
    
    print("🔍 Products Table Cost Check")
    print("=" * 50)
    
    # Get products that should have been updated by the latest invoice
    product_names = [
        "Haldiram's Drumsticks",
        "Anand Special Palak Muruku", 
        "Anand Gooseberry Amla",
        "Deccan Brown Sona Masoori",
        "Vadilal Mixed Vegetables",
        "Vadilal Jumbo Punjabi Samosa"
    ]
    
    print(f"\n📦 Products Table Cost Values:")
    print("-" * 80)
    print(f"{'Product Name':<35} | {'Current Cost':<12} | {'Expected Cost':<12} | {'Status'}")
    print("-" * 80)
    
    # Expected cost per unit values from our test
    expected_costs = {
        "Haldiram's Drumsticks": 2.67,
        "Anand Special Palak Muruku": 0.75,
        "Anand Gooseberry Amla": 2.00,
        "Deccan Brown Sona Masoori": 13.50,
        "Vadilal Mixed Vegetables": 1.70,
        "Vadilal Jumbo Punjabi Samosa": 6.40
    }
    
    for product_key in product_names:
        # Search for products with similar names
        products = supabase.table('products').select(
            'id, name, cost, last_invoice_number, last_update_date'
        ).ilike('name', f'%{product_key.split()[0]}%').execute()
        
        if products.data:
            for product in products.data:
                name = product.get('name', 'Unknown')[:33]
                cost = product.get('cost')
                invoice = product.get('last_invoice_number', 'None')
                
                # Find expected cost for this product
                expected = None
                for key, exp_cost in expected_costs.items():
                    if key.split()[0].lower() in name.lower():
                        expected = exp_cost
                        break
                
                if cost is not None:
                    cost_str = f"${cost:.2f}"
                    if expected:
                        expected_str = f"${expected:.2f}"
                        status = "✅ CORRECT" if abs(cost - expected) < 0.01 else "❌ WRONG"
                    else:
                        expected_str = "Unknown"
                        status = "? UNKNOWN"
                else:
                    cost_str = "NULL"
                    expected_str = f"${expected:.2f}" if expected else "Unknown"
                    status = "❌ NULL"
                
                print(f"{name:<35} | {cost_str:<12} | {expected_str:<12} | {status}")
                
                if invoice:
                    print(f"  Last Invoice: {invoice}")
                if product.get('last_update_date'):
                    print(f"  Last Updated: {product.get('last_update_date')}")
                print()
        else:
            print(f"{product_key:<35} | NOT FOUND   | Unknown      | ❌ MISSING")
    
    # Check recent price history to see if updates are happening
    print(f"\n📈 Recent Price History (last 10 entries):")
    print("-" * 60)
    
    history = supabase.table('price_history').select(
        'product_id, old_cost, new_cost, invoice_number, created_at'
    ).order('created_at', desc=True).limit(10).execute()
    
    if history.data:
        for entry in history.data:
            product_id = entry.get('product_id', 'Unknown')[:20]
            old_cost = entry.get('old_cost') or 0
            new_cost = entry.get('new_cost') or 0
            invoice = entry.get('invoice_number', 'Unknown')
            created = entry.get('created_at', '')[:19]
            
            print(f"{created} | {invoice} | Product {product_id} | ${old_cost:.2f} → ${new_cost:.2f}")
    else:
        print("No price history found")

if __name__ == "__main__":
    main()
