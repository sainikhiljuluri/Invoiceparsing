#!/usr/bin/env python3
"""
Simplified terminal test for Components 6, 7, 8 integration
Tests with actual project structure
"""

import sys
import os
import asyncio
import json
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.pipeline_orchestrator import PipelineOrchestrator
from database.connection import DatabaseConnection
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def print_header(title):
    """Print a formatted header"""
    print(f"\n{'='*60}")
    print(f"🎯 {title}")
    print(f"{'='*60}")

def print_section(title):
    """Print a formatted section"""
    print(f"\n{'─'*40}")
    print(f"📋 {title}")
    print(f"{'─'*40}")

def print_result(key, value, indent=0):
    """Print a formatted result"""
    spaces = "  " * indent
    if isinstance(value, dict):
        print(f"{spaces}✅ {key}:")
        for k, v in value.items():
            print(f"{spaces}    {k}: {v}")
    elif isinstance(value, list):
        print(f"{spaces}✅ {key}: {len(value)} items")
        for i, item in enumerate(value[:3]):  # Show first 3
            print(f"{spaces}    [{i+1}] {item}")
    else:
        print(f"{spaces}✅ {key}: {value}")

async def main():
    """Main test function"""
    print_header("Invoice Processing Pipeline Test")
    print("🧪 Testing Components 6, 7, 8 Integration")
    
    # Check for PDF file argument
    if len(sys.argv) < 2:
        print("\n❌ Usage: python3 test_simple_pipeline.py <path_to_invoice.pdf>")
        print("\nExample:")
        print("  python3 test_simple_pipeline.py uploads/test1.pdf")
        return
    
    pdf_path = sys.argv[1]
    
    # Validate PDF file
    if not os.path.exists(pdf_path):
        print(f"❌ PDF file not found: {pdf_path}")
        return
    
    if not pdf_path.lower().endswith('.pdf'):
        print(f"❌ File must be a PDF: {pdf_path}")
        return
    
    print_result("PDF File", pdf_path)
    print_result("File Size", f"{os.path.getsize(pdf_path)} bytes")
    
    # Initialize system
    print_section("System Initialization")
    
    try:
        # Initialize database
        db = DatabaseConnection()
        print_result("Database Connection", "✅ Connected")
        
        # Initialize pipeline orchestrator
        pipeline = PipelineOrchestrator(db)
        print_result("Pipeline Orchestrator", "✅ Initialized")
        
        # Generate test invoice ID
        import uuid
        invoice_id = str(uuid.uuid4())
        print_result("Test Invoice ID", invoice_id)
        
    except Exception as e:
        print(f"❌ System initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Test the complete pipeline
    print_section("Complete Pipeline Processing")
    
    try:
        print("🚀 Starting complete pipeline processing...")
        
        # Process through the complete pipeline
        result = await pipeline.process_invoice(invoice_id, pdf_path)
        
        print_result("Pipeline Status", result.get('status', 'Unknown'))
        print_result("Processing Time", f"{result.get('processing_time', 0):.2f}s")
        
        # Show detailed results
        if 'vendor_detection' in result:
            print_section("Component 6: Claude AI Results")
            vendor_info = result['vendor_detection']
            print_result("Vendor Name", vendor_info.get('vendor_name', 'Not detected'))
            print_result("Invoice Number", vendor_info.get('invoice_number', 'Not found'))
            print_result("Total Amount", f"${vendor_info.get('total_amount', 0):.2f}")
            
            if 'line_items' in vendor_info:
                line_items = vendor_info['line_items']
                print_result("Line Items", f"{len(line_items)} products extracted")
                
                # Show first few items
                for i, item in enumerate(line_items[:3]):
                    print(f"    Item {i+1}:")
                    print_result("Product", item.get('product_name', 'Unknown'), 2)
                    print_result("Quantity", item.get('quantity', 0), 2)
                    print_result("Unit Price", f"${item.get('unit_price', 0):.2f}", 2)
        
        if 'product_matching' in result:
            print_section("Component 7: Product Matching Results")
            matching_info = result['product_matching']
            print_result("Total Products", matching_info.get('total_products', 0))
            print_result("Successfully Matched", matching_info.get('matched_products', 0))
            print_result("Match Rate", f"{matching_info.get('match_rate', 0):.1f}%")
            
            if 'matches' in matching_info:
                matches = matching_info['matches']
                print("\n📊 Matching Details:")
                for i, match in enumerate(matches[:3]):
                    print(f"    Match {i+1}:")
                    print_result("Product", match.get('product_name', 'Unknown'), 2)
                    print_result("Confidence", f"{match.get('confidence', 0):.1%}", 2)
                    print_result("Strategy", match.get('strategy', 'Unknown'), 2)
        
        if 'price_updates' in result:
            print_section("Component 8: Price Updates & Tracking")
            price_info = result['price_updates']
            print_result("Price Updates", price_info.get('updates_count', 0))
            print_result("Alerts Generated", price_info.get('alerts_count', 0))
            
            if 'alerts' in price_info and price_info['alerts']:
                print("\n🚨 Price Alerts:")
                for alert in price_info['alerts'][:3]:
                    print_result("Alert Type", alert.get('type', 'Unknown'), 1)
                    print_result("Product", alert.get('product_name', 'Unknown'), 1)
                    print_result("Message", alert.get('message', 'No message'), 1)
        
        # Summary
        print_header("Test Summary")
        
        total_items = result.get('vendor_detection', {}).get('line_items', [])
        matched_count = result.get('product_matching', {}).get('matched_products', 0)
        total_count = len(total_items) if total_items else 0
        match_rate = (matched_count / total_count * 100) if total_count > 0 else 0
        
        print_result("Total Line Items", total_count)
        print_result("Successfully Matched", matched_count)
        print_result("Match Rate", f"{match_rate:.1f}%")
        print_result("Processing Status", result.get('status', 'Unknown'))
        
        print(f"\n🎉 Pipeline test completed!")
        print(f"📊 Results: {matched_count}/{total_count} products matched ({match_rate:.1f}%)")
        
    except Exception as e:
        print(f"❌ Pipeline processing failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
