"""
Component 5: Product Data Loader - Final Version
Maps Excel Price to price column and Cost to cost column
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
import re
from tqdm import tqdm
import asyncio
import uuid
from sentence_transformers import SentenceTransformer
from supabase import create_client, Client
import os
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProductDataLoader:
    def __init__(self):
        self.supabase = create_client(
            os.getenv('SUPABASE_URL'),
            os.getenv('SUPABASE_SERVICE_KEY')
        )
        
        logger.info("Loading embedding model...")
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        self.known_brands = [
            'DEEP', 'HALDIRAM', "HALDIRAM'S", 'ANAND', 'DECCAN', 
            'VADILAL', 'BRITANNIA', 'PARLE', 'MTR', 'GITS', 
            'SWAD', 'LAXMI', 'SHAN', 'MDH', 'BROOKE BOND',
            'PG TIPS', 'TEA INDIA', 'LIPTON', 'TETLEY', 'TWININGS',
            'AMUL', 'MOTHER DAIRY', 'NESTLE', 'CADBURY', 'BIKAJI',
            'BALAJI', 'KURKURE', "LAY'S", 'UNCLE CHIPS', 'BINGO',
            'TATA', 'RAJDHANI', 'FORTUNE', 'PATANJALI', 'DABUR',
            'EVEREST', 'CATCH', 'PRIYA', 'AASHIRVAAD', 'PILLSBURY'
        ]
        
        self.batch_size = 100
        self.import_batch_id = str(uuid.uuid4())
        
        self.stats = {
            'total_records': 0,
            'successful_imports': 0,
            'failed_imports': 0,
            'duplicates_updated': 0,
            'products_with_cost': 0,
            'products_with_price': 0,
            'brands_found': set()
        }
    
    def load_excel_file(self, file_path: str) -> pd.DataFrame:
        logger.info(f"Loading Excel file: {file_path}")
        
        df = pd.read_excel(file_path)
        logger.info(f"Loaded {len(df)} products")
        
        # Add row numbers
        df['excel_row_number'] = df.index + 2
        
        # Clean data
        df = self._clean_dataframe(df)
        self.stats['total_records'] = len(df)
        
        # Count products with price and cost
        self.stats['products_with_price'] = df['Price'].notna().sum()
        if 'Cost' in df.columns:
            self.stats['products_with_cost'] = df['Cost'].notna().sum()
        
        logger.info(f"Products with Price: {self.stats['products_with_price']}")
        logger.info(f"Products with Cost: {self.stats['products_with_cost']}")
        
        return df
    
    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        # Remove duplicates
        initial_count = len(df)
        df = df.drop_duplicates(subset=['Barcode'], keep='first')
        if initial_count > len(df):
            logger.info(f"Removed {initial_count - len(df)} duplicate barcodes")
        
        # Clean numeric fields
        for field in ['Price', 'Cost']:
            if field in df.columns:
                df[field] = pd.to_numeric(df[field], errors='coerce')
                # Don't treat 0 as null - it might be a valid price
        
        # Clean string fields
        string_cols = ['Product Name', 'Product Description', 'Product Category', 
                      'Product Subcategory', 'Barcode']
        
        for col in string_cols:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip()
                df[col] = df[col].replace('nan', '')
        
        # Handle Active column
        if 'Active' in df.columns:
            df['is_active'] = df['Active'].str.lower() == 'yes'
        else:
            df['is_active'] = True
        
        return df
    
    def extract_brand(self, product_name: str) -> str:
        if not product_name:
            return ''
        
        product_upper = product_name.upper()
        
        # Check known brands
        for brand in self.known_brands:
            brand_upper = brand.upper()
            if product_upper.startswith(brand_upper + ' ') or product_upper == brand_upper:
                self.stats['brands_found'].add(brand)
                return brand
        
        # Extract first word as brand
        words = product_name.split()
        if words and words[0][0].isupper() and len(words[0]) > 2:
            self.stats['brands_found'].add(words[0])
            return words[0]
        
        return ''
    
    def extract_pack_info(self, product_name: str) -> Dict[str, Any]:
        result = {
            'pack_size': '',
            'units_per_case': None
        }
        
        # Extract pack size
        size_pattern = r'(\d+(?:\.\d+)?)\s*(OZ|GM|G|KG|LB|L|ML|Gm|Oz|gm|oz)\b'
        size_match = re.search(size_pattern, product_name, re.IGNORECASE)
        if size_match:
            size = size_match.group(1)
            unit = size_match.group(2).upper()
            unit_map = {'G': 'GM', 'GM': 'GM', 'OZ': 'OZ'}
            unit = unit_map.get(unit, unit)
            result['pack_size'] = f"{size} {unit}"
        
        # Extract units per case
        units_pattern = r'\((\d+)\)'
        units_match = re.search(units_pattern, product_name)
        if units_match:
            result['units_per_case'] = int(units_match.group(1))
        
        return result
    
    def normalize_product_name(self, name: str) -> str:
        if not name:
            return ''
        
        # Uppercase and remove special chars
        normalized = re.sub(r'[^A-Z0-9\s]', ' ', name.upper())
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Expand abbreviations
        abbreviations = {
            r'\bGM\b': 'GRAM',
            r'\bKG\b': 'KILOGRAM',
            r'\bLB\b': 'POUND',
            r'\bOZ\b': 'OUNCE'
        }
        
        for abbr, expansion in abbreviations.items():
            normalized = re.sub(abbr, expansion, normalized)
        
        return normalized.strip()
    
    def prepare_product_data(self, row: pd.Series) -> Dict[str, Any]:
        product_name = row.get('Product Name', '')
        
        # Extract brand and pack info
        brand = self.extract_brand(product_name)
        pack_info = self.extract_pack_info(product_name)
        
        # Create search text
        search_parts = [
            product_name,
            row.get('Product Description', ''),
            brand,
            row.get('Product Category', ''),
            row.get('Product Subcategory', ''),
            str(row.get('Barcode', '')),
            pack_info['pack_size']
        ]
        search_text = ' '.join(filter(None, search_parts))
        
        # IMPORTANT: Correct mapping
        # Excel "Price" → database "price" (selling price)
        # Excel "Cost" → database "cost" (supplier cost)
        product = {
            'name': product_name,
            'barcode': str(row['Barcode']),
            'brand': brand,
            'category': row.get('Product Category', ''),
            'sub_category': row.get('Product Subcategory', ''),
            
            # PRICE MAPPING - THIS IS THE KEY PART!
            'price': float(row['Price']) if pd.notna(row.get('Price')) else None,  # Selling price
            'cost': float(row['Cost']) if pd.notna(row.get('Cost')) else None,    # Supplier cost
            
            'pack_size': pack_info['pack_size'],
            'units_per_case': pack_info['units_per_case'],
            'search_text': search_text,
            'normalized_name': self.normalize_product_name(product_name),
            'is_active': row.get('is_active', True),
            'is_discontinued': False,
            'excel_row_number': row['excel_row_number'],
            'import_batch_id': self.import_batch_id,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            
            # Default values
            'currency': 'USD',
            'sku': None,
            'product_code': None,
            'case_weight': None,
            'case_cost': None,
            'supplier_name': None,
            'supplier_code': None,
            'origin_country': None,
            'min_order_quantity': None,
            'lead_time_days': None,
            'vendor_id': None,
            'last_invoice_number': None,
            'last_update_date': None
        }
        
        # Calculate case_cost if we have cost and units
        if product['cost'] and product['units_per_case']:
            product['case_cost'] = round(product['cost'] * product['units_per_case'], 2)
        
        return product
    
    def generate_embeddings_for_products(self, products: List[Dict]) -> np.ndarray:
        texts = [product.get('search_text', '') for product in products]
        
        embeddings = self.embedding_model.encode(
            texts,
            batch_size=32,
            show_progress_bar=False,
            convert_to_numpy=True
        )
        
        return embeddings
    
    async def process_batch(self, batch_df: pd.DataFrame, batch_num: int):
        products = []
        
        # Prepare products
        for _, row in batch_df.iterrows():
            try:
                product = self.prepare_product_data(row)
                products.append(product)
            except Exception as e:
                logger.error(f"Error preparing product {row.get('Barcode')}: {e}")
                self.stats['failed_imports'] += 1
        
        # Generate embeddings
        try:
            embeddings = self.generate_embeddings_for_products(products)
            for i, product in enumerate(products):
                product['embedding'] = embeddings[i].tolist()
        except Exception as e:
            logger.warning(f"Could not generate embeddings: {e}")
        
        # Upsert products
        for product in products:
            try:
                # Check if exists
                existing = self.supabase.table('products')\
                    .select('id, cost, price')\
                    .eq('barcode', product['barcode'])\
                    .execute()
                
                if existing.data:
                    # Update existing
                    product_id = existing.data[0]['id']
                    
                    # Preserve vendor info
                    preserve_fields = ['vendor_id', 'last_invoice_number', 
                                     'last_update_date', 'created_at']
                    
                    update_data = {k: v for k, v in product.items() 
                                 if k not in preserve_fields and k != 'id'}
                    update_data['updated_at'] = datetime.now().isoformat()
                    
                    self.supabase.table('products')\
                        .update(update_data)\
                        .eq('id', product_id)\
                        .execute()
                    
                    self.stats['duplicates_updated'] += 1
                else:
                    # Insert new
                    self.supabase.table('products').insert(product).execute()
                    self.stats['successful_imports'] += 1
                    
            except Exception as e:
                logger.error(f"Error processing product {product['barcode']}: {e}")
                self.stats['failed_imports'] += 1
    
    async def load_products(self, file_path: str):
        start_time = datetime.now()
        
        try:
            # Load Excel
            df = self.load_excel_file(file_path)
            
            # Process in batches
            total_batches = (len(df) + self.batch_size - 1) // self.batch_size
            
            print(f"\nProcessing {len(df)} products in {total_batches} batches...")
            print(f"Import batch ID: {self.import_batch_id}")
            
            for i in tqdm(range(0, len(df), self.batch_size), desc="Loading products"):
                batch_df = df.iloc[i:i + self.batch_size]
                batch_num = i // self.batch_size + 1
                await self.process_batch(batch_df, batch_num)
            
            self._print_summary(start_time)
            
        except Exception as e:
            logger.error(f"Import failed: {e}")
            raise
    
    def _print_summary(self, start_time: datetime):
        duration = datetime.now() - start_time
        
        print("\n" + "="*60)
        print("PRODUCT IMPORT SUMMARY")
        print("="*60)
        print(f"Import Batch: {self.import_batch_id}")
        print(f"Total Records: {self.stats['total_records']:,}")
        print(f"New Products Added: {self.stats['successful_imports']:,}")
        print(f"Existing Products Updated: {self.stats['duplicates_updated']:,}")
        print(f"Failed: {self.stats['failed_imports']:,}")
        print(f"Products with Price (selling): {self.stats['products_with_price']:,}")
        print(f"Products with Cost (supplier): {self.stats['products_with_cost']:,}")
        print(f"Unique Brands Found: {len(self.stats['brands_found'])}")
        print(f"Duration: {duration}")
        print("="*60)
        
        print("\n📊 Verification Queries:")
        print("-- Check products with both price and cost:")
        print("SELECT name, price, cost, (price - cost) as margin")
        print("FROM products WHERE price IS NOT NULL AND cost IS NOT NULL LIMIT 10;")
        
        print("\n-- Check price distribution:")
        print("SELECT COUNT(*) as total,")
        print("  COUNT(price) as has_price,")
        print("  COUNT(cost) as has_cost,")
        print("  AVG(price) as avg_price,")
        print("  AVG(cost) as avg_cost")
        print("FROM products;")


async def main():
    loader = ProductDataLoader()
    await loader.load_products('data/Milpitas_New.xlsx')


if __name__ == "__main__":
    print("="*60)
    print("COMPONENT 5: PRODUCT DATA LOADER")
    print("="*60)
    print("Mapping Configuration:")
    print("  Excel 'Price' → Database 'price' (selling price)")
    print("  Excel 'Cost' → Database 'cost' (supplier cost)")
    print("="*60)
    
    response = input("\nReady to start import? (y/n): ")
    if response.lower() == 'y':
        asyncio.run(main())
    else:
        print("Import cancelled.")