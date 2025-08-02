"""
Unit tests for Component 8: Price Updates & Tracking
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta

from services.price_updater import PriceUpdater
from services.price_validator import PriceValidator
from database.price_repository import PriceRepository


class TestPriceValidator(unittest.TestCase):
    """Test price validation logic"""
    
    def setUp(self):
        self.validator = PriceValidator()
    
    def test_price_bounds_validation(self):
        """Test price bounds checking"""
        # Test valid price
        valid, msg, _ = self.validator.validate_price_change(None, 10.0, 'USD')
        self.assertTrue(valid)
        
        # Test price too low
        valid, msg, _ = self.validator.validate_price_change(None, 0.001, 'USD')
        self.assertFalse(valid)
        self.assertIn("below minimum", msg)
        
        # Test price too high
        valid, msg, _ = self.validator.validate_price_change(None, 99999.0, 'USD')
        self.assertFalse(valid)
        self.assertIn("above maximum", msg)
    
    def test_percentage_change_validation(self):
        """Test percentage change limits"""
        # Test acceptable increase (30%)
        valid, msg, details = self.validator.validate_price_change(10.0, 13.0, 'USD')
        self.assertTrue(valid)
        self.assertEqual(details['change_percentage'], 30.0)
        
        # Test excessive increase (60%)
        valid, msg, details = self.validator.validate_price_change(10.0, 16.0, 'USD')
        self.assertFalse(valid)
        self.assertIn("exceeds maximum allowed 50%", msg)
        
        # Test acceptable decrease (20%)
        valid, msg, details = self.validator.validate_price_change(10.0, 8.0, 'USD')
        self.assertTrue(valid)
        self.assertEqual(details['change_percentage'], -20.0)
        
        # Test excessive decrease (40%)
        valid, msg, details = self.validator.validate_price_change(10.0, 6.0, 'USD')
        self.assertFalse(valid)
        self.assertIn("exceeds maximum allowed 30%", msg)
    
    def test_first_time_price(self):
        """Test first-time price entry"""
        valid, msg, _ = self.validator.validate_price_change(None, 15.0, 'USD')
        self.assertTrue(valid)
        self.assertIn("First price entry", msg)
    
    def test_rapid_change_detection(self):
        """Test rapid price change detection"""
        # Create mock history with rapid changes
        now = datetime.now()
        rapid_history = [
            {'created_at': (now - timedelta(hours=1)).isoformat()},
            {'created_at': (now - timedelta(hours=2)).isoformat()},
            {'created_at': (now - timedelta(hours=3)).isoformat()},
        ]
        
        valid, msg, details = self.validator.validate_price_change(
            10.0, 11.0, 'USD', rapid_history
        )
        
        # Should still be valid but with warning
        self.assertTrue(valid)
        self.assertIn('warning', details)


class TestPriceUpdater(unittest.TestCase):
    """Test price update service"""
    
    def setUp(self):
        self.mock_repo = Mock(spec=PriceRepository)
        self.mock_validator = Mock(spec=PriceValidator)
        self.updater = PriceUpdater(self.mock_repo, self.mock_validator)
    
    def test_successful_price_update(self):
        """Test successful price update flow"""
        # Setup mocks
        self.mock_repo.get_current_product_cost.return_value = {
            'id': 'prod_123',
            'name': 'Test Product',
            'cost': 10.0,
            'currency': 'USD'
        }
        self.mock_repo.get_price_history.return_value = []
        self.mock_repo.update_product_cost.return_value = True
        self.mock_repo.create_price_history_entry.return_value = True
        
        self.mock_validator.validate_price_change.return_value = (
            True, 
            "Price change validated",
            {'change_percentage': 20.0}
        )
        
        # Test update
        result = self.updater.update_product_price(
            product_id='prod_123',
            new_cost=12.0,
            currency='USD',
            invoice_id='inv_123',
            invoice_number='INV-2024-001',
            vendor_id='vendor_123'
        )
        
        # Assertions
        self.assertEqual(result['status'], 'updated')
        self.assertEqual(result['old_cost'], 10.0)
        self.assertEqual(result['new_cost'], 12.0)
        self.assertEqual(result['change_percentage'], 20.0)
        
        # Verify repo calls
        self.mock_repo.update_product_cost.assert_called_once()
        self.mock_repo.create_price_history_entry.assert_called_once()
    
    def test_validation_failure(self):
        """Test price update with validation failure"""
        # Setup mocks
        self.mock_repo.get_current_product_cost.return_value = {
            'id': 'prod_123',
            'name': 'Test Product',
            'cost': 10.0
        }
        
        self.mock_validator.validate_price_change.return_value = (
            False,
            "Price increase too high",
            {'change_percentage': 100.0}
        )
        
        # Test update
        result = self.updater.update_product_price(
            product_id='prod_123',
            new_cost=20.0,  # 100% increase
            currency='USD',
            invoice_id='inv_123',
            invoice_number='INV-2024-001'
        )
        
        # Assertions
        self.assertEqual(result['status'], 'skipped')
        self.assertIn("too high", result['reason'])
        
        # Verify product cost was NOT updated
        self.mock_repo.update_product_cost.assert_not_called()
    
    def test_bulk_invoice_update(self):
        """Test updating prices from invoice"""
        matched_products = [
            {
                'product_id': 'prod_1',
                'product_name': 'Product 1',
                'cost_per_unit': 15.0,
                'currency': 'USD',
                'routing': 'auto_approve'
            },
            {
                'product_id': 'prod_2',
                'product_name': 'Product 2', 
                'cost_per_unit': 25.0,
                'currency': 'USD',
                'routing': 'review_priority_2'  # Should be skipped
            }
        ]
        
        # Mock successful update
        self.updater.update_product_price = Mock(return_value={
            'status': 'updated',
            'product_id': 'prod_1',
            'old_cost': 10.0,
            'new_cost': 15.0
        })
        
        # Test
        results = self.updater.update_prices_from_invoice(
            invoice_id='inv_123',
            invoice_number='INV-2024-001',
            vendor_id='vendor_123',
            matched_products=matched_products
        )
        
        # Assertions
        self.assertEqual(results['total_products'], 2)
        self.assertEqual(results['updated'], 1)
        self.assertEqual(results['skipped'], 1)
        self.assertEqual(results['failed'], 0)


if __name__ == '__main__':
    unittest.main()