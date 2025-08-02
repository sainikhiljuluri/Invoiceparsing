"""
Initialize database with all required tables and extensions
"""

import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from database.connection import db
from config.settings import settings

logger = logging.getLogger(__name__)

def verify_tables():
    """Verify that all tables were created"""
    expected_tables = [
        'vendors', 'products', 'invoices', 'invoice_items',
        'price_history', 'vendor_parsing_rules', 'product_mappings',
        'processing_queue', 'human_review_queue', 'claude_processing_results',
        'conversation_memory', 'dashboard_widgets', 'anomaly_detections',
        'predictive_models', 'notification_rules', 'import_batches',
        'product_aliases', 'brands'
    ]
    
    verified_tables = []
    missing_tables = []
    
    for table in expected_tables:
        try:
            # Try to query the table
            result = db.query(table, {})
            verified_tables.append(table)
            logger.info(f"✅ Table verified: {table}")
        except Exception as e:
            missing_tables.append(table)
            logger.error(f"❌ Table missing or error: {table} - {e}")
    
    return verified_tables, missing_tables

def init_database():
    """Initialize the database"""
    logger.info("=" * 50)
    logger.info("Verifying Database Setup...")
    logger.info("=" * 50)
    
    # Note: For Supabase, you need to run the SQL directly in the Dashboard
    logger.info("\n⚠️  IMPORTANT: Make sure you've run the schema.sql in Supabase SQL Editor")
    
    # Test database connection
    logger.info("\nTesting database connection...")
    try:
        # Test Supabase connection
        vendors = db.query('vendors')
        logger.info(f"✅ Supabase connection successful")
        logger.info(f"Found {len(vendors)} vendors")
        
        # Test Redis connection
        if db.redis_client:
            db.cache_set('test_key', 'test_value', 10)
            test_value = db.cache_get('test_key')
            if test_value == 'test_value':
                logger.info("✅ Redis connection successful")
            db.cache_delete('test_key')
        else:
            logger.warning("⚠️  Redis not connected - running without cache")
            
    except Exception as e:
        logger.error(f"❌ Database connection error: {e}")
        return False
    
    # Verify tables
    logger.info("\nVerifying tables...")
    verified, missing = verify_tables()
    
    logger.info(f"\n✅ Verified tables: {len(verified)}")
    logger.info(f"❌ Missing tables: {len(missing)}")
    
    if missing:
        logger.error(f"Missing tables: {', '.join(missing)}")
        logger.error("Please run the schema.sql in Supabase SQL Editor")
        return False
    
    # Check default data
    logger.info("\nChecking default data...")
    
    # Check vendors
    vendors = db.query('vendors')
    logger.info(f"Found {len(vendors)} vendors:")
    for vendor in vendors:
        logger.info(f"  - {vendor['name']} ({vendor['currency']})")
    
    # Check brands
    brands = db.get_brands()
    logger.info(f"Found {len(brands)} brands")
    
    # Get product stats
    stats = db.get_product_stats()
    logger.info(f"\nProduct Statistics:")
    logger.info(f"  Total products: {stats.get('total_products', 0)}")
    logger.info(f"  Active products: {stats.get('active_products', 0)}")
    
    logger.info("\n✅ Database initialization complete!")
    return True

if __name__ == "__main__":
    init_database()