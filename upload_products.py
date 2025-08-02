#!/usr/bin/env python3
"""
Product Upload Script
Uploads product data from various sources to the invoice parser system
"""

import sys
import os
import logging
import argparse
import json
import pandas as pd
from typing import Dict, Any, List, Optional
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.product_loader import ProductLoader
from parsers import get_parser_for_vendor
from services.pdf_extractor import PDFExtractor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ProductUploader:
    """Handles uploading products from various sources"""
    
    def __init__(self):
        self.loader = ProductLoader()
        self.pdf_extractor = PDFExtractor()
        
    def upload_from_pdf(self, pdf_path: str, vendor_key: str) -> Dict[str, Any]:
        """
        Upload products by parsing a PDF invoice
        
        Args:
            pdf_path: Path to PDF file
            vendor_key: Vendor identifier
            
        Returns:
            Upload results
        """
        try:
            logger.info(f"Processing PDF: {pdf_path} for vendor: {vendor_key}")
            
            # Get appropriate parser for vendor
            parser = get_parser_for_vendor(vendor_key)
            if not parser:
                return {
                    'success': False,
                    'error': f'No parser found for vendor: {vendor_key}',
                    'products_uploaded': 0
                }
            
            # Parse the invoice
            invoice_data = parser.parse_invoice(pdf_path)
            
            if not invoice_data.get('success'):
                return {
                    'success': False,
                    'error': 'Failed to parse PDF invoice',
                    'products_uploaded': 0
                }
            
            # Upload products
            result = self.loader.process_invoice_products(invoice_data, vendor_key)
            
            logger.info(f"Uploaded {result['products_processed']} products from PDF")
            return {
                'success': result['success'],
                'products_uploaded': result['products_processed'],
                'invoice_data': invoice_data,
                'message': result['message']
            }
            
        except Exception as e:
            logger.error(f"Error uploading from PDF: {e}")
            return {
                'success': False,
                'error': str(e),
                'products_uploaded': 0
            }
    
    def upload_from_json(self, json_path: str, vendor_key: str) -> Dict[str, Any]:
        """
        Upload products from JSON file
        
        Args:
            json_path: Path to JSON file
            vendor_key: Vendor identifier
            
        Returns:
            Upload results
        """
        try:
            logger.info(f"Processing JSON: {json_path} for vendor: {vendor_key}")
            
            with open(json_path, 'r') as f:
                data = json.load(f)
            
            # Handle different JSON structures
            if 'products' in data:
                # Full invoice data
                result = self.loader.process_invoice_products(data, vendor_key)
            elif isinstance(data, list):
                # List of products
                invoice_data = {
                    'products': data,
                    'invoice_number': f'JSON-{datetime.now().strftime("%Y%m%d%H%M%S")}',
                    'date': datetime.now().strftime("%Y-%m-%d"),
                    'vendor_key': vendor_key
                }
                result = self.loader.process_invoice_products(invoice_data, vendor_key)
            else:
                return {
                    'success': False,
                    'error': 'Invalid JSON structure',
                    'products_uploaded': 0
                }
            
            logger.info(f"Uploaded {result['products_processed']} products from JSON")
            return {
                'success': result['success'],
                'products_uploaded': result['products_processed'],
                'message': result['message']
            }
            
        except Exception as e:
            logger.error(f"Error uploading from JSON: {e}")
            return {
                'success': False,
                'error': str(e),
                'products_uploaded': 0
            }
    
    def upload_from_excel(self, excel_path: str, vendor_key: str, sheet_name: str = None) -> Dict[str, Any]:
        """
        Upload products from Excel file
        
        Args:
            excel_path: Path to Excel file
            vendor_key: Vendor identifier
            sheet_name: Optional sheet name
            
        Returns:
            Upload results
        """
        try:
            logger.info(f"Processing Excel: {excel_path} for vendor: {vendor_key}")
            
            # Read Excel file
            if sheet_name:
                df = pd.read_excel(excel_path, sheet_name=sheet_name)
            else:
                df = pd.read_excel(excel_path)
            
            # Convert DataFrame to product list
            products = []
            for _, row in df.iterrows():
                product = {
                    'name': str(row.get('name', row.get('product_name', ''))),
                    'description': str(row.get('description', '')),
                    'quantity': float(row.get('quantity', 0)),
                    'unit_price': float(row.get('unit_price', row.get('price', 0))),
                    'total': float(row.get('total', row.get('amount', 0))),
                    'unit': str(row.get('unit', 'each')),
                    'category': str(row.get('category', ''))
                }
                
                # Skip empty rows
                if product['name'] and product['quantity'] > 0:
                    products.append(product)
            
            # Create invoice data
            invoice_data = {
                'products': products,
                'invoice_number': f'EXCEL-{datetime.now().strftime("%Y%m%d%H%M%S")}',
                'date': datetime.now().strftime("%Y-%m-%d"),
                'vendor_key': vendor_key
            }
            
            # Upload products
            result = self.loader.process_invoice_products(invoice_data, vendor_key)
            
            logger.info(f"Uploaded {result['products_processed']} products from Excel")
            return {
                'success': result['success'],
                'products_uploaded': result['products_processed'],
                'message': result['message']
            }
            
        except Exception as e:
            logger.error(f"Error uploading from Excel: {e}")
            return {
                'success': False,
                'error': str(e),
                'products_uploaded': 0
            }
    
    def upload_from_csv(self, csv_path: str, vendor_key: str) -> Dict[str, Any]:
        """
        Upload products from CSV file
        
        Args:
            csv_path: Path to CSV file
            vendor_key: Vendor identifier
            
        Returns:
            Upload results
        """
        try:
            logger.info(f"Processing CSV: {csv_path} for vendor: {vendor_key}")
            
            # Read CSV file
            df = pd.read_csv(csv_path)
            
            # Convert DataFrame to product list
            products = []
            for _, row in df.iterrows():
                product = {
                    'name': str(row.get('name', row.get('product_name', ''))),
                    'description': str(row.get('description', '')),
                    'quantity': float(row.get('quantity', 0)),
                    'unit_price': float(row.get('unit_price', row.get('price', 0))),
                    'total': float(row.get('total', row.get('amount', 0))),
                    'unit': str(row.get('unit', 'each')),
                    'category': str(row.get('category', ''))
                }
                
                # Skip empty rows
                if product['name'] and product['quantity'] > 0:
                    products.append(product)
            
            # Create invoice data
            invoice_data = {
                'products': products,
                'invoice_number': f'CSV-{datetime.now().strftime("%Y%m%d%H%M%S")}',
                'date': datetime.now().strftime("%Y-%m-%d"),
                'vendor_key': vendor_key
            }
            
            # Upload products
            result = self.loader.process_invoice_products(invoice_data, vendor_key)
            
            logger.info(f"Uploaded {result['products_processed']} products from CSV")
            return {
                'success': result['success'],
                'products_uploaded': result['products_processed'],
                'message': result['message']
            }
            
        except Exception as e:
            logger.error(f"Error uploading from CSV: {e}")
            return {
                'success': False,
                'error': str(e),
                'products_uploaded': 0
            }
    
    def bulk_upload_directory(self, directory_path: str, vendor_key: str) -> Dict[str, Any]:
        """
        Upload all supported files from a directory
        
        Args:
            directory_path: Path to directory containing files
            vendor_key: Vendor identifier
            
        Returns:
            Bulk upload results
        """
        try:
            logger.info(f"Processing directory: {directory_path} for vendor: {vendor_key}")
            
            if not os.path.isdir(directory_path):
                return {
                    'success': False,
                    'error': 'Directory does not exist',
                    'files_processed': 0,
                    'total_products_uploaded': 0
                }
            
            results = []
            total_products = 0
            
            # Process all files in directory
            for filename in os.listdir(directory_path):
                file_path = os.path.join(directory_path, filename)
                
                if not os.path.isfile(file_path):
                    continue
                
                file_ext = filename.lower().split('.')[-1]
                
                try:
                    if file_ext == 'pdf':
                        result = self.upload_from_pdf(file_path, vendor_key)
                    elif file_ext == 'json':
                        result = self.upload_from_json(file_path, vendor_key)
                    elif file_ext in ['xlsx', 'xls']:
                        result = self.upload_from_excel(file_path, vendor_key)
                    elif file_ext == 'csv':
                        result = self.upload_from_csv(file_path, vendor_key)
                    else:
                        logger.info(f"Skipping unsupported file: {filename}")
                        continue
                    
                    result['filename'] = filename
                    results.append(result)
                    
                    if result['success']:
                        total_products += result['products_uploaded']
                        
                except Exception as e:
                    logger.error(f"Error processing {filename}: {e}")
                    results.append({
                        'filename': filename,
                        'success': False,
                        'error': str(e),
                        'products_uploaded': 0
                    })
            
            successful_files = sum(1 for r in results if r['success'])
            
            logger.info(f"Processed {len(results)} files, {successful_files} successful, {total_products} total products uploaded")
            
            return {
                'success': successful_files > 0,
                'files_processed': len(results),
                'successful_files': successful_files,
                'total_products_uploaded': total_products,
                'results': results
            }
            
        except Exception as e:
            logger.error(f"Error in bulk upload: {e}")
            return {
                'success': False,
                'error': str(e),
                'files_processed': 0,
                'total_products_uploaded': 0
            }

