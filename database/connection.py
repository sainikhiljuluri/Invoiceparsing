"""
Enhanced database connection module for 38,776 products
Optimized for wholesale food distribution system
"""

import json
import logging
import redis
from typing import Optional, Dict, Any, List, Tuple
from supabase import create_client, Client
from contextlib import contextmanager
import asyncio
from datetime import datetime

from config.settings import settings

logger = logging.getLogger(__name__)

class DatabaseConnection:
    """Enhanced database connection with bulk operations support"""
    
    def __init__(self):
        # Initialize Supabase client
        self.supabase: Client = create_client(
            settings.supabase_url,
            settings.supabase_service_key
        )
        
        # Initialize Redis client
        try:
            self.redis_client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=True,
                health_check_interval=30
            )
            self.redis_client.ping()
            logger.info("Redis connection established")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Running without cache.")
            self.redis_client = None
    
    # PostgreSQL Methods
    def query(self, table: str, filters: Dict = None) -> List[Dict]:
        """Query PostgreSQL table"""
        try:
            query = self.supabase.table(table).select("*")
            
            if filters:
                for key, value in filters.items():
                    query = query.eq(key, value)
            
            result = query.execute()
            return result.data
        except Exception as e:
            logger.error(f"Query error: {e}")
            return []
    
    def insert(self, table: str, data: Dict) -> Optional[Dict]:
        """Insert data into PostgreSQL table"""
        try:
            result = self.supabase.table(table).insert(data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Insert error: {e}")
            return None
    
    def update(self, table: str, id: str, data: Dict) -> Optional[Dict]:
        """Update data in PostgreSQL table"""
        try:
            result = self.supabase.table(table).update(data).eq('id', id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Update error: {e}")
            return None
    
    # Enhanced PostgreSQL Methods for 38k products
    
    def bulk_insert(self, table: str, data: List[Dict], batch_size: int = 1000) -> Tuple[int, List[Dict]]:
        """Bulk insert with batching for large datasets"""
        inserted_count = 0
        errors = []
        
        # Process in batches to handle 38k products efficiently
        for i in range(0, len(data), batch_size):
            batch = data[i:i + batch_size]
            try:
                result = self.supabase.table(table).insert(batch).execute()
                inserted_count += len(result.data)
                logger.info(f"Inserted batch {i//batch_size + 1}: {len(result.data)} records")
            except Exception as e:
                logger.error(f"Batch insert error at {i}: {e}")
                errors.extend([{"index": i+j, "error": str(e)} for j in range(len(batch))])
        
        return inserted_count, errors
    
    def upsert_products(self, products: List[Dict], conflict_columns: List[str] = ['barcode']) -> Tuple[int, int]:
        """Upsert products with conflict resolution"""
        try:
            result = self.supabase.table('products').upsert(
                products,
                on_conflict=','.join(conflict_columns)
            ).execute()
            
            updated = len([p for p in result.data if p.get('updated_at') != p.get('created_at')])
            inserted = len(result.data) - updated
            
            return inserted, updated
        except Exception as e:
            logger.error(f"Upsert error: {e}")
            return 0, 0
    
    def search_products(self, 
                       query: str = None,
                       embedding: List[float] = None,
                       filters: Dict = None,
                       limit: int = 20) -> List[Dict]:
        """Enhanced product search with multiple strategies"""
        try:
            # Check cache first for text queries
            if query and self.redis_client:
                cache_key = f"search:{query}:{limit}"
                cached = self.cache_get(cache_key)
                if cached:
                    return cached
            
            # Use the enhanced search function
            params = {
                'search_query': query,
                'query_embedding': embedding,
                'match_count': limit
            }
            
            if filters:
                params.update({
                    'brand_filter': filters.get('brand'),
                    'category_filter': filters.get('category')
                })
            
            result = self.supabase.rpc('search_products', params).execute()
            
            # Cache results for text queries
            if query and self.redis_client and result.data:
                self.cache_set(f"search:{query}:{limit}", result.data, ttl=300)  # 5 min cache
            
            return result.data
        except Exception as e:
            logger.error(f"Product search error: {e}")
            return []
    
    def get_product_by_barcode(self, barcode: str) -> Optional[Dict]:
        """Fast barcode lookup with caching"""
        if not barcode:
            return None
        
        # Check cache
        cache_key = f"product:barcode:{barcode}"
        if self.redis_client:
            cached = self.cache_get(cache_key)
            if cached:
                return cached
        
        try:
            result = self.supabase.table('products')\
                .select("*")\
                .eq('barcode', barcode)\
                .single()\
                .execute()
            
            if result.data and self.redis_client:
                self.cache_set(cache_key, result.data, ttl=3600)  # 1 hour cache
            
            return result.data
        except Exception as e:
            logger.error(f"Barcode lookup error: {e}")
            return None
    
    def create_import_batch(self, file_name: str, total_rows: int) -> Dict:
        """Create import batch for tracking Excel imports"""
        try:
            batch_data = {
                'file_name': file_name,
                'total_rows': total_rows,
                'status': 'processing',
                'started_at': datetime.now().isoformat()
            }
            
            result = self.supabase.table('import_batches').insert(batch_data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Import batch creation error: {e}")
            return None
    
    def update_import_batch(self, batch_id: str, data: Dict) -> bool:
        """Update import batch status"""
        try:
            self.supabase.table('import_batches')\
                .update(data)\
                .eq('id', batch_id)\
                .execute()
            return True
        except Exception as e:
            logger.error(f"Import batch update error: {e}")
            return False
    
    def get_brands(self) -> List[Dict]:
        """Get all active brands with caching"""
        cache_key = "brands:active"
        
        if self.redis_client:
            cached = self.cache_get(cache_key)
            if cached:
                return cached
        
        try:
            result = self.supabase.table('brands')\
                .select("*")\
                .eq('is_active', True)\
                .order('name')\
                .execute()
            
            if result.data and self.redis_client:
                self.cache_set(cache_key, result.data, ttl=3600)  # 1 hour cache
            
            return result.data
        except Exception as e:
            logger.error(f"Brands fetch error: {e}")
            return []
    
    def vector_search(self, table: str, embedding: List[float], limit: int = 10) -> List[Dict]:
        """Perform vector similarity search using pgvector"""
        try:
            # Using Supabase's RPC for vector search
            result = self.supabase.rpc(
                'search_products',
                {
                    'query_embedding': embedding,
                    'match_count': limit
                }
            ).execute()
            return result.data
        except Exception as e:
            logger.error(f"Vector search error: {e}")
            return []
    
    # Redis Methods
    def cache_get(self, key: str) -> Optional[Any]:
        """Get value from Redis cache"""
        if not self.redis_client:
            return None
        
        try:
            value = self.redis_client.get(key)
            return json.loads(value) if value else None
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None
    
    def cache_set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set value in Redis cache with TTL"""
        if not self.redis_client:
            return False
        
        try:
            self.redis_client.setex(
                key,
                ttl,
                json.dumps(value)
            )
            return True
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            return False
    
    def cache_delete(self, key: str) -> bool:
        """Delete key from Redis cache"""
        if not self.redis_client:
            return False
        
        try:
            self.redis_client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            return False
    
    # Optimized cache methods for large dataset
    
    def cache_product_batch(self, products: List[Dict], ttl: int = 3600) -> int:
        """Cache multiple products efficiently"""
        if not self.redis_client:
            return 0
        
        cached_count = 0
        pipeline = self.redis_client.pipeline()
        
        for product in products:
            if product.get('barcode'):
                key = f"product:barcode:{product['barcode']}"
                pipeline.setex(key, ttl, json.dumps(product))
                cached_count += 1
            
            if product.get('id'):
                key = f"product:id:{product['id']}"
                pipeline.setex(key, ttl, json.dumps(product))
                cached_count += 1
        
        try:
            pipeline.execute()
            return cached_count
        except Exception as e:
            logger.error(f"Batch cache error: {e}")
            return 0
    
    def clear_product_cache(self) -> int:
        """Clear all product cache entries"""
        if not self.redis_client:
            return 0
        
        try:
            keys = []
            for key in self.redis_client.scan_iter("product:*"):
                keys.append(key)
            
            if keys:
                deleted = self.redis_client.delete(*keys)
                logger.info(f"Cleared {deleted} product cache entries")
                return deleted
            return 0
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return 0
    
    def refresh_materialized_view(self) -> bool:
        """Refresh the product search materialized view"""
        try:
            self.supabase.rpc('refresh_product_search_view').execute()
            logger.info("Product search view refreshed")
            return True
        except Exception as e:
            logger.error(f"Materialized view refresh error: {e}")
            return False
    
    # Analytics methods for monitoring
    
    def get_product_stats(self) -> Dict:
        """Get product database statistics"""
        try:
            stats = {}
            
            # Total products
            total = self.supabase.table('products')\
                .select('id', count='exact')\
                .execute()
            stats['total_products'] = total.count
            
            # Active products
            active = self.supabase.table('products')\
                .select('id', count='exact')\
                .eq('is_active', True)\
                .execute()
            stats['active_products'] = active.count
            
            # Products by brand
            brands = self.supabase.table('products')\
                .select('brand')\
                .execute()
            
            brand_counts = {}
            for p in brands.data:
                brand = p.get('brand', 'Unknown')
                brand_counts[brand] = brand_counts.get(brand, 0) + 1
            
            stats['top_brands'] = sorted(
                brand_counts.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:10]
            
            return stats
        except Exception as e:
            logger.error(f"Stats fetch error: {e}")
            return {}

    async def close(self):
        """Close database connections"""
        # Close Redis if connected
        if hasattr(self, 'redis_client') and self.redis_client:
            await self.redis_client.close()
        # Supabase client doesn't need explicit closing
        logger.info("Database connections closed")

# Enhanced global database instance
db = DatabaseConnection()

# Helper functions for common operations

async def import_products_async(products: List[Dict], batch_size: int = 500):
    """Async product import for better performance"""
    total = len(products)
    logger.info(f"Starting async import of {total} products")
    
    # Create import batch
    batch = db.create_import_batch(
        file_name="Milpitas_New.xlsx",
        total_rows=total
    )
    batch_id = batch['id'] if batch else None
    
    # Process in chunks
    inserted = 0
    errors = []
    
    for i in range(0, total, batch_size):
        chunk = products[i:i + batch_size]
        count, chunk_errors = db.bulk_insert('products', chunk)
        inserted += count
        errors.extend(chunk_errors)
        
        # Update progress
        if batch_id:
            db.update_import_batch(batch_id, {
                'imported_rows': inserted,
                'failed_rows': len(errors)
            })
        
        # Log progress
        progress = (i + len(chunk)) / total * 100
        logger.info(f"Import progress: {progress:.1f}% ({inserted}/{total})")
        
        # Small delay to prevent overwhelming the database
        await asyncio.sleep(0.1)
    
    # Final update
    if batch_id:
        db.update_import_batch(batch_id, {
            'status': 'completed' if not errors else 'completed_with_errors',
            'imported_rows': inserted,
            'failed_rows': len(errors),
            'error_log': errors[:100],  # Store first 100 errors
            'completed_at': datetime.now().isoformat()
        })
    
    # Refresh materialized view
    db.refresh_materialized_view()
    
    return inserted, errors