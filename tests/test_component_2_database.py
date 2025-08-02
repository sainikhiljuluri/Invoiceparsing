"""
Test database configuration and connections
"""

import sys
import json
import asyncio
from pathlib import Path
from datetime import datetime
import pytest
import numpy as np

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from database.connection import db, import_products_async

def test_supabase_connection():
    """Test Supabase PostgreSQL connection"""
    try:
        # Test basic query
        result = db.query('vendors')
        assert isinstance(result, list)
        print(f"✅ Supabase connection working - found {len(result)} vendors")
    except Exception as e:
        pytest.fail(f"Supabase connection failed: {e}")

def test_redis_connection():
    """Test Redis connection"""
    if not db.redis_client:
        pytest.skip("Redis not configured")
    
    # Test set and get
    test_key = "test:connection"
    test_value = {"test": "data", "timestamp": str(datetime.now())}
    
    # Set value
    success = db.cache_set(test_key, test_value, 30)
    assert success, "Failed to set Redis value"
    
    # Get value
    retrieved = db.cache_get(test_key)
    assert retrieved == test_value, "Retrieved value doesn't match"
    
    # Delete value
    deleted = db.cache_delete(test_key)
    assert deleted, "Failed to delete Redis value"
    
    print("✅ Redis connection working")

def test_vendor_operations():
    """Test vendor table operations"""
    vendors = db.query('vendors')
    assert len(vendors) >= 4, "Expected at least 4 default vendors"
    
    vendor_names = [v['name'] for v in vendors]
    expected_vendors = ['NIKHIL DISTRIBUTORS', 'CHETAK SAN FRANCISCO LLC', 'RAJA FOODS', 'JK WHOLESALE']
    
    for expected in expected_vendors:
        assert expected in vendor_names, f"Missing vendor: {expected}"
    
    print(f"✅ Found all {len(expected_vendors)} default vendors")

def test_brand_operations():
    """Test brand operations"""
    brands = db.get_brands()
    assert len(brands) >= 15, "Expected at least 15 default brands"
    
    brand_names = [b['name'] for b in brands]
    expected_brands = ['DEEP', 'HALDIRAM', 'VADILAL', 'MTR', 'SWAD']
    
    for expected in expected_brands:
        assert expected in brand_names, f"Missing brand: {expected}"
    
    print(f"✅ Found {len(brands)} brands")

def test_bulk_operations():
    """Test bulk insert capabilities"""
    # Create test products
    test_products = [
        {
            'name': f'BULK TEST PRODUCT {i}',
            'brand': 'TEST BRAND',
            'category': 'TEST',
            'barcode': f'TEST{i:06d}',
            'cost': 10.50 + i,
            'pack_size': '500g',
            'units_per_case': 12,
            'search_text': f'bulk test product {i} test brand'
        }
        for i in range(100)
    ]
    
    # Test bulk insert
    inserted, errors = db.bulk_insert('products', test_products, batch_size=50)
    print(f"✅ Bulk inserted {inserted} products with {len(errors)} errors")
    
    assert inserted > 0, "Bulk insert failed"

def test_product_search():
    """Test enhanced product search"""
    # First insert a searchable product
    test_product = {
        'name': 'DEEP CASHEW WHOLE 7OZ',
        'brand': 'DEEP',
        'category': 'Dry Fruits',
        'barcode': 'TESTCASHEW001',
        'pack_size': '7OZ',
        'units_per_case': 20,
        'cost': 30.00,
        'search_text': 'deep cashew whole 7oz dry fruits'
    }
    
    db.insert('products', test_product)
    
    # Test text search
    results = db.search_products(query="cashew", limit=10)
    print(f"✅ Text search found {len(results)} products")
    
    # Test filtered search
    results = db.search_products(
        query="cashew",
        filters={'brand': 'DEEP'},
        limit=5
    )
    print(f"✅ Filtered search found {len(results)} products")

def test_barcode_lookup():
    """Test fast barcode lookup"""
    # First, get a product with barcode
    products = db.query('products', {})
    if products and products[0].get('barcode'):
        barcode = products[0]['barcode']
        
        # Test lookup
        product = db.get_product_by_barcode(barcode)
        assert product is not None, "Barcode lookup failed"
        print(f"✅ Barcode lookup successful: {product['name']}")

def test_import_batch_tracking():
    """Test import batch functionality"""
    # Create batch
    batch = db.create_import_batch('test_import.xlsx', 1000)
    assert batch is not None, "Failed to create import batch"
    
    # Update batch
    success = db.update_import_batch(batch['id'], {
        'imported_rows': 950,
        'failed_rows': 50,
        'status': 'completed_with_errors'
    })
    assert success, "Failed to update import batch"
    print(f"✅ Import batch tracking working")

def test_cache_operations():
    """Test caching for performance"""
    # Get some products
    products = db.query('products', {})[:10]
    
    if products:
        # Cache them
        cached_count = db.cache_product_batch(products)
        print(f"✅ Cached {cached_count} product entries")
        
        # Test cache retrieval
        if products[0].get('barcode'):
            cached = db.get_product_by_barcode(products[0]['barcode'])
            assert cached is not None, "Cache retrieval failed"
            print("✅ Cache retrieval working")

async def test_async_import():
    """Test async import simulation"""
    # Create small test batch
    test_products = [
        {
            'name': f'ASYNC TEST {i}',
            'brand': 'ASYNC BRAND',
            'barcode': f'ASYNC{i:06d}',
            'cost': 15.00,
            'search_text': f'async test {i} async brand'
        }
        for i in range(50)
    ]
    
    # Run async import
    inserted, errors = await import_products_async(test_products, batch_size=10)
    print(f"✅ Async import: {inserted} inserted, {len(errors)} errors")

def test_product_stats():
    """Test analytics functions"""
    stats = db.get_product_stats()
    print(f"✅ Product stats:")
    print(f"   Total products: {stats.get('total_products', 0)}")
    print(f"   Active products: {stats.get('active_products', 0)}")
    if stats.get('top_brands'):
        print(f"   Top brand: {stats['top_brands'][0]}")

def test_all_tables_exist():
    """Test that all required tables exist"""
    required_tables = [
        'vendors', 'products', 'invoices', 'invoice_items',
        'price_history', 'vendor_parsing_rules', 'product_mappings',
        'processing_queue', 'human_review_queue', 'claude_processing_results',
        'conversation_memory', 'dashboard_widgets', 'anomaly_detections',
        'predictive_models', 'notification_rules', 'import_batches',
        'product_aliases', 'brands'
    ]
    
    missing_tables = []
    for table in required_tables:
        try:
            db.query(table)
        except Exception as e:
            missing_tables.append(table)
    
    if missing_tables:
        pytest.fail(f"Missing tables: {', '.join(missing_tables)}")
    else:
        print(f"✅ All {len(required_tables)} tables exist")

if __name__ == "__main__":
    print("Testing Enhanced Database Configuration...")
    print("=" * 60)
    
    # Run sync tests
    test_supabase_connection()
    test_redis_connection()
    test_vendor_operations()
    test_brand_operations()
    test_bulk_operations()
    test_product_search()
    test_barcode_lookup()
    test_import_batch_tracking()
    test_cache_operations()
    test_product_stats()
    test_all_tables_exist()
    
    # Run async test
    asyncio.run(test_async_import())
    
    print("=" * 60)
    print("✅ All database tests passed!")