#!/usr/bin/env python3
"""
Component 5 Validation Script
Validates product loading, data processing, and analytics functionality
"""

import sys
import os
import logging
from typing import Dict, Any, List
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.product_loader import ProductLoader
from database.connection import get_supabase_client

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Component5Validator:
    """Validates Component 5 functionality"""
    
    def __init__(self):
        self.loader = ProductLoader()
        self.client = get_supabase_client()
        self.test_results = []
        
    def log_test_result(self, test_name: str, passed: bool, message: str = ""):
        """Log test result"""
        status = "PASS" if passed else "FAIL"
        result = f"[{status}] {test_name}"
        if message:
            result += f": {message}"
        
        logger.info(result)
        self.test_results.append({
            'test': test_name,
            'passed': passed,
            'message': message
        })
        
    def test_product_loader_initialization(self) -> bool:
        """Test ProductLoader can be initialized"""
        try:
            loader = ProductLoader()
            self.log_test_result("ProductLoader Initialization", True, "Successfully initialized")
            return True
        except Exception as e:
            self.log_test_result("ProductLoader Initialization", False, f"Error: {e}")
            return False
    
    def test_database_connection(self) -> bool:
        """Test database connection"""
        try:
            client = get_supabase_client()
            # Try a simple query to test connection
            result = client.table('invoice_products').select('*').limit(1).execute()
            self.log_test_result("Database Connection", True, "Connection successful")
            return True
        except Exception as e:
            self.log_test_result("Database Connection", False, f"Error: {e}")
            return False
    
    def test_product_processing(self) -> bool:
        """Test product data processing"""
        try:
            # Sample invoice data
            sample_invoice = {
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
                'invoice_number': 'TEST-2024-001',
                'date': '2024-07-27',
                'currency': 'USD'
            }
            
            products = self.loader.load_products_from_invoice(sample_invoice, 'test_vendor')
            
            if len(products) == 2:
                self.log_test_result("Product Processing", True, f"Processed {len(products)} products")
                return True
            else:
                self.log_test_result("Product Processing", False, f"Expected 2 products, got {len(products)}")
                return False
                
        except Exception as e:
            self.log_test_result("Product Processing", False, f"Error: {e}")
            return False
    
    def test_product_normalization(self) -> bool:
        """Test product name normalization"""
        try:
            # Test normalization
            test_name = "  item: basmati rice premium  "
            normalized = self.loader._normalize_product_name(test_name)
            
            if normalized == "Basmati Rice Premium":
                self.log_test_result("Product Normalization", True, f"'{test_name}' -> '{normalized}'")
                return True
            else:
                self.log_test_result("Product Normalization", False, f"Expected 'Basmati Rice Premium', got '{normalized}'")
                return False
                
        except Exception as e:
            self.log_test_result("Product Normalization", False, f"Error: {e}")
            return False
    
    def test_category_determination(self) -> bool:
        """Test product category determination"""
        try:
            test_cases = [
                ("Basmati Rice", "Grains & Cereals"),
                ("Turmeric Powder", "Spices & Seasonings"),
                ("Coconut Oil", "Oils & Fats"),
                ("Masoor Dal", "Pulses & Legumes"),
                ("Tea Bags", "Beverages"),
                ("Unknown Product", "General Grocery")
            ]
            
            all_passed = True
            for product_name, expected_category in test_cases:
                actual_category = self.loader._determine_category(product_name)
                if actual_category != expected_category:
                    self.log_test_result("Category Determination", False, 
                                       f"'{product_name}': expected '{expected_category}', got '{actual_category}'")
                    all_passed = False
            
            if all_passed:
                self.log_test_result("Category Determination", True, f"All {len(test_cases)} test cases passed")
                return True
            else:
                return False
                
        except Exception as e:
            self.log_test_result("Category Determination", False, f"Error: {e}")
            return False
    
    def test_complete_workflow(self) -> bool:
        """Test complete product processing workflow"""
        try:
            # Sample invoice data
            sample_invoice = {
                'products': [
                    {
                        'name': 'Test Product',
                        'quantity': 1,
                        'unit_price': 10.00,
                        'total': 10.00,
                        'unit': 'piece'
                    }
                ],
                'invoice_number': f'TEST-{datetime.now().strftime("%Y%m%d%H%M%S")}',
                'date': datetime.now().strftime("%Y-%m-%d"),
                'currency': 'USD'
            }
            
            # Process without saving to database (dry run)
            result = self.loader.process_invoice_products(sample_invoice, 'test_vendor')
            
            if result['success'] and result['products_processed'] == 1:
                self.log_test_result("Complete Workflow", True, "Workflow completed successfully")
                return True
            else:
                self.log_test_result("Complete Workflow", False, f"Workflow failed: {result.get('message', 'Unknown error')}")
                return False
                
        except Exception as e:
            self.log_test_result("Complete Workflow", False, f"Error: {e}")
            return False
    
    def test_statistics_generation(self) -> bool:
        """Test product statistics generation"""
        try:
            stats = self.loader.get_product_statistics()
            
            # Check if stats structure is correct
            required_keys = ['total_products', 'categories', 'vendors', 'total_value', 'average_price']
            missing_keys = [key for key in required_keys if key not in stats]
            
            if not missing_keys:
                self.log_test_result("Statistics Generation", True, f"Generated stats with {stats['total_products']} products")
                return True
            else:
                self.log_test_result("Statistics Generation", False, f"Missing keys: {missing_keys}")
                return False
                
        except Exception as e:
            self.log_test_result("Statistics Generation", False, f"Error: {e}")
            return False
    
    def test_vendor_filtering(self) -> bool:
        """Test vendor-specific product filtering"""
        try:
            # Test getting products by vendor (should work even if empty)
            products = self.loader.get_products_by_vendor('test_vendor', limit=10)
            
            # Should return a list (even if empty)
            if isinstance(products, list):
                self.log_test_result("Vendor Filtering", True, f"Retrieved {len(products)} products for test_vendor")
                return True
            else:
                self.log_test_result("Vendor Filtering", False, f"Expected list, got {type(products)}")
                return False
                
        except Exception as e:
            self.log_test_result("Vendor Filtering", False, f"Error: {e}")
            return False
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all validation tests"""
        logger.info("=" * 60)
        logger.info("COMPONENT 5 VALIDATION - PRODUCT LOADER")
        logger.info("=" * 60)
        
        tests = [
            self.test_product_loader_initialization,
            self.test_database_connection,
            self.test_product_processing,
            self.test_product_normalization,
            self.test_category_determination,
            self.test_complete_workflow,
            self.test_statistics_generation,
            self.test_vendor_filtering
        ]
        
        passed_tests = 0
        total_tests = len(tests)
        
        for test in tests:
            if test():
                passed_tests += 1
        
        logger.info("=" * 60)
        logger.info(f"VALIDATION SUMMARY: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            logger.info("🎉 ALL TESTS PASSED! Component 5 is ready for production.")
        else:
            logger.warning(f"⚠️  {total_tests - passed_tests} test(s) failed. Review issues above.")
        
        logger.info("=" * 60)
        
        return {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': total_tests - passed_tests,
            'success_rate': (passed_tests / total_tests) * 100,
            'all_passed': passed_tests == total_tests,
            'test_results': self.test_results
        }

def main():
    """Main validation function"""
    try:
        validator = Component5Validator()
        results = validator.run_all_tests()
        
        # Exit with appropriate code
        sys.exit(0 if results['all_passed'] else 1)
        
    except Exception as e:
        logger.error(f"Validation failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
