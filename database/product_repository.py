"""
Product repository for database operations
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import numpy as np
from supabase import Client

logger = logging.getLogger(__name__)


class ProductRepository:
    """Handle all product-related database operations"""
    
    def __init__(self, supabase_client: Client):
        self.client = supabase_client
        
    def search_by_exact_name(self, product_name: str) -> Optional[Dict]:
        """Search for exact product name match"""
        try:
            response = self.client.table('products').select('*').ilike(
                'name', product_name
            ).execute()
            
            if response.data:
                return response.data[0]
            return None
            
        except Exception as e:
            logger.error(f"Error searching by exact name: {e}")
            return None
    
    def search_by_barcode(self, barcode: str) -> Optional[Dict]:
        """Search for product by barcode"""
        try:
            response = self.client.table('products').select('*').eq(
                'barcode', barcode
            ).execute()
            
            if response.data:
                return response.data[0]
            return None
            
        except Exception as e:
            logger.error(f"Error searching by barcode: {e}")
            return None
    
    def search_by_brand_and_keywords(self, brand: str, keywords: List[str]) -> List[Dict]:
        """Search products by brand and keywords"""
        try:
            # Start with brand filter
            query = self.client.table('products').select('*')
            
            if brand:
                query = query.ilike('brand', f'%{brand}%')
            
            # Add keyword filters
            for keyword in keywords[:3]:  # Limit to first 3 keywords
                query = query.ilike('name', f'%{keyword}%')
            
            response = query.limit(10).execute()
            return response.data or []
            
        except Exception as e:
            logger.error(f"Error searching by brand and keywords: {e}")
            return []
    
    def search_by_vector_similarity(self, embedding: List[float], threshold: float = 0.7) -> List[Dict]:
        """Search products by vector similarity"""
        try:
            # Convert embedding to proper format
            embedding_str = '[' + ','.join(map(str, embedding)) + ']'
            
            # Use Supabase vector similarity search
            response = self.client.rpc(
                'match_products_by_embedding',
                {
                    'query_embedding': embedding_str,
                    'match_threshold': threshold,
                    'match_count': 10
                }
            ).execute()
            
            return response.data or []
            
        except Exception as e:
            logger.error(f"Error in vector similarity search: {e}")
            return []
    
    def get_learned_mappings(self, invoice_product_name: str) -> Optional[Dict]:
        """Get previously learned product mappings"""
        try:
            response = self.client.table('product_mappings').select(
                '*, products(*)'
            ).eq(
                'invoice_product_name', invoice_product_name
            ).eq(
                'is_active', True
            ).order(
                'confidence_score', desc=True
            ).limit(1).execute()
            
            if response.data:
                mapping = response.data[0]
                return {
                    'product': mapping['products'],
                    'confidence': mapping['confidence_score'],
                    'mapping_id': mapping['id']
                }
            return None
            
        except Exception as e:
            logger.error(f"Error getting learned mappings: {e}")
            return None
    
    def create_product_mapping(self, mapping_data: Dict) -> bool:
        """Create a new product mapping"""
        try:
            response = self.client.table('product_mappings').insert({
                'invoice_product_name': mapping_data['invoice_product_name'],
                'product_id': mapping_data['product_id'],
                'vendor_id': mapping_data.get('vendor_id'),
                'confidence_score': mapping_data['confidence_score'],
                'match_strategy': mapping_data['match_strategy'],
                'is_active': True,
                'created_by': mapping_data.get('created_by', 'system'),
                'created_at': datetime.now().isoformat()
            }).execute()
            
            return bool(response.data)
            
        except Exception as e:
            logger.error(f"Error creating product mapping: {e}")
            return False
    
    def get_all_products_for_fuzzy_match(self) -> List[Dict]:
        """Get all products for fuzzy matching"""
        try:
            response = self.client.table('products').select(
                'id, name, brand, size, category'
            ).execute()
            
            return response.data or []
            
        except Exception as e:
            logger.error(f"Error getting products for fuzzy match: {e}")
            return []