#!/usr/bin/env python3
"""
Setup script for Human Review Database Tables
Creates the necessary tables in Supabase for the human review system
"""

import os
import sys
import json
from database.connection import db

def create_review_tables():
    """Create human review tables in Supabase"""
    
    supabase = db.supabase
    
    try:
        print("🔧 Setting up Human Review Database Tables...")
        
        # Check if tables exist by trying to select from them
        print("📋 Checking human_review_queue table...")
        try:
            result = supabase.table('human_review_queue').select('id').limit(1).execute()
            print("✅ human_review_queue table already exists")
            queue_exists = True
        except Exception as e:
            print(f"⚠️ human_review_queue table doesn't exist: {str(e)}")
            queue_exists = False
            
        print("🗺️ Checking product_mappings table...")
        try:
            result = supabase.table('product_mappings').select('id').limit(1).execute()
            print("✅ product_mappings table already exists")
            mappings_exists = True
        except Exception as e:
            print(f"⚠️ product_mappings table doesn't exist: {str(e)}")
            mappings_exists = False
        
        if not queue_exists or not mappings_exists:
            print("\n💡 Some tables are missing. You'll need to create them manually in Supabase.")
            print("📝 SQL to run in Supabase SQL Editor:")
            print("\n-- Human Review Queue Table")
            print("CREATE TABLE human_review_queue (")
            print("    id SERIAL PRIMARY KEY,")
            print("    invoice_id VARCHAR(255) NOT NULL,")
            print("    invoice_item_id VARCHAR(255),")
            print("    product_info JSONB NOT NULL,")
            print("    priority INTEGER DEFAULT 2,")
            print("    status VARCHAR(50) DEFAULT 'pending',")
            print("    reviewed_by VARCHAR(255),")
            print("    reviewed_at TIMESTAMP,")
            print("    review_decision JSONB,")
            print("    created_at TIMESTAMP DEFAULT NOW(),")
            print("    updated_at TIMESTAMP DEFAULT NOW()")
            print(");")
            print("\n-- Product Mappings Table")
            print("CREATE TABLE product_mappings (")
            print("    id SERIAL PRIMARY KEY,")
            print("    original_name VARCHAR(500) NOT NULL,")
            print("    normalized_name VARCHAR(500),")
            print("    mapped_product_id VARCHAR(255) NOT NULL,")
            print("    vendor_key VARCHAR(100) NOT NULL,")
            print("    confidence DECIMAL(3,2) DEFAULT 1.0,")
            print("    mapping_source VARCHAR(50) DEFAULT 'human',")
            print("    created_by VARCHAR(255),")
            print("    created_at TIMESTAMP DEFAULT NOW(),")
            print("    usage_count INTEGER DEFAULT 0,")
            print("    is_active BOOLEAN DEFAULT true,")
            print("    UNIQUE(original_name, vendor_key)")
            print(");")
        
        # Try to insert test data if tables exist
        if queue_exists:
            print("\n🧪 Adding test data...")
            insert_test_data(supabase)
        
        return True
        
    except Exception as e:
        print(f"❌ Error during setup: {str(e)}")
        return False

def insert_test_data(supabase):
    """Insert test data for the review interface"""
    
    try:
        # Test review queue item
        test_review_item = {
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
            'status': 'pending'
        }
        
        # Insert test review item
        result = supabase.table('human_review_queue').insert({
            'invoice_id': test_review_item['invoice_id'],
            'invoice_item_id': test_review_item['invoice_item_id'],
            'product_info': test_review_item['product_info'],
            'priority': test_review_item['priority'],
            'status': test_review_item['status']
        }).execute()
        
        if result.data:
            print("✅ Test review item added successfully")
        else:
            print("⚠️ Could not add test review item")
            
        # Test product mapping
        test_mapping = {
            'original_name': 'HALDIRAM BHUJIA',
            'mapped_product_id': 'prod-001',
            'vendor_key': 'HALDIRAM_FOODS',
            'confidence': 1.0,
            'mapping_source': 'human',
            'created_by': 'test_setup'
        }
        
        result2 = supabase.table('product_mappings').insert(test_mapping).execute()
        
        if result2.data:
            print("✅ Test product mapping added successfully")
        else:
            print("⚠️ Could not add test product mapping")
            
    except Exception as e:
        print(f"⚠️ Could not insert test data: {str(e)}")
        print("💡 This is normal if tables don't exist yet")

def check_existing_tables(supabase):
    """Check what tables already exist"""
    
    print("🔍 Checking existing database structure...")
    
    # Check for existing tables
    tables_to_check = [
        'invoices', 'invoice_items', 'products', 'vendors',
        'human_review_queue', 'product_mappings'
    ]
    
    for table in tables_to_check:
        try:
            result = supabase.table(table).select('*').limit(1).execute()
            print(f"✅ Table '{table}' exists ({len(result.data)} sample records)")
        except Exception as e:
            print(f"❌ Table '{table}' not found or inaccessible")

if __name__ == "__main__":
    print("🚀 Human Review Database Setup")
    print("=" * 50)
    
    try:
        # Check existing structure
        supabase = get_supabase_client()
        check_existing_tables(supabase)
        
        print("\n" + "=" * 50)
        
        # Create review tables
        success = create_review_tables()
        
        if success:
            print("\n✅ Setup completed successfully!")
            print("\n🎯 Next steps:")
            print("1. Visit http://localhost:3000/review.html")
            print("2. Check the review queue for test items")
            print("3. Upload some invoices to generate real review items")
        else:
            print("\n⚠️ Setup completed with warnings")
            print("You may need to create tables manually in Supabase")
            
    except Exception as e:
        print(f"\n❌ Setup failed: {str(e)}")
        sys.exit(1)
