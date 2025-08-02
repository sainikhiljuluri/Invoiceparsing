"""
Unit tests for Component 5 - Product Loader functionality
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.product_loader import ProductLoader

class TestProductLoader(unittest.TestCase):
    """Test cases for ProductLoader class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_client = Mock()
        
        # Mock the get_supabase_client function
        with patch('database.product_loader.get_supabase_client', return_value=self.mock_client):
            self.loader = ProductLoader()
    
    def test_initialization(self):
        """Test ProductLoader initialization"""
        with patch('database.product_loader.get_supabase_client', return_value=self.mock_client):
            loader = ProductLoader()
            self.assertIsNotNone(loader.client)
            self.assertIsNotNone(loader.logger)
    
    def test_normalize_product_name(self):
        """Test product name normalization"""
        test_cases = [
            ("  basmati rice  ", "Basmati Rice"),
            ("Item: Premium Tea", "Premium Tea"),
            ("Product: Coconut Oil", "Coconut Oil"),
            ("Desc: Turmeric Powder", "Turmeric Powder"),
            ("", ""),
            ("UPPERCASE PRODUCT", "Uppercase Product")
        ]
        
        for input_name, expected in test_cases:
            with self.subTest(input_name=input_name):
                result = self.loader._normalize_product_name(input_name)
                self.assertEqual(result, expected)
    
    def test_determine_category(self):
        """Test product category determination"""
        test_cases = [
            ("Basmati Rice", "Grains & Cereals"),
            ("Wheat Flour", "Grains & Cereals"),
            ("Coconut Oil", "Oils & Fats"),
            ("Ghee", "Oils & Fats"),
            ("Turmeric Powder", "Spices & Seasonings"),
            ("Red Chili", "Spices & Seasonings"),
            ("Masoor Dal", "Pulses & Legumes"),
            ("Chickpea", "Pulses & Legumes"),
            ("Tea Bags", "Beverages"),
            ("Coffee Powder", "Beverages"),
            ("Potato Chips", "Snacks"),
            ("Biscuits", "Snacks"),
            ("Unknown Product", "General Grocery"),
            ("", "Uncategorized")
        ]
        
        for product_name, expected_category in test_cases:
            with self.subTest(product_name=product_name):
                result = self.loader._determine_category(product_name)
                self.assertEqual(result, expected_category)
    
    def test_process_product_valid(self):
        """Test processing valid product data"""
        product_data = {
            'name': 'Basmati Rice',
            'description': 'Premium quality rice',
            'quantity': 10,
            'unit_price': 25.50,
            'total': 255.00,
            'unit': 'kg'
        }
        
        invoice_data = {
            'invoice_number': 'TEST-001',
            'date': '2024-07-27',
            'currency': 'USD'
        }
        
        result = self.loader._process_product(product_data, 'test_vendor', invoice_data)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['name'], 'Basmati Rice')
        self.assertEqual(result['quantity'], 10.0)
        self.assertEqual(result['unit_price'], 25.50)
        self.assertEqual(result['total_price'], 255.00)
        self.assertEqual(result['vendor_key'], 'test_vendor')
        self.assertEqual(result['category'], 'Grains & Cereals')
    
    def test_process_product_invalid(self):
        """Test processing invalid product data"""
        # Test with empty name
        product_data = {
            'name': '',
            'quantity': 10,
            'unit_price': 25.50,
            'total': 255.00
        }
        
        invoice_data = {'invoice_number': 'TEST-001'}
        
        result = self.loader._process_product(product_data, 'test_vendor', invoice_data)
        self.assertIsNone(result)
        
        # Test with zero quantity
        product_data = {
            'name': 'Test Product',
            'quantity': 0,
            'unit_price': 25.50,
            'total': 255.00
        }
        
        result = self.loader._process_product(product_data, 'test_vendor', invoice_data)
        self.assertIsNone(result)
    
    def test_load_products_from_invoice(self):
        """Test loading products from invoice data"""
        invoice_data = {
            'products': [
                {
                    'name': 'Basmati Rice',
                    'quantity': 10,
                    'unit_price': 25.50,
                    'total': 255.00,
                    'unit': 'kg'
                },
                {
                    'name': 'Turmeric Powder',
                    'quantity': 2,
                    'unit_price': 15.00,
                    'total': 30.00,
                    'unit': 'kg'
                }
            ],
            'invoice_number': 'TEST-001',
            'date': '2024-07-27'
        }
        
        products = self.loader.load_products_from_invoice(invoice_data, 'test_vendor')
        
        self.assertEqual(len(products), 2)
        self.assertEqual(products[0]['name'], 'Basmati Rice')
        self.assertEqual(products[1]['name'], 'Turmeric Powder')
    
    def test_load_products_empty_invoice(self):
        """Test loading products from empty invoice"""
        invoice_data = {'products': []}
        
        products = self.loader.load_products_from_invoice(invoice_data, 'test_vendor')
        
        self.assertEqual(len(products), 0)
    
    def test_save_products_to_database_success(self):
        """Test successful saving of products to database"""
        products = [
            {
                'name': 'Test Product',
                'quantity': 1,
                'unit_price': 10.00,
                'total_price': 10.00,
                'vendor_key': 'test_vendor'
            }
        ]
        
        # Mock successful database insert
        mock_result = Mock()
        mock_result.data = [{'id': 1}]
        self.mock_client.table.return_value.insert.return_value.execute.return_value = mock_result
        
        result = self.loader.save_products_to_database(products)
        
        self.assertTrue(result)
        self.mock_client.table.assert_called_with('invoice_products')
    
    def test_save_products_to_database_failure(self):
        """Test failed saving of products to database"""
        products = [{'name': 'Test Product'}]
        
        # Mock failed database insert
        mock_result = Mock()
        mock_result.data = None
        self.mock_client.table.return_value.insert.return_value.execute.return_value = mock_result
        
        result = self.loader.save_products_to_database(products)
        
        self.assertFalse(result)
    
    def test_save_products_empty_list(self):
        """Test saving empty product list"""
        result = self.loader.save_products_to_database([])
        self.assertTrue(result)  # Should succeed with empty list
    
    def test_get_products_by_vendor(self):
        """Test retrieving products by vendor"""
        # Mock database query result
        mock_result = Mock()
        mock_result.data = [
            {'name': 'Product 1', 'vendor_key': 'test_vendor'},
            {'name': 'Product 2', 'vendor_key': 'test_vendor'}
        ]
        
        self.mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = mock_result
        
        products = self.loader.get_products_by_vendor('test_vendor', limit=10)
        
        self.assertEqual(len(products), 2)
        self.mock_client.table.assert_called_with('invoice_products')
    
    def test_get_product_statistics(self):
        """Test generating product statistics"""
        # Mock database query result
        mock_result = Mock()
        mock_result.data = [
            {
                'category': 'Grains & Cereals',
                'vendor_key': 'vendor1',
                'total_price': 100.0
            },
            {
                'category': 'Spices & Seasonings',
                'vendor_key': 'vendor1',
                'total_price': 50.0
            },
            {
                'category': 'Grains & Cereals',
                'vendor_key': 'vendor2',
                'total_price': 75.0
            }
        ]
        
        self.mock_client.table.return_value.select.return_value.execute.return_value = mock_result
        
        stats = self.loader.get_product_statistics()
        
        self.assertEqual(stats['total_products'], 3)
        self.assertEqual(stats['categories']['Grains & Cereals'], 2)
        self.assertEqual(stats['categories']['Spices & Seasonings'], 1)
        self.assertEqual(stats['vendors']['vendor1'], 2)
        self.assertEqual(stats['vendors']['vendor2'], 1)
        self.assertEqual(stats['total_value'], 225.0)
        self.assertEqual(stats['average_price'], 75.0)
    
    def test_get_product_statistics_empty(self):
        """Test generating statistics with no products"""
        # Mock empty database result
        mock_result = Mock()
        mock_result.data = []
        
        self.mock_client.table.return_value.select.return_value.execute.return_value = mock_result
        
        stats = self.loader.get_product_statistics()
        
        self.assertEqual(stats['total_products'], 0)
        self.assertEqual(stats['categories'], {})
        self.assertEqual(stats['vendors'], {})
        self.assertEqual(stats['total_value'], 0)
        self.assertEqual(stats['average_price'], 0)
    
    def test_process_invoice_products_success(self):
        """Test complete invoice products processing workflow"""
        invoice_data = {
            'products': [
                {
                    'name': 'Test Product',
                    'quantity': 1,
                    'unit_price': 10.00,
                    'total': 10.00
                }
            ],
            'invoice_number': 'TEST-001',
            'date': '2024-07-27'
        }
        
        # Mock successful database save
        mock_result = Mock()
        mock_result.data = [{'id': 1}]
        self.mock_client.table.return_value.insert.return_value.execute.return_value = mock_result
        
        result = self.loader.process_invoice_products(invoice_data, 'test_vendor')
        
        self.assertTrue(result['success'])
        self.assertEqual(result['products_processed'], 1)
        self.assertIn('products', result)
    
    def test_process_invoice_products_no_products(self):
        """Test processing invoice with no products"""
        invoice_data = {'products': []}
        
        result = self.loader.process_invoice_products(invoice_data, 'test_vendor')
        
        self.assertTrue(result['success'])
        self.assertEqual(result['products_processed'], 0)
        self.assertEqual(result['message'], 'No products found in invoice')
    
    def test_process_invoice_products_save_failure(self):
        """Test processing with database save failure"""
        invoice_data = {
            'products': [
                {
                    'name': 'Test Product',
                    'quantity': 1,
                    'unit_price': 10.00,
                    'total': 10.00
                }
            ]
        }
        
        # Mock failed database save
        mock_result = Mock()
        mock_result.data = None
        self.mock_client.table.return_value.insert.return_value.execute.return_value = mock_result
        
        result = self.loader.process_invoice_products(invoice_data, 'test_vendor')
        
        self.assertFalse(result['success'])
        self.assertEqual(result['products_processed'], 1)
        self.assertEqual(result['message'], 'Failed to save products')

