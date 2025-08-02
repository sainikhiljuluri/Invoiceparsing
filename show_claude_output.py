#!/usr/bin/env python3
"""
Display Claude Component 6 Output
Show exactly what the Claude processor extracts from invoices
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from components.invoice_processing.claude_processor import ClaudeInvoiceProcessor

async def show_claude_extraction():
    """Show what Claude Component 6 extracts from the test invoice"""
    
    print("🤖 Component 6: Claude Invoice Processor Output")
    print("=" * 60)
    
    # Initialize Claude processor
    processor = ClaudeInvoiceProcessor()
    
    # Process the test invoice
    invoice_path = "uploads/test1.pdf"
    
    print(f"📄 Processing: {invoice_path}")
    print("-" * 60)
    
    try:
        # Extract data with Claude
        result = await processor.process_invoice(invoice_path)
        
        print(f"\n🏢 VENDOR INFORMATION:")
        print(f"  Vendor Key: {result.vendor_key}")
        print(f"  Vendor Name: {result.vendor_name}")
        
        print(f"\n📋 INVOICE DETAILS:")
        print(f"  Invoice Number: {result.invoice_number}")
        print(f"  Invoice Date: {result.invoice_date}")
        print(f"  Currency: {result.currency}")
        
        print(f"\n💰 FINANCIAL TOTALS:")
        print(f"  Subtotal: {result.currency} {result.subtotal:,.2f}")
        print(f"  Tax Amount: {result.currency} {result.tax_amount:,.2f}")
        print(f"  Total Amount: {result.currency} {result.total_amount:,.2f}")
        
        print(f"\n📦 EXTRACTED PRODUCTS ({len(result.products)} items):")
        print("-" * 60)
        
        for i, product in enumerate(result.products, 1):
            print(f"\n{i}. {product.product_name}")
            print(f"   Line Number: {product.line_number}")
            print(f"   Quantity: {product.quantity}")
            print(f"   Unit Price: {result.currency} {product.unit_price:.2f}")
            print(f"   Total: {result.currency} {product.total:.2f}")
            
            if product.units_per_pack:
                print(f"   Units per Pack: {product.units_per_pack}")
                cost_per_unit = product.unit_price / product.units_per_pack
                print(f"   Cost per Unit: {result.currency} {cost_per_unit:.2f}")
            
            if product.cost_per_unit:
                print(f"   Cost per Unit (direct): {result.currency} {product.cost_per_unit:.2f}")
            
            if product.raw_text:
                print(f"   Raw Text: {product.raw_text[:50]}...")
        
        print(f"\n📊 SUMMARY:")
        print(f"  Total Products Extracted: {len(result.products)}")
        print(f"  Total Invoice Value: {result.currency} {result.total_amount:,.2f}")
        
        # Show data structure for debugging
        print(f"\n🔍 DATA STRUCTURE (for debugging):")
        print("-" * 60)
        
        for i, product in enumerate(result.products[:2], 1):  # Show first 2 products
            print(f"\nProduct {i} Data Structure:")
            product_dict = {
                'product_name': product.product_name,
                'line_number': product.line_number,
                'quantity': product.quantity,
                'unit_price': product.unit_price,
                'total': product.total,
                'units_per_pack': product.units_per_pack,
                'cost_per_unit': product.cost_per_unit,
                'raw_text': product.raw_text
            }
            
            for key, value in product_dict.items():
                print(f"  {key}: {value}")
        
    except Exception as e:
        print(f"❌ Error processing invoice: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(show_claude_extraction())
