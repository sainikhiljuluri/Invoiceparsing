#!/usr/bin/env python3
"""
Debug database to see what invoices exist
"""

import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from database.connection import DatabaseConnection
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def debug_database():
    """Debug what's in the database"""
    
    db = DatabaseConnection()
    await db.initialize()
    
    try:
        # Check processing queue
        logger.info("\n📋 PROCESSING QUEUE:")
        queue_items = await db.execute(
            """
            SELECT 
                id,
                status,
                filename,
                created_at,
                error_message
            FROM processing_queue
            ORDER BY created_at DESC
            LIMIT 10
            """,
            {}
        )
        
        if queue_items:
            for item in queue_items:
                logger.info(f"  {item['id']}: {item['status']} - {item['filename']}")
                if item['error_message']:
                    logger.info(f"    Error: {item['error_message']}")
        else:
            logger.info("  No items in processing queue")
        
        # Check invoices
        logger.info("\n📄 INVOICES:")
        invoices = await db.execute(
            """
            SELECT 
                i.id,
                i.invoice_number,
                i.total_amount,
                i.created_at,
                v.name as vendor_name
            FROM invoices i
            LEFT JOIN vendors v ON i.vendor_id = v.id
            ORDER BY i.created_at DESC
            LIMIT 10
            """,
            {}
        )
        
        if invoices:
            for inv in invoices:
                logger.info(f"  {inv['id']}: {inv['invoice_number']} - {inv['vendor_name']} - ₹{inv['total_amount']}")
        else:
            logger.info("  No invoices found")
        
        # Check vendors
        logger.info("\n🏢 VENDORS:")
        vendors = await db.execute(
            """
            SELECT id, vendor_key, name, currency
            FROM vendors
            ORDER BY name
            """,
            {}
        )
        
        if vendors:
            for vendor in vendors:
                logger.info(f"  {vendor['id']}: {vendor['vendor_key']} - {vendor['name']} ({vendor['currency']})")
        else:
            logger.info("  No vendors found")
        
        # Check specific invoice ID from logs
        test_id = "b3498d6a-8352-4444-b0fb-fc5938df9d82"
        logger.info(f"\n🔍 Looking for specific ID: {test_id}")
        
        # Check in processing_queue
        pq_result = await db.execute(
            "SELECT * FROM processing_queue WHERE id = :id",
            {"id": test_id}
        )
        
        if pq_result:
            logger.info(f"  Found in processing_queue: {pq_result[0]['status']}")
        else:
            logger.info("  Not found in processing_queue")
        
        # Check in invoices
        inv_result = await db.execute(
            "SELECT * FROM invoices WHERE id = :id",
            {"id": test_id}
        )
        
        if inv_result:
            logger.info(f"  Found in invoices: {inv_result[0]['invoice_number']}")
        else:
            logger.info("  Not found in invoices table")
            
    except Exception as e:
        logger.error(f"Error during debug: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(debug_database())