def main():
    """Main upload function"""
    parser = argparse.ArgumentParser(description='Upload products to invoice parser system')
    parser.add_argument('--file', '-f', help='File to upload')
    parser.add_argument('--directory', '-d', help='Directory to bulk upload')
    parser.add_argument('--vendor', '-v', required=True, help='Vendor key')
    parser.add_argument('--type', '-t', choices=['pdf', 'json', 'excel', 'csv', 'auto'], 
                       default='auto', help='File type (auto-detect by default)')
    parser.add_argument('--sheet', '-s', help='Excel sheet name (for Excel files)')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    uploader = ProductUploader()
    
    try:
        if args.directory:
            # Bulk upload from directory
            result = uploader.bulk_upload_directory(args.directory, args.vendor)
            
            if result['success']:
                print(f"✅ Successfully processed {result['files_processed']} files")
                print(f"📦 Uploaded {result['total_products_uploaded']} products")
            else:
                print(f"❌ Bulk upload failed: {result.get('error', 'Unknown error')}")
                sys.exit(1)
                
        elif args.file:
            # Single file upload
            if not os.path.exists(args.file):
                print(f"❌ File not found: {args.file}")
                sys.exit(1)
            
            # Determine file type
            if args.type == 'auto':
                file_ext = args.file.lower().split('.')[-1]
                if file_ext == 'pdf':
                    result = uploader.upload_from_pdf(args.file, args.vendor)
                elif file_ext == 'json':
                    result = uploader.upload_from_json(args.file, args.vendor)
                elif file_ext in ['xlsx', 'xls']:
                    result = uploader.upload_from_excel(args.file, args.vendor, args.sheet)
                elif file_ext == 'csv':
                    result = uploader.upload_from_csv(args.file, args.vendor)
                else:
                    print(f"❌ Unsupported file type: {file_ext}")
                    sys.exit(1)
            else:
                # Use specified type
                if args.type == 'pdf':
                    result = uploader.upload_from_pdf(args.file, args.vendor)
                elif args.type == 'json':
                    result = uploader.upload_from_json(args.file, args.vendor)
                elif args.type == 'excel':
                    result = uploader.upload_from_excel(args.file, args.vendor, args.sheet)
                elif args.type == 'csv':
                    result = uploader.upload_from_csv(args.file, args.vendor)
            
            if result['success']:
                print(f"✅ Successfully uploaded {result['products_uploaded']} products")
            else:
                print(f"❌ Upload failed: {result.get('error', 'Unknown error')}")
                sys.exit(1)
        else:
            print("❌ Please specify either --file or --directory")
            parser.print_help()
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Upload failed with error: {e}")
        print(f"❌ Upload failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
