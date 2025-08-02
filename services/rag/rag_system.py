"""
Core RAG System implementation
"""

import os
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import json

from anthropic import Anthropic
from sentence_transformers import SentenceTransformer

from config.database import get_supabase_client
from .intent_analyzer import IntentAnalyzer
from .entity_extractor import EntityExtractor
from .response_generator import ResponseGenerator
from services.analytics.analytics_engine import AnalyticsEngine
from services.conversation_memory import ConversationMemory
from services.pricing_calculator import PriceCalculator
from services.price_analytics import PricingAnalytics

logger = logging.getLogger(__name__)


class AdvancedRAGSystem:
    """Main RAG system orchestrator"""
    
    def __init__(self):
        self.client = get_supabase_client()
        
        # Initialize components
        self.intent_analyzer = IntentAnalyzer()
        self.entity_extractor = EntityExtractor(self.client)
        self.response_generator = ResponseGenerator()
        self.analytics_engine = AnalyticsEngine(self.client)
        self.conversation_memory = ConversationMemory(self.client)
        
        # Initialize embedder
        self.embedder = SentenceTransformer(
            os.getenv('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
        )
        
        logger.info("RAG System initialized")
    
    async def process_query(self, query: str, session_id: str, 
                          user_id: Optional[str] = None) -> Dict[str, Any]:
        """Process user query and return response"""
        
        start_time = datetime.now()
        
        try:
            # Step 1: Analyze intent
            intent = await self.intent_analyzer.analyze(query)
            
            # Step 2: Extract entities
            entities = await self.entity_extractor.extract(query)
            
            # Step 3: Get conversation context
            context = await self.conversation_memory.get_context(
                session_id, limit=5
            )
            
            # Step 4: Retrieve relevant information
            retrieved_info = await self._retrieve_information(
                query, intent, entities
            )
            
            # Step 5: Generate response
            response = await self.response_generator.generate(
                query=query,
                intent=intent,
                entities=entities,
                retrieved_info=retrieved_info,
                context=context
            )
            
            # Step 6: Store in memory
            await self.conversation_memory.add_turn(
                session_id=session_id,
                user_query=query,
                assistant_response=response['answer'],
                intent=intent['type'],
                entities=entities
            )
            
            # Step 7: Track analytics
            processing_time = (datetime.now() - start_time).total_seconds()
            await self._track_analytics(intent, processing_time, True)
            
            return response
            
        except Exception as e:
            logger.error(f"RAG processing error: {e}")
            return {
                'answer': "I encountered an error. Please try again.",
                'error': str(e),
                'success': False
            }
    
    async def _retrieve_information(self, query: str, intent: Dict, 
                                  entities: Dict) -> Dict[str, Any]:
        """Retrieve relevant information based on query"""
        
        retrieved = {
            'documents': [],
            'data': {},
            'sources': []
        }
        
        # Route based on intent
        if intent['type'] == 'cost_query':
            retrieved = await self._retrieve_cost_info(entities)
        elif intent['type'] == 'trend_analysis':
            retrieved = await self._retrieve_trend_info(entities)
        elif intent['type'] == 'anomaly_check':
            retrieved = await self._retrieve_anomalies()
        elif intent['type'] == 'product_details':
            # For product details, also calculate pricing if cost is available
            retrieved = await self._retrieve_product_details_with_pricing(entities)
        elif intent['type'] == 'invoice_query' or 'invoice_numbers' in entities:
            retrieved = await self._retrieve_invoice_info(entities)
        elif intent['type'] == 'pricing_query':
            retrieved = await self._handle_pricing_query(query, entities)
        elif intent['type'] == 'pricing_analysis':
            retrieved = await self._handle_pricing_analysis(query, entities)
        elif intent['type'] == 'bulk_pricing':
            retrieved = await self._handle_bulk_pricing(query, entities)
        
        return retrieved
    
    async def _retrieve_cost_info(self, entities: Dict) -> Dict[str, Any]:
        """Retrieve cost information"""
        cost_info = {}
        products = entities.get('products', [])
        
        for product in products:
            # Priority 1: Check invoice_items table for actual purchase prices
            invoice_items_result = self.client.table('invoice_items').select(
                'product_name, unit_price, cost_per_unit, created_at, invoice_id, invoices(invoice_number, invoice_date, vendor_name)'
            ).ilike('product_name', f'%{product}%').order(
                'created_at', desc=True
            ).limit(10).execute()
            
            if invoice_items_result.data:
                # Use most recent invoice item cost
                latest_item = invoice_items_result.data[0]
                actual_cost = latest_item.get('cost_per_unit') or latest_item.get('unit_price') or 0
                
                # Extract invoice information
                invoice_info = latest_item.get('invoices', {})
                invoice_number = invoice_info.get('invoice_number', 'Unknown') if invoice_info else 'Unknown'
                invoice_date = invoice_info.get('invoice_date', 'Unknown') if invoice_info else 'Unknown'
                vendor_name = invoice_info.get('vendor_name', 'Unknown') if invoice_info else 'Unknown'
                
                cost_info[product] = {
                    'cost_per_unit': actual_cost,
                    'currency': 'USD',  # Default currency
                    'updated_at': latest_item.get('created_at', 'Unknown'),
                    'source': 'invoice_items_table',
                    'invoice_id': latest_item.get('invoice_id'),
                    'invoice_number': invoice_number,
                    'invoice_date': invoice_date,
                    'vendor_name': vendor_name,
                    'product_name': latest_item.get('product_name')
                }
                
                # Add recent purchase history
                cost_info[product]['recent_purchases'] = [
                    {
                        'price': item.get('cost_per_unit') or item.get('unit_price') or 0,
                        'date': item['created_at'],
                        'invoice': item['invoice_id']
                    } for item in invoice_items_result.data
                ]
            else:
                # Priority 2: Fall back to products table if not found in invoice_items
                product_result = self.client.table('products').select(
                    'id, name, cost, price, currency, updated_at'
                ).ilike('name', f'%{product}%').limit(1).execute()
                
                if product_result.data:
                    product_data = product_result.data[0]
                    cost_info[product] = {
                        'cost_per_unit': product_data.get('cost') or product_data.get('price') or 0,
                        'currency': product_data.get('currency', 'USD'),
                        'updated_at': product_data.get('updated_at', 'Unknown'),
                        'source': 'products_table',
                        'product_name': product_data['name']
                    }
        
        return {
            'data': cost_info,
            'sources': ['invoice_items_table', 'products_table']
        }
    
    async def _retrieve_trend_info(self, entities: Dict) -> Dict[str, Any]:
        """Retrieve trend information from recent invoice items"""
        try:
            # Get recent invoice items with price information
            result = self.client.table('invoice_items').select(
                'product_name, unit_price, cost_per_unit, created_at, invoice_id, invoices(invoice_number, invoice_date)'
            ).order('created_at', desc=True).limit(50).execute()
            
            # Group by product to show recent price trends
            product_trends = {}
            for item in result.data:
                product_name = item['product_name']
                cost = item.get('cost_per_unit') or item.get('unit_price') or 0
                
                if product_name not in product_trends:
                    product_trends[product_name] = []
                
                product_trends[product_name].append({
                    'cost': cost,
                    'date': item['created_at'],
                    'invoice_id': item['invoice_id'],
                    'invoice_number': item.get('invoices', {}).get('invoice_number', 'Unknown') if item.get('invoices') else 'Unknown'
                })
            
            return {
                'data': product_trends,
                'raw_items': result.data,
                'sources': ['invoice_items_table']
            }
        except Exception as e:
            logger.error(f"Error retrieving trend info: {e}")
            return {'data': {}, 'sources': []}
    
    async def _retrieve_product_details_with_pricing(self, entities: Dict) -> Dict[str, Any]:
        """Retrieve product details and automatically calculate suggested selling prices"""
        
        # First get regular product details
        product_details = await self._retrieve_product_details(entities)
        
        # If products were found with cost information, calculate pricing
        if product_details.get('data') and 'products' in product_details['data']:
            calculator = PriceCalculator(self.client)
            products_with_pricing = []
            
            for product in product_details['data']['products']:
                if product.get('cost_per_unit') and product['cost_per_unit'] > 0:
                    # Create product info for pricing calculation
                    product_info = {
                        'product_name': product['product_name'],
                        'cost_per_unit': product['cost_per_unit'],
                        'category': self._categorize_product(product['product_name']),
                        'brand': self._extract_brand(product['product_name']),
                        'size': self._extract_size(product['product_name'])
                    }
                    
                    # Calculate suggested pricing
                    try:
                        pricing = calculator.calculate_suggested_price(product_info)
                        product['pricing'] = pricing
                        product['has_pricing'] = True
                    except Exception as e:
                        logger.error(f"Error calculating pricing for {product['product_name']}: {e}")
                        product['has_pricing'] = False
                else:
                    product['has_pricing'] = False
                
                products_with_pricing.append(product)
            
            product_details['data']['products'] = products_with_pricing
            product_details['data']['pricing_calculated'] = True
        
        return product_details
    
    async def _retrieve_product_details(self, entities: Dict) -> Dict[str, Any]:
        """Retrieve full product details including barcode, brand, category"""
        products = entities.get('products', [])
        product_details = {}
        
        for product in products:
            try:
                # Get full product information from products table
                result = self.client.table('products').select(
                    'id, name, brand, category, sub_category, barcode, sku, product_code, '
                    'pack_size, units_per_case, case_weight, cost, price, currency, '
                    'supplier_name, supplier_code, origin_country, min_order_quantity, '
                    'lead_time_days, is_active, is_discontinued, last_update_date, size'
                ).ilike('name', f'%{product}%').limit(5).execute()
                
                for item in result.data:
                    product_name = item['name']
                    product_details[product_name] = {
                        'name': item['name'],
                        'brand': item.get('brand', 'Unknown'),
                        'category': item.get('category', 'Unknown'),
                        'sub_category': item.get('sub_category', 'Unknown'),
                        'barcode': item.get('barcode', 'Not available'),
                        'sku': item.get('sku', 'Not available'),
                        'product_code': item.get('product_code', 'Not available'),
                        'pack_size': item.get('pack_size', 'Unknown'),
                        'units_per_case': item.get('units_per_case', 'Unknown'),
                        'case_weight': item.get('case_weight', 'Unknown'),
                        'cost': item.get('cost', 0),
                        'price': item.get('price', 0),
                        'currency': item.get('currency', 'USD'),
                        'supplier_name': item.get('supplier_name', 'Unknown'),
                        'supplier_code': item.get('supplier_code', 'Unknown'),
                        'origin_country': item.get('origin_country', 'Unknown'),
                        'min_order_quantity': item.get('min_order_quantity', 'Unknown'),
                        'lead_time_days': item.get('lead_time_days', 'Unknown'),
                        'size': item.get('size', 'Unknown'),
                        'is_active': item.get('is_active', True),
                        'is_discontinued': item.get('is_discontinued', False),
                        'last_update_date': item.get('last_update_date', 'Unknown')
                    }
                    
            except Exception as e:
                logger.error(f"Error retrieving product details for {product}: {e}")
                continue
        
        return {
            'data': product_details,
            'sources': ['products_table']
        }
    
    async def _retrieve_anomalies(self) -> Dict[str, Any]:
        """Retrieve anomaly information"""
        try:
            anomalies = await self.analytics_engine.detect_anomalies('last_week')
            return {
                'data': anomalies,
                'sources': ['Anomaly detection']
            }
        except Exception as e:
            logger.error(f"Error retrieving anomalies: {e}")
            return {'data': [], 'sources': []}
    
    async def _retrieve_invoice_info(self, entities: Dict) -> Dict[str, Any]:
        """Retrieve information about specific invoices and their products"""
        invoice_info = {}
        
        invoice_numbers = entities.get('invoice_numbers', [])
        
        for invoice_number in invoice_numbers:
            try:
                # Get invoice details
                invoice_result = self.client.table('invoices').select(
                    '*'
                ).eq('invoice_number', invoice_number).execute()
                
                if not invoice_result.data:
                    invoice_info[invoice_number] = {
                        'error': f'Invoice {invoice_number} not found',
                        'products': []
                    }
                    continue
                
                invoice_data = invoice_result.data[0]
                invoice_id = invoice_data['id']
                
                # Get all products/items for this invoice
                items_result = self.client.table('invoice_items').select(
                    '*'
                ).eq('invoice_id', invoice_id).execute()
                
                products = []
                total_value = 0
                
                for item in items_result.data:
                    product_info = {
                        'name': item.get('invoice_product_name', 'Unknown Product'),
                        'quantity': item.get('quantity', 0),
                        'units_per_pack': item.get('units', 0),
                        'unit_price': item.get('unit_price', 0),
                        'cost_per_unit': item.get('cost_per_unit', 0),
                        'total_amount': item.get('total_amount', 0),
                        'match_confidence': item.get('match_confidence', 0)
                    }
                    products.append(product_info)
                    
                    if item.get('total_amount'):
                        total_value += float(item.get('total_amount', 0))
                
                invoice_info[invoice_number] = {
                    'invoice_details': {
                        'invoice_number': invoice_data.get('invoice_number'),
                        'vendor_name': invoice_data.get('vendor_name'),
                        'invoice_date': invoice_data.get('invoice_date'),
                        'total_amount': invoice_data.get('total_amount'),
                        'processing_status': invoice_data.get('processing_status'),
                        'products_found': len(products),
                        'calculated_total': total_value
                    },
                    'products': products,
                    'summary': {
                        'total_products': len(products),
                        'total_value': total_value
                    }
                }
                
            except Exception as e:
                logger.error(f"Error retrieving invoice {invoice_number}: {e}")
                invoice_info[invoice_number] = {
                    'error': f'Error retrieving invoice {invoice_number}: {str(e)}',
                    'products': []
                }
        
        return {
            'data': invoice_info,
            'sources': ['invoices_table', 'invoice_items_table']
        }
    
    async def _track_analytics(self, intent: Dict, response_time: float, 
                              success: bool):
        """Track query analytics"""
        try:
            self.client.table('rag_analytics').insert({
                'intent_type': intent['type'],
                'confidence': intent['confidence'],
                'response_time': response_time,
                'success': success,
                'timestamp': datetime.now().isoformat()
            }).execute()
        except Exception as e:
            logger.error(f"Error tracking analytics: {e}")
    
    async def _handle_pricing_query(self, query: str, entities: Dict) -> Dict[str, Any]:
        """Handle pricing-related queries"""
        
        # Initialize price calculator
        calculator = PriceCalculator(self.client)
        
        # Extract product from entities or query
        product_name = self._extract_product_from_query(query, entities)
        
        if not product_name:
            # Provide helpful guidance with examples
            return {
                'data': {
                    'guidance': 'To calculate a suggested selling price, I need specific product details. Here are some examples:',
                    'examples': [
                        '"What should I sell Basmati Rice 1kg for if it costs ₹45?"',
                        '"Suggest selling price for Turmeric Powder 500g costing ₹25"',
                        '"Price recommendation for Organic Tea 100g at ₹80 cost"'
                    ],
                    'help_text': 'Please provide: Product name, size/quantity, and your cost price for accurate pricing recommendations.',
                    'query_type': 'pricing_guidance'
                },
                'sources': ['pricing_system']
            }
        
        # Get product details from database
        product_info = await self._get_product_info(product_name)
        
        if not product_info:
            return {
                'data': {'error': f'Product "{product_name}" not found in database'},
                'sources': ['pricing_system']
            }
        
        # Calculate suggested price
        pricing = calculator.calculate_suggested_price(product_info)
        
        return {
            'data': {
                'pricing_result': pricing,
                'product_name': product_name,
                'query_type': 'pricing_suggestion'
            },
            'sources': ['pricing_calculator', 'product_database']
        }
    
    async def _handle_pricing_analysis(self, query: str, entities: Dict) -> Dict[str, Any]:
        """Handle pricing analysis queries"""
        
        product_name = self._extract_product_from_query(query, entities)
        
        if not product_name:
            return {
                'data': {'error': 'Please specify a product for pricing analysis'},
                'sources': ['pricing_analytics']
            }
        
        product_id = await self._get_product_id(product_name)
        
        if not product_id:
            return {
                'data': {'error': f'Product "{product_name}" not found for analysis'},
                'sources': ['pricing_analytics']
            }
        
        analytics = PricingAnalytics(self.client)
        analysis = analytics.analyze_pricing_performance(product_id)
        
        return {
            'data': {
                'analysis_result': analysis,
                'product_name': product_name,
                'query_type': 'pricing_analysis'
            },
            'sources': ['pricing_analytics', 'sales_data']
        }
    
    async def _handle_bulk_pricing(self, query: str, entities: Dict) -> Dict[str, Any]:
        """Handle bulk pricing requests"""
        
        category = self._extract_category_from_query(query, entities)
        
        if not category:
            return {
                'data': {'error': 'Please specify a product category for bulk pricing'},
                'sources': ['pricing_system']
            }
        
        products = await self._get_products_by_category(category)
        
        if not products:
            return {
                'data': {'error': f'No products found in category "{category}"'},
                'sources': ['product_database']
            }
        
        calculator = PriceCalculator(self.client)
        results = calculator.calculate_bulk_prices(products[:10])  # Limit to 10
        
        return {
            'data': {
                'bulk_pricing_results': results,
                'category': category,
                'products_processed': len(results),
                'query_type': 'bulk_pricing'
            },
            'sources': ['pricing_calculator', 'product_database']
        }
    
    def _extract_product_from_query(self, query: str, entities: Dict = None) -> str:
        """Extract product name from query or entities"""
        
        # First check entities
        if entities and entities.get('products'):
            return entities['products'][0]
        
        # Then try to extract from query text
        query_lower = query.lower()
        
        # Look for common patterns
        import re
        
        # Pattern: "price for [product]"
        match = re.search(r'(?:price|pricing)\s+for\s+([\w\s]+?)(?:\s|$|\?)', query_lower)
        if match:
            return match.group(1).strip()
        
        # Pattern: "[product] price"
        match = re.search(r'([\w\s]+?)\s+(?:price|pricing)', query_lower)
        if match:
            return match.group(1).strip()
        
        # Pattern: quoted product name
        match = re.search(r'["\']([^"\'\']+)["\']', query)
        if match:
            return match.group(1).strip()
        
        return None
    
    def _extract_category_from_query(self, query: str, entities: Dict = None) -> str:
        """Extract category from query"""
        
        if entities and entities.get('categories'):
            return entities['categories'][0]
        
        query_lower = query.lower()
        
        # Common categories
        categories = {
            'rice': 'RICE',
            'flour': 'FLOUR', 
            'atta': 'FLOUR',
            'spices': 'SPICES',
            'masala': 'SPICES',
            'snacks': 'SNACKS',
            'frozen': 'FROZEN',
            'sweets': 'SWEETS',
            'lentils': 'LENTILS',
            'dal': 'LENTILS'
        }
        
        for keyword, category in categories.items():
            if keyword in query_lower:
                return category
        
        return None
    
    async def _get_product_info(self, product_name: str) -> Dict:
        """Get product information from database"""
        
        try:
            # First try exact match
            result = self.client.table('products').select('*').eq(
                'name', product_name
            ).execute()
            
            if result.data:
                product = result.data[0]
                
                # Get latest cost from invoice_items
                cost_result = self.client.table('invoice_items').select(
                    'cost_per_unit, unit_price'
                ).ilike('product_name', f'%{product_name}%').order(
                    'created_at', desc=True
                ).limit(1).execute()
                
                cost_per_unit = 0
                if cost_result.data:
                    item = cost_result.data[0]
                    cost_per_unit = item.get('cost_per_unit') or item.get('unit_price') or 0
                
                return {
                    'product_name': product['name'],
                    'cost_per_unit': cost_per_unit,
                    'category': product.get('category', 'DEFAULT'),
                    'brand': product.get('brand', ''),
                    'size': product.get('size', '')
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting product info for {product_name}: {e}")
            return None
    
    async def _get_product_id(self, product_name: str) -> str:
        """Get product ID from database"""
        
        try:
            result = self.client.table('products').select('id').ilike(
                'name', f'%{product_name}%'
            ).limit(1).execute()
            
            if result.data:
                return result.data[0]['id']
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting product ID for {product_name}: {e}")
            return None
    
    def _categorize_product(self, product_name: str) -> str:
        """Categorize product based on name"""
        product_lower = product_name.lower()
        
        if any(keyword in product_lower for keyword in ['rice', 'basmati', 'sona', 'masuri']):
            return 'Rice'
        elif any(keyword in product_lower for keyword in ['turmeric', 'chili', 'coriander', 'cumin', 'spice']):
            return 'Spices'
        elif any(keyword in product_lower for keyword in ['tea', 'coffee']):
            return 'Beverages'
        elif any(keyword in product_lower for keyword in ['oil', 'ghee']):
            return 'Oils & Fats'
        elif any(keyword in product_lower for keyword in ['dal', 'lentil', 'bean']):
            return 'Pulses'
        else:
            return 'General'
    
    def _extract_brand(self, product_name: str) -> str:
        """Extract brand from product name"""
        brands = ['24 mantra', '24m', 'india gate', 'tata', 'fortune', 'saffola', 'organic']
        product_lower = product_name.lower()
        
        for brand in brands:
            if brand in product_lower:
                return brand.title()
        
        return 'Generic'
    
    def _extract_size(self, product_name: str) -> str:
        """Extract size/quantity from product name"""
        import re
        
        size_pattern = r'(\\d+(?:\\.\\d+)?\\s*(?:kg|g|lb|lbs|oz|ml|l)\\b)'
        match = re.search(size_pattern, product_name.lower())
        
        if match:
            return match.group(1)
        
        return 'Standard'
    
    async def _get_products_by_category(self, category: str) -> List[Dict]:
        """Get products by category"""
        
        try:
            # Get products from category
            result = self.client.table('products').select('*').eq(
                'category', category
            ).limit(10).execute()
            
            products = []
            for product in result.data:
                # Get latest cost
                cost_result = self.client.table('invoice_items').select(
                    'cost_per_unit, unit_price'
                ).ilike('product_name', f'%{product["name"]}%').order(
                    'created_at', desc=True
                ).limit(1).execute()
                
                for item in cost_result.data:
                    product_name = item['product_name']
                    cost_per_unit = item.get('cost_per_unit') or item.get('unit_price') or 0
                    
                    # Extract invoice information
                    invoice_info = item.get('invoices', {})
                    invoice_number = invoice_info.get('invoice_number', 'Unknown') if invoice_info else 'Unknown'
                    invoice_date = invoice_info.get('invoice_date', 'Unknown') if invoice_info else 'Unknown'
                    
                    if product_name not in product_details:
                        product_details[product_name] = {
                            'product_name': product_name,
                            'cost_per_unit': cost_per_unit,
                            'barcode': item.get('barcode', 'Not available'),
                            'brand': item.get('brand', 'Unknown'),
                            'category': item.get('category', 'Unknown'),
                            'invoice_number': invoice_number,
                            'invoice_date': invoice_date,
                            'created_at': item.get('created_at', 'Unknown')
                        }
            
            return list(product_details.values())
            
        except Exception as e:
            logger.error(f"Error getting products for category {category}: {e}")
            return []
