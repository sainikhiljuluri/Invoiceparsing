#!/usr/bin/env python3
"""
Check Test1.pdf Invoice Data
Examine specifically the test1.pdf invoice to verify our field mapping fixes
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
    
    print("🔍 Test1.pdf Invoice Data Check")
    print("=" * 50)
    
    # Get the most recent INV-2025-0087 invoice (from test1.pdf)
    invoice = supabase.table('invoices').select(
        'id, invoice_number, created_at'
    ).eq('invoice_number', 'INV-2025-0087').order('created_at', desc=True).limit(1).execute()
    
    if invoice.data:
        latest_invoice = invoice.data[0]
        invoice_id = latest_invoice['id']
        invoice_number = latest_invoice['invoice_number']
        
        print(f"\n📋 Invoice: {invoice_number}")
        print(f"Invoice ID: {invoice_id}")
        print(f"Created: {latest_invoice['created_at']}")
        
        # Get invoice items for this specific invoice
        items = supabase.table('invoice_items').select(
            'product_name, unit_price, cost_per_unit, units, quantity'
        ).eq('invoice_id', invoice_id).order('line_number').execute()
        
        if items.data:
            print(f"\n📦 Invoice Items ({len(items.data)} items):")
            print("-" * 90)
            print(f"{'#':<2} | {'Product Name':<30} | {'Unit Price':<10} | {'Units':<6} | {'Cost/Unit':<10} | {'Expected':<10} | {'Status'}")
            print("-" * 90)
            
            # Expected values from Claude Component 6
            expected_data = [
                {"name": "Haldiram's Drumsticks 908 Gm", "unit_price": 32.00, "units_per_pack": 12, "cost_per_unit": 2.67},
                {"name": "Anand Special Palak Muruku 170GM", "unit_price": 18.00, "units_per_pack": 24, "cost_per_unit": 0.75},
                {"name": "Anand Gooseberry Amla 1 Lb", "unit_price": 20.00, "units_per_pack": 10, "cost_per_unit": 2.0},
                {"name": "Deccan Brown Sona Masoori Rice 20 Lb", "unit_price": 27.00, "units_per_pack": 2, "cost_per_unit": 13.5},
                {"name": "Vadilal Mixed Vegetables 908 Gm", "unit_price": 17.00, "units_per_pack": 10, "cost_per_unit": 1.7},
                {"name": "Vadilal Jumbo Punjabi Samosa 1.5 Kg", "unit_price": 32.00, "units_per_pack": 5, "cost_per_unit": 6.4}
            ]
            
            for i, item in enumerate(items.data[:6], 1):  # Show first 6 items
                name = item.get('product_name', 'Unknown')[:28]
                unit_price = item.get('unit_price', 0)
                cost_per_unit = item.get('cost_per_unit', 0)
                units = item.get('units', 1)
                
                # Get expected values for this product
                expected = next((exp for exp in expected_data if exp["name"][:20] in name), None)
                if expected:
                    expected_units = expected["units_per_pack"]
                    expected_cost = expected["cost_per_unit"]
                else:
                    expected_units = units
                    expected_cost = round(unit_price / units, 2) if units > 0 else unit_price
                
                # Check if values are correct
                units_correct = units == expected_units
                cost_correct = abs(cost_per_unit - expected_cost) < 0.01
                
                status = "✅ CORRECT" if (units_correct and cost_correct) else "❌ WRONG"
                
                print(f"{i:<2} | {name:<30} | ${unit_price:>8.2f} | {units:>4} | ${cost_per_unit:>8.2f} | ${expected_cost:>8.2f} | {status}")
                
                if not units_correct:
                    print(f"     Units: Expected {expected_units}, Got {units}")
                if not cost_correct:
                    print(f"     Cost: Expected ${expected_cost:.2f}, Got ${cost_per_unit:.2f}")
        
        print(f"\n🎯 SUMMARY:")
        print(f"Total items: {len(items.data)}")
        if len(items.data) > 6:
            print(f"⚠️  Expected 6 items, found {len(items.data)} (duplication issue)")
        else:
            print(f"✅ Item count correct: {len(items.data)}")
    
    else:
        print("❌ No INV-2025-0087 invoice found in database")

if __name__ == "__main__":
    main()
