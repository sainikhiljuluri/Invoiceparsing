#!/usr/bin/env python3

import os
from supabase import create_client
from dotenv import load_dotenv
import json

load_dotenv()
supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_KEY'))

# Get the most recent successful invoice (completed status)
print("=== CHECKING SUCCESSFUL FYVE ELEMENTS INVOICE ===")
result = supabase.table('invoices').select('*').eq('processing_status', 'completed').order('created_at', desc=True).limit(1).execute()

if result.data:
    invoice = result.data[0]
    print(f"✅ Invoice ID: {invoice.get('id')}")
    print(f"✅ Invoice Number: {invoice.get('invoice_number')}")
    print(f"✅ Vendor Name: {invoice.get('vendor_name')}")
    print(f"✅ Invoice Date: {invoice.get('invoice_date')}")
    print(f"✅ Total Amount: ${invoice.get('total_amount')}")
    print(f"✅ Subtotal: ${invoice.get('subtotal')}")
    print(f"✅ Tax Amount: ${invoice.get('tax_amount')}")
    print(f"✅ Currency: {invoice.get('currency')}")
    print(f"✅ Processing Status: {invoice.get('processing_status')}")
    print(f"✅ Extraction Method: {invoice.get('extraction_method')}")
    print(f"✅ Created At: {invoice.get('created_at')}")
    
    # Get invoice items for this invoice
    invoice_id = invoice.get('id')
    items_result = supabase.table('invoice_items').select('*').eq('invoice_id', invoice_id).execute()
    
    print(f"\n=== INVOICE ITEMS ({len(items_result.data)} products) ===")
    for item in items_result.data:
        print(f"📦 Line {item.get('line_number')}: {item.get('product_name')}")
        print(f"   Quantity: {item.get('quantity')}")
        print(f"   Units: {item.get('units')}")
        print(f"   Unit Price: ${item.get('unit_price')}")
        print(f"   Total: ${item.get('total_price')}")
        print(f"   Cost per Unit: ${item.get('cost_per_unit')}")
        print(f"   Match Confidence: {item.get('match_confidence')}")
        print(f"   Match Strategy: {item.get('match_strategy')}")
        print()

else:
    print("❌ No successful invoices found")
    
    # Check all recent invoices
    print("\n=== ALL RECENT INVOICES ===")
    all_result = supabase.table('invoices').select('id, invoice_number, vendor_name, processing_status, created_at').order('created_at', desc=True).limit(5).execute()
    
    for inv in all_result.data:
        print(f"ID: {inv.get('id')[:8]}... | Number: {inv.get('invoice_number')} | Vendor: {inv.get('vendor_name')} | Status: {inv.get('processing_status')}")
