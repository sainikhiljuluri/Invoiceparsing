#!/usr/bin/env python3
"""
Script to get all products from invoices in the database
"""

import os
import sys
from pathlib import Path
from supabase import create_client
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

def get_invoice_products():
    """Get all products from invoices"""
    try:
        # Get Supabase credentials
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        
        if not supabase_url or not supabase_key:
            print("❌ Missing Supabase credentials")
            return
        
        # Create Supabase client
        supabase = create_client(supabase_url, supabase_key)
        
        print("🔍 Fetching invoices...")
        
        # Get all invoices
        invoices_result = supabase.table('invoices').select('*').execute()
        invoices = invoices_result.data
        
        print(f"📄 Found {len(invoices)} invoices")
        
        if not invoices:
            print("❌ No invoices found in database")
            return
        
        # Get the most recent invoice
        latest_invoice = max(invoices, key=lambda x: x['created_at'])
        invoice_id = latest_invoice['id']
        invoice_number = latest_invoice.get('invoice_number', 'Unknown')
        vendor_name = latest_invoice.get('vendor_name', 'Unknown')
        
        print(f"\n📋 Latest Invoice Details:")
        print(f"   Invoice Number: {invoice_number}")
        print(f"   Vendor: {vendor_name}")
        print(f"   Date: {latest_invoice.get('invoice_date', 'Unknown')}")
        print(f"   Total: {latest_invoice.get('total_amount', 'Unknown')}")
        
        # Get all invoice items for this invoice
        print(f"\n🔍 Fetching products from invoice {invoice_number}...")
        
        items_result = supabase.table('invoice_items').select('*').eq('invoice_id', invoice_id).execute()
        items = items_result.data
        
        if not items:
            print("❌ No products found in this invoice")
            
            # Check if there are ANY invoice items in the database
            all_items_result = supabase.table('invoice_items').select('*').limit(10).execute()
            all_items = all_items_result.data
            
            if all_items:
                print(f"\n📦 Found {len(all_items)} invoice items in database (from other invoices):")
                for i, item in enumerate(all_items[:5], 1):
                    print(f"   {i}. {item.get('invoice_product_name', 'Unknown Product')}")
                    print(f"      Quantity: {item.get('quantity', 'N/A')}")
                    print(f"      Unit Price: ${item.get('unit_price', 'N/A')}")
                    print(f"      Total: ${item.get('total_amount', 'N/A')}")
                    print()
            else:
                print("❌ No invoice items found in entire database")
            return
        
        print(f"✅ Found {len(items)} products in invoice {invoice_number}:")
        print("=" * 60)
        
        total_invoice_value = 0
        
        for i, item in enumerate(items, 1):
            product_name = item.get('invoice_product_name', 'Unknown Product')
            quantity = item.get('quantity', 0)
            units = item.get('units', 0)
            unit_price = item.get('unit_price', 0)
            total_amount = item.get('total_amount', 0)
            cost_per_unit = item.get('cost_per_unit', 0)
            
            print(f"{i}. {product_name}")
            print(f"   📦 Quantity: {quantity}")
            if units and units != quantity:
                print(f"   📊 Units per Pack: {units}")
            print(f"   💰 Unit Price: ${unit_price}")
            if cost_per_unit:
                print(f"   🏷️  Cost per Unit: ${cost_per_unit}")
            print(f"   💵 Total Amount: ${total_amount}")
            
            # Add to total
            if total_amount:
                total_invoice_value += float(total_amount)
            
            print()
        
        print("=" * 60)
        print(f"📊 Invoice Summary:")
        print(f"   Total Products: {len(items)}")
        print(f"   Total Value: ${total_invoice_value:.2f}")
        
        # Also show all invoices available
        print(f"\n📄 All Available Invoices:")
        for inv in invoices:
            print(f"   • {inv.get('invoice_number', 'Unknown')} - {inv.get('vendor_name', 'Unknown')} ({inv.get('invoice_date', 'Unknown')})")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    get_invoice_products()
