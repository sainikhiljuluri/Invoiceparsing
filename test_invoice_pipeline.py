#!/usr/bin/env python3
"""
Terminal test script for integrated Components 6, 7, 8
Tests the complete invoice processing pipeline with a real PDF
"""

import sys
import os
import asyncio
import json
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.connection import DatabaseConnection
from services.pipeline_orchestrator import PipelineOrchestrator
from components.invoice_processing.claude_processor import ClaudeInvoiceProcessor
from components.product_matching.product_matcher import ProductMatcher
from components.pricing.price_repository import PriceRepository
from components.pricing.price_analytics import PriceAnalytics
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
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
    if isinstance(value, (dict, list)):
        print(f"{spaces}✅ {key}: {json.dumps(value, indent=2)}")
    else:
        print(f"{spaces}✅ {key}: {value}")

async def test_component_6(pipeline, invoice_id, pdf_path):
    """Test Component 6: Claude AI Invoice Processing"""
    print_section("Component 6: Claude AI Invoice Processing")
    
    try:
        # Process with Claude
        claude_result = await pipeline.claude_processor.process_invoice(pdf_path)
        
        print_result("Vendor Detection", claude_result.get('vendor_name', 'Not detected'))
        print_result("Invoice Number", claude_result.get('invoice_number', 'Not found'))
        print_result("Invoice Date", claude_result.get('invoice_date', 'Not found'))
        print_result("Total Amount", f"${claude_result.get('total_amount', 0):.2f}")
        print_result("Currency", claude_result.get('currency', 'USD'))
        
        line_items = claude_result.get('line_items', [])
        print_result("Line Items Count", len(line_items))
        
        if line_items:
            print("\n📄 Line Items:")
            for i, item in enumerate(line_items[:5]):  # Show first 5 items
                print(f"  Item {i+1}:")
                print_result("Product", item.get('product_name', 'Unknown'), 1)
                print_result("Quantity", item.get('quantity', 0), 1)
                print_result("Unit Price", f"${item.get('unit_price', 0):.2f}", 1)
                print_result("Total", f"${item.get('total_price', 0):.2f}", 1)
        
        return claude_result
        
    except Exception as e:
        print(f"❌ Component 6 failed: {e}")
        return None

async def test_component_7(pipeline, claude_result):
    """Test Component 7: Advanced Product Matching"""
    print_section("Component 7: Advanced Product Matching")
    
    if not claude_result or not claude_result.get('line_items'):
        print("❌ No line items to match")
        return []
    
    matching_results = []
    line_items = claude_result.get('line_items', [])
    
    print(f"🔍 Matching {len(line_items)} products...")
    
    for i, item in enumerate(line_items):
        print(f"\n  Product {i+1}: {item.get('product_name', 'Unknown')}")
        
        try:
            # Test product matching
            match_result = pipeline.product_matcher.match_product(item)
            
            if match_result.matched:
                print_result("Match Found", "✅ YES", 1)
                print_result("Product ID", match_result.product_id, 1)
                print_result("Matched Name", match_result.product_name, 1)
                print_result("Confidence", f"{match_result.confidence:.2%}", 1)
                print_result("Strategy", match_result.strategy, 1)
                print_result("Routing", match_result.routing, 1)
            else:
                print_result("Match Found", "❌ NO", 1)
                print_result("Reason", match_result.reason, 1)
            
            matching_results.append({
                'item': item,
                'match_result': match_result
            })
            
        except Exception as e:
            print(f"    ❌ Matching failed: {e}")
    
    return matching_results

async def test_component_8(pipeline, matching_results, vendor_id=None):
    """Test Component 8: Price Updates & Tracking"""
    print_section("Component 8: Price Updates & Tracking")
    
    if not matching_results:
        print("❌ No matching results to process")
        return
    
    price_updates = 0
    alerts_generated = 0
    
    for result in matching_results:
        if not result['match_result'].matched:
            continue
            
        item = result['item']
        match = result['match_result']
        
        try:
            # Test price update
            new_price = item.get('unit_price', 0)
            if new_price > 0:
                print(f"\n  Updating price for: {match.product_name}")
                
                # Update price
                price_update_result = await pipeline.price_updater.update_product_price(
                    product_id=match.product_id,
                    new_price=new_price,
                    vendor_id=vendor_id,
                    invoice_id="test-invoice"
                )
                
                if price_update_result:
                    price_updates += 1
                    print_result("Price Updated", f"${new_price:.2f}", 1)
                    
                    # Check for alerts
                    if price_update_result.get('alert_generated'):
                        alerts_generated += 1
                        print_result("Alert Generated", "🚨 YES", 1)
                        print_result("Alert Type", price_update_result.get('alert_type'), 1)
                
        except Exception as e:
            print(f"    ❌ Price update failed: {e}")
    
    print_result("Total Price Updates", price_updates)
    print_result("Total Alerts Generated", alerts_generated)

async def main():
    """Main test function"""
    print_header("Invoice Processing Pipeline Test")
    print("🧪 Testing Components 6, 7, 8 Integration")
    
    # Check for PDF file argument
    if len(sys.argv) < 2:
        print("\n❌ Usage: python3 test_invoice_pipeline.py <path_to_invoice.pdf>")
        print("\nExample:")
        print("  python3 test_invoice_pipeline.py /path/to/invoice.pdf")
        print("  python3 test_invoice_pipeline.py ./sample_invoice.pdf")
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
        return
    
    # Test Component 6: Claude AI Processing
    claude_result = await test_component_6(pipeline, invoice_id, pdf_path)
    
    if not claude_result:
        print("\n❌ Cannot proceed without Claude results")
        return
    
    # Test Component 7: Product Matching
    matching_results = await test_component_7(pipeline, claude_result)
    
    # Test Component 8: Price Updates
    vendor_id = claude_result.get('vendor_id')
    await test_component_8(pipeline, matching_results, vendor_id)
    
    # Summary
    print_header("Test Summary")
    
    total_items = len(claude_result.get('line_items', []))
    matched_items = sum(1 for r in matching_results if r['match_result'].matched)
    match_rate = (matched_items / total_items * 100) if total_items > 0 else 0
    
    print_result("Total Line Items", total_items)
    print_result("Successfully Matched", matched_items)
    print_result("Match Rate", f"{match_rate:.1f}%")
    print_result("Vendor Detected", claude_result.get('vendor_name', 'Unknown'))
    print_result("Total Amount", f"${claude_result.get('total_amount', 0):.2f}")
    
    print(f"\n🎉 Pipeline test completed successfully!")
    print(f"📊 Results: {matched_items}/{total_items} products matched ({match_rate:.1f}%)")

if __name__ == "__main__":
    asyncio.run(main())
