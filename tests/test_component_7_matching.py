"""
Unit tests for Component 7: Product Matching
"""

import unittest
from unittest.mock import Mock, MagicMock
import os
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.product_matcher import ProductMatcher, MatchResult
from database.product_repository import ProductRepository
from services.embedding_generator import EmbeddingGenerator
from services.human_review_manager import HumanReviewManager


class TestProductMatcher(unittest.TestCase):
    """Test product matching functionality"""
    
    def setUp(self):
        # Mock dependencies
        self.mock_repo = Mock(spec=ProductRepository)
        self.mock_embedding = Mock(spec=EmbeddingGenerator)
        self.matcher = ProductMatcher(self.mock_repo, self.mock_embedding)
    
    def test_learned_mapping_match(self):
        """Test matching with learned mappings"""
        # Setup mock
        self.mock_repo.get_learned_mappings.return_value = {
            'product': {'id': 'prod_123', 'name': 'DEEP CASHEW WHOLE 7OZ'},
            'confidence': 0.98,
            'mapping_id': 'map_123'
        }
        
        # Test
        result = self.matcher.match_product({'product_name': 'DEEP CASHEW WHOLE 7OZ (20)'})
        
        # Assert
        self.assertTrue(result.matched)
        self.assertEqual(result.product_id, 'prod_123')
        self.assertEqual(result.confidence, 0.98)
        self.assertEqual(result.strategy, 'learned_mapping')
        self.assertEqual(result.routing, 'auto_approve')
    
    def test_structured_match(self):
        """Test structured format matching"""
        # Setup mock
        self.mock_repo.get_learned_mappings.return_value = None
        self.mock_repo.search_by_brand_and_keywords.return_value = [
            {
                'id': 'prod_456',
                'name': 'DEEP CASHEW WHOLE 7OZ',
                'brand': 'DEEP'
            }
        ]
        
        # Test
        result = self.matcher._strategy_structured_match('DEEP CASHEW WHOLE 7OZ')
        
        # Assert
        self.assertIsNotNone(result)
        self.assertTrue(result.matched)
        self.assertEqual(result.strategy, 'structured_match')
    
    def test_fuzzy_match(self):
        """Test fuzzy string matching"""
        # Setup mock
        self.mock_repo.get_all_products_for_fuzzy_match.return_value = [
            {'id': 'prod_789', 'name': 'DEEP CASHEW WHOLE 7OZ'},
            {'id': 'prod_790', 'name': 'DEEP ALMOND WHOLE 7OZ'}
        ]
        
        # Test
        result = self.matcher._strategy_fuzzy_match('DEEP CASHW WHOLE 7 OZ')  # Typo
        
        # Assert
        self.assertIsNotNone(result)
        self.assertTrue(result.matched)
        self.assertEqual(result.product_id, 'prod_789')
        self.assertEqual(result.strategy, 'fuzzy_match')
    
    def test_confidence_routing(self):
        """Test routing based on confidence scores"""
        test_cases = [
            (0.95, 'auto_approve'),
            (0.85, 'auto_approve'),
            (0.80, 'review_priority_2'),
            (0.70, 'review_priority_2'),
            (0.50, 'review_priority_1'),
            (0.20, 'creation_queue')
        ]
        
        for confidence, expected_routing in test_cases:
            routing = self.matcher._determine_routing(confidence)
            self.assertEqual(routing, expected_routing)
    
    def test_parse_product_structure(self):
        """Test product structure parsing"""
        test_cases = [
            ("DEEP CASHEW WHOLE 7OZ", {
                'brand': 'DEEP',
                'keywords': ['CASHEW', 'WHOLE'],
                'size': '7',
                'unit': 'OZ'
            }),
            ("Haldiram Samosa 350g", {
                'brand': 'HALDIRAM',
                'keywords': ['SAMOSA'],
                'size': '350',
                'unit': 'G'
            }),
            ("Unknown Product 500GM", {
                'brand': None,
                'keywords': ['UNKNOWN', 'PRODUCT'],
                'size': '500',
                'unit': 'GM'
            })
        ]
        
        for product_name, expected in test_cases:
            result = self.matcher._parse_product_structure(product_name)
            self.assertEqual(result['brand'], expected['brand'])
            self.assertEqual(result['size'], expected['size'])
            self.assertEqual(result['unit'], expected['unit'])


class TestHumanReviewManager(unittest.TestCase):
    """Test human review functionality"""
    
    def setUp(self):
        self.mock_client = Mock()
        self.review_manager = HumanReviewManager(self.mock_client)
    
    def test_add_to_review_queue(self):
        """Test adding item to review queue"""
        # Setup mock
        self.mock_client.table.return_value.insert.return_value.execute.return_value.data = [
            {'id': 'review_123'}
        ]
        
        # Test
        review_item = {
            'invoice_id': 'inv_123',
            'invoice_product_name': 'DEEP CASHEW 7OZ',
            'suggested_product_id': 'prod_123',
            'confidence_score': 0.75,
            'match_strategy': 'fuzzy_match',
            'priority': 2
        }
        
        review_id = self.review_manager.add_to_review_queue(review_item)
        
        # Assert
        self.assertEqual(review_id, 'review_123')
        self.mock_client.table.assert_called_with('human_review_queue')


if __name__ == '__main__':
    unittest.main()