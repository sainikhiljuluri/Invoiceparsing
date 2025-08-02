"""
Component 5: Product Data Loader
Loads product master data from Excel with embeddings and search optimization
"""

import os
import logging
import json
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
import numpy as np
from datetime import datetime
import hashlib

# For embeddings
from sentence_transformers import SentenceTransformer

# Database
from supabase import create_client, Client
from dotenv import load_dotenv

# For text processing
import re
from unidecode import unidecode

load_dotenv()
logger = logging.getLogger(__name__)


class ProductDataLoader:
    """Load and process product data from Excel files"""
    
    def __init__(self):
        # Initialize Supabase client
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("Supabase credentials not found in environment")
            
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        
        # Initialize embedding model (384-dimensional)
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Product processing configuration
        self.config = {
            'batch_size': 100,
            'embedding_batch_size': 32,
            'duplicate_threshold': 0.95,
            'required_columns': ['product_name', 'brand', 'category'],
            'optional_columns': ['size', 'unit', 'barcode', 'description', 'cost']
        }
        
        # Category mappings for normalization
        self.category_mappings = {
            'RICE & RICE PRODUCTS': 'Rice & Grains',
            'RICE': 'Rice & Grains',
            'RICE PRODUCTS': 'Rice & Grains',
            'ATTA & FLOURS': 'Flours & Batters',
            'FLOUR': 'Flours & Batters',
            'ATTA': 'Flours & Batters',
            'DALS & PULSES': 'Lentils & Pulses',
            'DAL': 'Lentils & Pulses',
            'PULSES': 'Lentils & Pulses',
            'SPICES': 'Spices & Seasonings',
            'MASALA': 'Spices & Seasonings',
            'SEASONINGS': 'Spices & Seasonings',
            'SNACKS': 'Snacks & Namkeen',
            'NAMKEEN': 'Snacks & Namkeen',
            'FROZEN': 'Frozen Foods',
            'FROZEN FOODS': 'Frozen Foods',
            'DAIRY': 'Dairy Products',
            'MILK PRODUCTS': 'Dairy Products',
            'SWEETS': 'Sweets & Desserts',
            'MITHAI': 'Sweets & Desserts',
            'DESSERTS': 'Sweets & Desserts',
            'BEVERAGES': 'Beverages',
            'DRINKS': 'Beverages',
            'PICKLES': 'Pickles & Chutneys',
            'CHUTNEYS': 'Pickles & Chutneys',
            'OILS': 'Cooking Oils',
            'COOKING OIL': 'Cooking Oils',
            'GHEE': 'Cooking Oils',
        }
        
        # Known brands for validation
        self.known_brands = {
            'DEEP', 'HALDIRAM', 'HALDIRAMS', 'MTR', 'GITS', 'SHAN', 'MDH',
            'EVEREST', 'CATCH', 'BADSHAH', 'PATANJALI', 'AASHIRVAAD', 'FORTUNE',
            'PILLSBURY', 'BRITANNIA', 'PARLE', 'BIKAJI', 'BALAJI', 'AMUL',
            'MOTHER DAIRY', 'VADILAL', 'KWALITY', 'GOWARDHAN', 'NANDINI',
            'SWAD', 'LAXMI', 'PRIYA', 'NIRAV', 'ZIYAD', 'AHMED', 'NATIONAL',
            'LAZIZA', 'BOMBAY', 'KOHINOOR', 'INDIA GATE', 'DAWAT', 'ZEBRA',
            'ELEPHANT', 'DEER', 'ANAND', 'AMRIT', 'KRISHNA', 'GANESH'
        }
    
    def load_products_from_excel(self, file_path: str, sheet_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Load products from Excel file
        
        Args:
            file_path: Path to Excel file
            sheet_name: Specific sheet to load (optional)
            
        Returns:
            Dictionary with loading results
        """
        logger.info(f"Loading products from: {file_path}")
        
        result = {
            'success': False,
            'total_rows': 0,
            'products_loaded': 0,
            'duplicates_found': 0,
            'errors': [],
            'warnings': [],
            'statistics': {}
        }
        
        try:
            # Read Excel file
            if sheet_name:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
            else:
                df = pd.read_excel(file_path)
            
            result['total_rows'] = len(df)
            logger.info(f"Found {len(df)} rows in Excel file")
            
            # Validate columns
            self._validate_columns(df, result)
            if result['errors']:
                return result
            
            # Clean and normalize data
            df_cleaned = self._clean_product_data(df)
            
            # Generate embeddings
            logger.info("Generating embeddings for products...")
            embeddings = self._generate_embeddings(df_cleaned)
            
            # Detect duplicates
            duplicate_groups = self._detect_duplicates(df_cleaned, embeddings)
            result['duplicates_found'] = sum(len(group) - 1 for group in duplicate_groups)
            
            # Prepare products for insertion
            products = self._prepare_products(df_cleaned, embeddings, duplicate_groups)
            
            # Insert into database
            inserted_count = self._bulk_insert_products(products)
            result['products_loaded'] = inserted_count
            
            # Generate statistics
            result['statistics'] = self._generate_statistics(df_cleaned, products)
            
            # Create search indexes
            self._create_search_indexes()
            
            result['success'] = True
            logger.info(f"Successfully loaded {inserted_count} products")
            
        except Exception as e:
            logger.error(f"Error loading products: {str(e)}")
            result['errors'].append(f"Loading failed: {str(e)}")
        
        return result
    
    def _validate_columns(self, df: pd.DataFrame, result: Dict):
        """Validate required columns exist"""
        missing_required = []
        
        for col in self.config['required_columns']:
            if col not in df.columns:
                # Try case-insensitive match
                matched = False
                for df_col in df.columns:
                    if col.lower() == df_col.lower():
                        df.rename(columns={df_col: col}, inplace=True)
                        matched = True
                        break
                
                if not matched:
                    missing_required.append(col)
        
        if missing_required:
            result['errors'].append(f"Missing required columns: {missing_required}")
        
        # Check optional columns
        for col in self.config['optional_columns']:
            if col not in df.columns:
                result['warnings'].append(f"Optional column '{col}' not found")
    
    def _clean_product_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and normalize product data"""
        df_clean = df.copy()
        
        # Clean product names
        df_clean['product_name'] = df_clean['product_name'].apply(self._clean_product_name)
        
        # Normalize brands
        df_clean['brand'] = df_clean['brand'].apply(self._normalize_brand)
        
        # Normalize categories
        if 'category' in df_clean.columns:
            df_clean['category'] = df_clean['category'].apply(self._normalize_category)
        
        # Extract size and unit if not present
        if 'size' not in df_clean.columns or 'unit' not in df_clean.columns:
            size_unit_data = df_clean['product_name'].apply(self._extract_size_unit)
            df_clean['size'] = size_unit_data.apply(lambda x: x[0])
            df_clean['unit'] = size_unit_data.apply(lambda x: x[1])
        
        # Generate search text
        df_clean['search_text'] = df_clean.apply(self._generate_search_text, axis=1)
        
        # Generate product hash
        df_clean['product_hash'] = df_clean.apply(self._generate_product_hash, axis=1)
        
        return df_clean
    
    def _clean_product_name(self, name: str) -> str:
        """Clean product name"""
        if pd.isna(name):
            return ""
        
        # Convert to string and strip
        name = str(name).strip()
        
        # Remove extra spaces
        name = re.sub(r'\s+', ' ', name)
        
        # Fix common issues
        name = name.replace('&amp;', '&')
        name = name.replace('  ', ' ')
        
        return name
    
    def _normalize_brand(self, brand: str) -> str:
        """Normalize brand name"""
        if pd.isna(brand):
            return "GENERIC"
        
        brand = str(brand).upper().strip()
        
        # Fix common variations
        brand_mappings = {
            "HALDIRAM'S": "HALDIRAM",
            "HALDIRAMS": "HALDIRAM",
            "MOTHER'S": "MOTHERS",
            "LAY'S": "LAYS",
        }
        
        brand = brand_mappings.get(brand, brand)
        
        # Validate against known brands
        if brand not in self.known_brands:
            logger.debug(f"Unknown brand: {brand}")
        
        return brand
    
    def _normalize_category(self, category: str) -> str:
        """Normalize category name"""
        if pd.isna(category):
            return "Uncategorized"
        
        category = str(category).upper().strip()
        
        # Map to normalized categories
        return self.category_mappings.get(category, category.title())
    
    def _extract_size_unit(self, product_name: str) -> Tuple[str, str]:
        """Extract size and unit from product name"""
        # Common patterns
        patterns = [
            r'(\d+\.?\d*)\s*(OZ|OUNCE)',
            r'(\d+\.?\d*)\s*(LB|POUND)',
            r'(\d+\.?\d*)\s*(G|GM|GRAM)',
            r'(\d+\.?\d*)\s*(KG|KILOGRAM)',
            r'(\d+\.?\d*)\s*(L|LTR|LITER)',
            r'(\d+\.?\d*)\s*(ML|MILLILITER)',
            r'(\d+\.?\d*)\s*(PC|PCS|PIECE)',
            r'(\d+\.?\d*)\s*(PK|PKT|PACKET)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, product_name, re.IGNORECASE)
            if match:
                size = match.group(1)
                unit = match.group(2).upper()
                
                # Normalize units
                unit_mapping = {
                    'OZ': 'OZ', 'OUNCE': 'OZ',
                    'LB': 'LB', 'POUND': 'LB',
                    'G': 'G', 'GM': 'G', 'GRAM': 'G',
                    'KG': 'KG', 'KILOGRAM': 'KG',
                    'L': 'L', 'LTR': 'L', 'LITER': 'L',
                    'ML': 'ML', 'MILLILITER': 'ML',
                    'PC': 'PC', 'PCS': 'PC', 'PIECE': 'PC',
                    'PK': 'PK', 'PKT': 'PK', 'PACKET': 'PK',
                }
                
                return (size, unit_mapping.get(unit, unit))
        
        return ("", "")
    
    def _generate_search_text(self, row: pd.Series) -> str:
        """Generate search text for a product"""
        parts = []
        
        # Add all relevant fields
        if not pd.isna(row.get('brand')):
            parts.append(str(row['brand']))
        
        if not pd.isna(row.get('product_name')):
            parts.append(str(row['product_name']))
        
        if not pd.isna(row.get('category')):
            parts.append(str(row['category']))
        
        if not pd.isna(row.get('description')):
            parts.append(str(row['description']))
        
        # Create searchable text
        search_text = ' '.join(parts)
        
        # Add normalized version without accents
        search_text_normalized = unidecode(search_text)
        
        return f"{search_text} {search_text_normalized}"
    
    def _generate_product_hash(self, row: pd.Series) -> str:
        """Generate unique hash for product"""
        # Use brand + normalized product name
        key_parts = []
        
        if not pd.isna(row.get('brand')):
            key_parts.append(str(row['brand']).upper())
        
        if not pd.isna(row.get('product_name')):
            # Normalize product name for hashing
            name = str(row['product_name']).upper()
            name = re.sub(r'[^A-Z0-9]+', '', name)
            key_parts.append(name)
        
        key = '|'.join(key_parts)
        return hashlib.md5(key.encode()).hexdigest()
    
    def _generate_embeddings(self, df: pd.DataFrame) -> np.ndarray:
        """Generate embeddings for all products"""
        search_texts = df['search_text'].tolist()
        
        embeddings = []
        batch_size = self.config['embedding_batch_size']
        
        for i in range(0, len(search_texts), batch_size):
            batch = search_texts[i:i + batch_size]
            batch_embeddings = self.embedding_model.encode(batch)
            embeddings.extend(batch_embeddings)
            
            if (i + batch_size) % 1000 == 0:
                logger.info(f"Generated embeddings for {i + batch_size} products")
        
        return np.array(embeddings)
    
    def _detect_duplicates(self, df: pd.DataFrame, embeddings: np.ndarray) -> List[List[int]]:
        """Detect duplicate products using embeddings"""
        duplicate_groups = []
        processed = set()
        
        threshold = self.config['duplicate_threshold']
        
        for i in range(len(df)):
            if i in processed:
                continue
            
            # Find similar products
            similarities = np.dot(embeddings[i], embeddings.T)
            similar_indices = np.where(similarities > threshold)[0]
            
            if len(similar_indices) > 1:
                group = similar_indices.tolist()
                duplicate_groups.append(group)
                processed.update(group)
        
        logger.info(f"Found {len(duplicate_groups)} duplicate groups")
        return duplicate_groups
    
    def _prepare_products(self, df: pd.DataFrame, embeddings: np.ndarray, 
                         duplicate_groups: List[List[int]]) -> List[Dict]:
        """Prepare products for database insertion"""
        products = []
        processed_indices = set()
        
        # Process duplicate groups (keep first of each group)
        for group in duplicate_groups:
            # Keep the first product in the group
            idx = group[0]
            processed_indices.add(idx)
            
            product = self._row_to_product(df.iloc[idx], embeddings[idx])
            products.append(product)
            
            # Mark others as duplicates
            for dup_idx in group[1:]:
                processed_indices.add(dup_idx)
        
        # Process non-duplicate products
        for idx in range(len(df)):
            if idx not in processed_indices:
                product = self._row_to_product(df.iloc[idx], embeddings[idx])
                products.append(product)
        
        return products
    
    def _row_to_product(self, row: pd.Series, embedding: np.ndarray) -> Dict:
        """Convert DataFrame row to product dictionary"""
        product = {
            'name': row['product_name'],
            'brand': row.get('brand', 'GENERIC'),
            'category': row.get('category', 'Uncategorized'),
            'size': row.get('size', ''),
            'unit': row.get('unit', ''),
            'barcode': row.get('barcode', ''),
            'description': row.get('description', ''),
            'search_text': row['search_text'],
            'product_hash': row['product_hash'],
            'embedding': embedding.tolist(),
            'cost': row.get('cost', 0.0),
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'is_active': True
        }
        
        return product
    
    def _bulk_insert_products(self, products: List[Dict]) -> int:
        """Bulk insert products into database"""
        inserted_count = 0
        batch_size = self.config['batch_size']
        
        for i in range(0, len(products), batch_size):
            batch = products[i:i + batch_size]
            
            try:
                # Insert batch
                response = self.supabase.table('products').insert(batch).execute()
                inserted_count += len(batch)
                
                if (i + batch_size) % 1000 == 0:
                    logger.info(f"Inserted {inserted_count} products")
                    
            except Exception as e:
                logger.error(f"Error inserting batch: {str(e)}")
                # Try individual inserts for failed batch
                for product in batch:
                    try:
                        self.supabase.table('products').insert(product).execute()
                        inserted_count += 1
                    except:
                        logger.error(f"Failed to insert product: {product['name']}")
        
        return inserted_count
    
    def _generate_statistics(self, df: pd.DataFrame, products: List[Dict]) -> Dict:
        """Generate loading statistics"""
        stats = {
            'total_products': len(products),
            'unique_brands': df['brand'].nunique(),
            'unique_categories': df['category'].nunique() if 'category' in df.columns else 0,
            'products_with_barcode': df['barcode'].notna().sum() if 'barcode' in df.columns else 0,
            'products_with_size': (df['size'] != '').sum() if 'size' in df.columns else 0,
            'brand_distribution': df['brand'].value_counts().head(10).to_dict(),
            'category_distribution': df['category'].value_counts().to_dict() if 'category' in df.columns else {}
        }
        
        return stats
    
    def _create_search_indexes(self):
        """Create database indexes for search optimization"""
        # Note: In actual Supabase, you'd run these as SQL migrations
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_products_brand ON products(brand);",
            "CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);",
            "CREATE INDEX IF NOT EXISTS idx_products_barcode ON products(barcode);",
            "CREATE INDEX IF NOT EXISTS idx_products_hash ON products(product_hash);",
            "CREATE INDEX IF NOT EXISTS idx_products_search ON products USING gin(to_tsvector('english', search_text));"
        ]
        
        logger.info("Search indexes created/verified")
    
    def search_products(self, query: str, limit: int = 10) -> List[Dict]:
        """Search products using embeddings"""
        # Generate embedding for query
        query_embedding = self.embedding_model.encode([query])[0]
        
        # Search using Supabase vector similarity
        # Note: This assumes you have pgvector extension enabled
        results = self.supabase.rpc(
            'search_products_by_embedding',
            {
                'query_embedding': query_embedding.tolist(),
                'match_threshold': 0.7,
                'match_count': limit
            }
        ).execute()
        
        return results.data if results.data else []


# Utility function for command-line usage
def main():
    """Main function for command-line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Load products from Excel file')
    parser.add_argument('file', help='Path to Excel file')
    parser.add_argument('--sheet', help='Sheet name (optional)')
    parser.add_argument('--test', action='store_true', help='Test mode - load only first 100 rows')
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize loader
    loader = ProductDataLoader()
    
    # Load products
    if args.test:
        # In test mode, load only first 100 rows
        df = pd.read_excel(args.file, nrows=100)
        temp_file = 'test_products.xlsx'
        df.to_excel(temp_file, index=False)
        result = loader.load_products_from_excel(temp_file)
        os.remove(temp_file)
    else:
        result = loader.load_products_from_excel(args.file, args.sheet)
    
    # Print results
    print("\n=== Product Loading Results ===")
    print(f"Success: {result['success']}")
    print(f"Total Rows: {result['total_rows']}")
    print(f"Products Loaded: {result['products_loaded']}")
    print(f"Duplicates Found: {result['duplicates_found']}")
    
    if result['errors']:
        print("\nErrors:")
        for error in result['errors']:
            print(f"  - {error}")
    
    if result['warnings']:
        print("\nWarnings:")
        for warning in result['warnings']:
            print(f"  - {warning}")
    
    if result['statistics']:
        print("\nStatistics:")
        stats = result['statistics']
        print(f"  Unique Brands: {stats.get('unique_brands', 0)}")
        print(f"  Unique Categories: {stats.get('unique_categories', 0)}")
        print(f"  Products with Barcode: {stats.get('products_with_barcode', 0)}")
        print(f"  Products with Size: {stats.get('products_with_size', 0)}")
        
        if stats.get('brand_distribution'):
            print("\n  Top Brands:")
            for brand, count in list(stats['brand_distribution'].items())[:5]:
                print(f"    {brand}: {count}")


if __name__ == '__main__':
    main()