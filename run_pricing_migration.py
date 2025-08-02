#!/usr/bin/env python3
"""
Run pricing recommendations table migration
"""

import os
import sys
import logging
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from database.connection import DatabaseConnection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_pricing_migration():
    """Run the pricing recommendations table migration"""
    
    try:
        # Initialize database connection
        db = DatabaseConnection()
        
        # Read the migration SQL
        migration_file = project_root / "database" / "migrations" / "create_pricing_recommendations_table.sql"
        
        if not migration_file.exists():
            logger.error(f"Migration file not found: {migration_file}")
            return False
        
        with open(migration_file, 'r') as f:
            sql_content = f.read()
        
        logger.info("Running pricing recommendations table migration...")
        
        # Execute the migration
        result = db.supabase.rpc('exec_sql', {'sql': sql_content}).execute()
        
        if result.data:
            logger.info("✅ Pricing recommendations table migration completed successfully!")
            logger.info("The following table was created:")
            logger.info("- pricing_recommendations (with indexes and triggers)")
            return True
        else:
            logger.error("❌ Migration failed - no result returned")
            return False
            
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        return False

if __name__ == "__main__":
    success = run_pricing_migration()
    sys.exit(0 if success else 1)
