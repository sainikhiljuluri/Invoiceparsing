#!/usr/bin/env python3
"""
Script to get all products from the most complete processed invoice
"""

import os
import sys
from pathlib import Path
from supabase import create_client
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

def get_complete_invoice_products():
    """Get all products from the most complete processed invoice"""
    try:
        # Get Supabase credentials
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        
        if not supabase_url or not supabase_key:
            print("❌ Missing Supabase credentials")
            return
        
        # Create Supabase client
        supabase = create_client(supabase_url, supabase_key)
        
        print("🔍 Finding invoices with complete product data...")
        
        # Get all invoice items with product names
        items_result = supabase.table('invoice_items').select('*').not_.is_('invoice_product_name', 'null').execute()
        items = items_result.data
        
        if not items:
            print("❌ No invoice items with product names found")
            return
        
        # Group items by invoice_id to find the invoice with the most products
        invoice_groups = {}
        for item in items:
            invoice_id = item.get('invoice_id')
            if invoice_id:
                if invoice_id not in invoice_groups:
                    invoice_groups[invoice_id] = []
                invoice_groups[invoice_id].append(item)
        
        if not invoice_groups:
            print("❌ No grouped invoice items found")
            return
        
        # Find the invoice with the most products
        best_invoice_id = max(invoice_groups.keys(), key=lambda x: len(invoice_groups[x]))
        best_items = invoice_groups[best_invoice_id]
        
        # Get invoice details
        invoice_result = supabase.table('invoices').select('*').eq('id', best_invoice_id).execute()
        invoice_data = invoice_result.data[0] if invoice_result.data else {}
        
        invoice_number = invoice_data.get('invoice_number', 'Unknown')
        vendor_name = invoice_data.get('vendor_name', 'Unknown')
        invoice_date = invoice_data.get('invoice_date', 'Unknown')
        total_amount = invoice_data.get('total_amount', 'Unknown')
        
        print(f"\n📋 Best Invoice with Complete Product Data:")
        print(f"   Invoice Number: {invoice_number}")
        print(f"   Vendor: {vendor_name}")
        print(f"   Date: {invoice_date}")
        print(f"   Total Amount: ${total_amount}")
        print(f"   Products Found: {len(best_items)}")
        
        print(f"\n🛒 ALL PRODUCTS IN INVOICE {invoice_number}:")
        print("=" * 80)
        
        total_calculated = 0
        
        for i, item in enumerate(best_items, 1):
            product_name = item.get('invoice_product_name', 'Unknown Product')
            quantity = item.get('quantity', 0)
            units = item.get('units', 0)
            unit_price = item.get('unit_price', 0)
            total_amount = item.get('total_amount', 0)
            cost_per_unit = item.get('cost_per_unit', 0)
            match_confidence = item.get('match_confidence', 0)
            
            print(f"{i:2d}. {product_name}")
            
            if quantity:
                print(f"     📦 Quantity: {quantity}")
            if units and units != quantity:
                print(f"     📊 Units per Pack: {units}")
            if unit_price:
                print(f"     💰 Unit Price: ${unit_price}")
            if cost_per_unit:
                print(f"     🏷️  Cost per Unit: ${cost_per_unit}")
            if total_amount:
                print(f"     💵 Line Total: ${total_amount}")
                total_calculated += float(total_amount)
            if match_confidence:
                print(f"     🎯 Match Confidence: {float(match_confidence)*100:.1f}%")
            
            print()
        
        print("=" * 80)
        print(f"📊 INVOICE SUMMARY:")
        print(f"   📦 Total Products: {len(best_items)}")
        print(f"   💵 Calculated Total: ${total_calculated:.2f}")
        print(f"   📋 Invoice Total: ${total_amount}")
        
        # Show all available invoices for reference
        print(f"\n📄 All Available Invoices ({len(invoice_groups)} with products):")
        for inv_id, inv_items in invoice_groups.items():
            inv_result = supabase.table('invoices').select('invoice_number, vendor_name, invoice_date').eq('id', inv_id).execute()
            inv_data = inv_result.data[0] if inv_result.data else {}
            inv_number = inv_data.get('invoice_number', 'Unknown')
            inv_vendor = inv_data.get('vendor_name', 'Unknown')
            inv_date = inv_data.get('invoice_date', 'Unknown')
            print(f"   • {inv_number} - {inv_vendor} ({inv_date}) - {len(inv_items)} products")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    get_complete_invoice_products()