class TestProductLoaderEdgeCases(unittest.TestCase):
    """Test edge cases and error handling"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_client = Mock()
        with patch('database.product_loader.get_supabase_client', return_value=self.mock_client):
            self.loader = ProductLoader()
    
    def test_process_product_with_missing_fields(self):
        """Test processing product with missing fields"""
        product_data = {'name': 'Test Product'}  # Missing required fields
        invoice_data = {}
        
        result = self.loader._process_product(product_data, 'test_vendor', invoice_data)
        
        # Should handle missing fields gracefully
        self.assertIsNone(result)  # Invalid due to missing quantity
    
    def test_process_product_with_invalid_types(self):
        """Test processing product with invalid data types"""
        product_data = {
            'name': 'Test Product',
            'quantity': 'invalid',  # Should be numeric
            'unit_price': 'invalid',  # Should be numeric
            'total': 'invalid'  # Should be numeric
        }
        invoice_data = {}
        
        # Should handle type conversion errors
        result = self.loader._process_product(product_data, 'test_vendor', invoice_data)
        self.assertIsNone(result)
    
    def test_database_connection_error(self):
        """Test handling database connection errors"""
        # Mock database error
        self.mock_client.table.side_effect = Exception("Database connection error")
        
        result = self.loader.save_products_to_database([{'name': 'Test'}])
        self.assertFalse(result)
    
    def test_get_products_by_vendor_error(self):
        """Test handling errors when retrieving products by vendor"""
        # Mock database error
        self.mock_client.table.side_effect = Exception("Database query error")
        
        products = self.loader.get_products_by_vendor('test_vendor')
        self.assertEqual(products, [])
    
    def test_get_statistics_error(self):
        """Test handling errors when generating statistics"""
        # Mock database error
        self.mock_client.table.side_effect = Exception("Database query error")
        
        stats = self.loader.get_product_statistics()
        self.assertIn('error', stats)

if __name__ == '__main__':
    unittest.main()
