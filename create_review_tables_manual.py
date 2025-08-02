#!/usr/bin/env python3
"""
Manual Database Table Creation for Human Review System
Creates tables directly using Supabase table operations
"""

import json
from datetime import datetime
from database.connection import db

def create_tables_manually():
    """Create tables by inserting sample data and letting Supabase infer schema"""
    
    supabase = db.supabase
    
    print("🚀 Creating Human Review Tables Manually")
    print("=" * 50)
    
    # Test 1: Try to create human_review_queue table with sample data
    print("📋 Creating human_review_queue table...")
    try:
        # Sample review queue item
        sample_review_item = {
            'invoice_id': 'test-invoice-001',
            'invoice_item_id': 'test-item-001',
            'product_info': {
                'invoice_id': 'test-invoice-001',
                'product_name': 'HALDIRAM BHUJIA 200G',
                'confidence': 0.65,
                'strategy': 'fuzzy_match',
                'routing': 'review_priority_2',
                'suggested_matches': [
                    {
                        'id': 'prod-001',
                        'name': 'HALDIRAM ALOO BHUJIA 200G',
                        'score': 0.85
                    },
                    {
                        'id': 'prod-002', 
                        'name': 'HALDIRAM BHUJIA MIX 150G',
                        'score': 0.72
                    }
                ],
                'metadata': {
                    'units': 1,
                    'cost_per_unit': 45.0,
                    'vendor': 'HALDIRAM_FOODS',
                    'original_text': 'HALDIRAM BHUJIA 200G PACK'
                }
            },
            'priority': 2,
            'status': 'pending',
            'created_at': datetime.now().isoformat()
        }
        
        # Try to insert into human_review_queue
        result = supabase.table('human_review_queue').insert(sample_review_item).execute()
        
        if result.data:
            print("✅ human_review_queue table created and test data inserted")
            print(f"   Inserted review item ID: {result.data[0].get('id', 'unknown')}")
        else:
            print("⚠️ Could not insert into human_review_queue table")
            
    except Exception as e:
        print(f"❌ Error with human_review_queue: {str(e)}")
        print("💡 You may need to create this table manually in Supabase SQL Editor")
    
    # Test 2: Try to create product_mappings table with sample data
    print("\n🗺️ Creating product_mappings table...")
    try:
        # Sample product mapping
        sample_mapping = {
            'original_name': 'HALDIRAM BHUJIA',
            'mapped_product_id': 'prod-001',
            'vendor_key': 'HALDIRAM_FOODS',
            'confidence': 1.0,
            'mapping_source': 'human',
            'created_by': 'test_setup',
            'created_at': datetime.now().isoformat(),
            'usage_count': 0,
            'is_active': True
        }
        
        # Try to insert into product_mappings
        result = supabase.table('product_mappings').insert(sample_mapping).execute()
        
        if result.data:
            print("✅ product_mappings table created and test data inserted")
            print(f"   Inserted mapping ID: {result.data[0].get('id', 'unknown')}")
        else:
            print("⚠️ Could not insert into product_mappings table")
            
    except Exception as e:
        print(f"❌ Error with product_mappings: {str(e)}")
        print("💡 You may need to create this table manually in Supabase SQL Editor")
    
    print("\n📊 Testing API endpoints...")
    
    # Test the API endpoints
    try:
        import requests
        
        # Test stats endpoint
        response = requests.get('http://localhost:8000/api/v1/review/stats')
        if response.status_code == 200:
            print("✅ Review stats API working")
            stats = response.json()
            print(f"   Queue stats: {stats}")
        else:
            print(f"⚠️ Stats API returned status {response.status_code}")
            
        # Test queue endpoint
        response = requests.get('http://localhost:8000/api/v1/review/queue')
        if response.status_code == 200:
            print("✅ Review queue API working")
            queue = response.json()
            print(f"   Queue items: {len(queue)}")
        else:
            print(f"⚠️ Queue API returned status {response.status_code}")
            
    except Exception as e:
        print(f"⚠️ Could not test API endpoints: {str(e)}")
        print("💡 Make sure the server is running on localhost:8000")
    
    print("\n🎯 Next Steps:")
    print("1. Visit http://localhost:3000/review.html to test the interface")
    print("2. If tables don't exist, create them manually in Supabase SQL Editor")
    print("3. Upload some invoices to generate real review items")
    
    return True

if __name__ == "__main__":
    create_tables_manually()
