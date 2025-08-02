"""
Pipeline Orchestrator - Coordinates all components
"""

import logging
import asyncio
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from services.vendor_detector import VendorDetector
from components.invoice_processing.claude_processor import ClaudeInvoiceProcessor, ProcessedInvoice
from services.product_matcher import ProductMatcher
from services.price_updater import PriceUpdater
from database.product_repository import ProductRepository
from database.price_repository import PriceRepository
from services.embedding_generator import EmbeddingGenerator
from services.alert_manager import AlertManager
from parsers.pdf_extractor import PDFExtractor
from services.rule_manager import RuleManager
from services.pricing_calculator import PriceCalculator

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """
    Orchestrates the complete invoice processing pipeline
    Components flow: Upload → Vendor Detection → Claude Processing → 
                    Product Matching → Price Updates → Alerts
    
    Features:
    - Parallel processing for product matching and price updates
    - Advanced error handling with fallbacks
    - Performance metrics collection
    - Configuration management
    - Caching for vendor rules
    """
    
    def __init__(self, db_connection, config: Optional[Dict] = None):
        self.db = db_connection
        self.config = self._get_default_config()
        if config:
            self.config.update(config)
        
        # Performance tracking
        self.metrics = {
            'component_times': {},
            'success_rates': {},
            'confidence_scores': [],
            'review_requirements': 0,
            'processing_bottlenecks': []
        }
        
        # Initialize all components with configuration
        self.pdf_extractor = PDFExtractor()
        self.vendor_detector = VendorDetector()
        self.rule_manager = RuleManager()
        self.claude_processor = ClaudeInvoiceProcessor()
        
        # Repositories
        self.product_repo = ProductRepository(self.db.supabase)
        self.price_repo = PriceRepository(self.db.supabase)
        
        # Services with configuration
        self.embedding_gen = EmbeddingGenerator()
        self.product_matcher = ProductMatcher(
            self.product_repo, 
            self.embedding_gen,
            config=self.config.get('product_matching', {})
        )
        self.alert_manager = AlertManager(self.db.supabase)
        self.price_updater = PriceUpdater(
            self.price_repo, 
            alert_manager=self.alert_manager,
            config=self.config.get('price_updates', {})
        )
        
        # Caching
        self._vendor_rules_cache = {}
        
        # Thread pool for parallel processing
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        logger.info("Pipeline Orchestrator initialized with all components and configuration")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration for all components"""
        return {
            'claude_processing': {
                'max_tokens': 4000,
                'temperature': 0.0,
                'timeout': 60
            },
            'product_matching': {
                'auto_approve_threshold': 0.85,
                'review_threshold': 0.70,
                'matching_strategies': ['exact', 'fuzzy', 'semantic'],
                'enable_parallel': True
            },
            'price_updates': {
                'max_price_increase': 50.0,
                'require_approval_above': 30.0,
                'track_history': True,
                'enable_parallel': True
            },
            'performance': {
                'enable_metrics': True,
                'cache_vendor_rules': True,
                'parallel_processing': True
            }
        }
    
    def _track_component_time(self, component: str, start_time: float):
        """Track time spent in each component"""
        if self.config.get('performance', {}).get('enable_metrics', True):
            duration = time.time() - start_time
            if component not in self.metrics['component_times']:
                self.metrics['component_times'][component] = []
            self.metrics['component_times'][component].append(duration)
    
    def _track_confidence_score(self, score: float):
        """Track confidence scores for analysis"""
        if self.config.get('performance', {}).get('enable_metrics', True):
            self.metrics['confidence_scores'].append(score)
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics summary"""
        if not self.config.get('performance', {}).get('enable_metrics', True):
            return {'metrics_disabled': True}
        
        metrics_summary = {
            'average_component_times': {},
            'total_processing_time': 0,
            'average_confidence': 0,
            'review_rate': 0,
            'bottlenecks': []
        }
        
        # Calculate average times per component
        for component, times in self.metrics['component_times'].items():
            if times:
                metrics_summary['average_component_times'][component] = sum(times) / len(times)
                metrics_summary['total_processing_time'] += sum(times)
        
        # Calculate average confidence
        if self.metrics['confidence_scores']:
            metrics_summary['average_confidence'] = sum(self.metrics['confidence_scores']) / len(self.metrics['confidence_scores'])
        
        # Identify bottlenecks (components taking >5 seconds on average)
        for component, avg_time in metrics_summary['average_component_times'].items():
            if avg_time > 5.0:
                metrics_summary['bottlenecks'].append({
                    'component': component,
                    'average_time': avg_time
                })
        
        return metrics_summary
    
    async def process_invoice(self, invoice_id: str, file_path: str) -> Dict:
        """
        Process an invoice through the complete pipeline
        
        Args:
            invoice_id: Unique invoice ID
            file_path: Path to PDF file
            
        Returns:
            Processing results summary
        """
        logger.info(f"Starting pipeline for invoice {invoice_id}")
        
        results = {
            'invoice_id': invoice_id,
            'start_time': datetime.now(),
            'steps_completed': [],
            'errors': [],
            'status': 'processing'
        }
        
        try:
            # Update status to processing
            await self._update_invoice_status(invoice_id, 'processing', 'Starting processing')
            
            # Step 1: Vendor Detection with fallback
            logger.info("Step 1: Detecting vendor...")
            start_time = time.time()
            
            try:
                vendor_result = await self._detect_vendor(file_path)
            except Exception as e:
                logger.warning(f"Vendor detection failed: {e}. Using generic vendor.")
                vendor_result = {
                    'detected': True,
                    'vendor_key': 'GENERIC',
                    'vendor_name': 'Generic Vendor',
                    'confidence': 0.5,
                    'currency': 'USD',
                    'vendor_id': None
                }
            
            self._track_component_time('vendor_detection', start_time)
            results['vendor'] = vendor_result
            results['steps_completed'].append('vendor_detection')
            
            if not vendor_result['detected']:
                raise Exception(f"Could not detect vendor: {vendor_result.get('reason')}")
            
            # Step 2: Claude Processing with fallback
            logger.info(f"Step 2: Processing with Claude for {vendor_result['vendor_name']}...")
            await self._update_invoice_status(invoice_id, 'processing', 'Extracting invoice data')
            start_time = time.time()
            
            try:
                extraction_result = await self._process_with_claude(
                    file_path, 
                    vendor_result['vendor_key']
                )
            except Exception as e:
                logger.warning(f"Claude processing failed: {e}. Attempting fallback extraction.")
                extraction_result = await self._fallback_extraction(file_path)
            
            self._track_component_time('claude_processing', start_time)
            results['extraction'] = extraction_result
            results['steps_completed'].append('claude_extraction')
            
            if not extraction_result or not extraction_result.products:
                raise Exception("Failed to extract invoice data")
            
            # Save invoice to database
            invoice_data = await self._save_invoice(
                invoice_id,
                extraction_result,
                vendor_result
            )
            
            # Get the actual invoice ID from the saved invoice data
            # (this handles cases where we updated an existing invoice)
            actual_invoice_id = invoice_data['id']
            
            # Step 3: Product Matching with parallel processing
            logger.info("Step 3: Matching products...")
            await self._update_invoice_status(actual_invoice_id, 'matching', 'Matching products')
            start_time = time.time()
            
            # Convert products to products format for matching
            products_for_matching = [
                {
                    'product_name': item.product_name,
                    'quantity': item.quantity,
                    'unit_price': item.unit_price,
                    'total_price': item.total,
                    'cost_per_unit': item.cost_per_unit,  # Use Claude's calculated cost_per_unit
                    'units_per_pack': item.units_per_pack,  # Add units_per_pack field
                    'currency': extraction_result.currency or 'USD',
                    'units': item.units_per_pack or 1  # Use units_per_pack for units field
                }
                for item in extraction_result.products
            ]
            
            # Use parallel processing if enabled and multiple products
            if (self.config.get('product_matching', {}).get('enable_parallel', True) and 
                len(products_for_matching) > 1):
                matched_products = await self._match_products_parallel(
                    products_for_matching,
                    vendor_result['vendor_key']
                )
            else:
                matched_products = await self._match_products(
                    products_for_matching,
                    vendor_result['vendor_key']
                )
            
            # Track confidence scores
            for product in matched_products:
                if product.get('confidence'):
                    self._track_confidence_score(product['confidence'])
            
            self._track_component_time('product_matching', start_time)
            results['matching'] = {
                'total_products': len(extraction_result.products),
                'matched': len([p for p in matched_products if p['matched']]),
                'products': matched_products
            }
            results['steps_completed'].append('product_matching')
            
            # Save matched items to database
            await self._save_invoice_items(
                actual_invoice_id,
                matched_products,
                products_for_matching
            )
            
            # Step 4: Price Updates with parallel processing
            logger.info("Step 4: Updating prices...")
            await self._update_invoice_status(actual_invoice_id, 'updating', 'Updating prices')
            start_time = time.time()
            
            # Use parallel processing for price updates if enabled
            if (self.config.get('price_updates', {}).get('enable_parallel', True) and 
                len(matched_products) > 1):
                price_results = await self._update_prices_parallel(
                    actual_invoice_id,
                    extraction_result.invoice_number,
                    vendor_result['vendor_id'],
                    matched_products
                )
            else:
                price_results = await self._update_prices(
                    actual_invoice_id,
                    extraction_result.invoice_number,
                    vendor_result['vendor_id'],
                    matched_products
                )
            
            self._track_component_time('price_updates', start_time)
            results['price_updates'] = price_results
            results['steps_completed'].append('price_updates')
            
            # Step 5: Calculate Suggested Selling Prices
            logger.info("Step 5: Calculating suggested selling prices...")
            await self._update_invoice_status(actual_invoice_id, 'pricing', 'Calculating suggested prices')
            start_time = time.time()
            
            try:
                pricing_results = await self._calculate_suggested_prices(actual_invoice_id)
            except Exception as e:
                logger.warning(f"Pricing calculation failed: {e}. Continuing without pricing.")
                pricing_results = {'calculated': 0, 'errors': [str(e)]}
            
            self._track_component_time('pricing_calculation', start_time)
            results['pricing'] = pricing_results
            results['steps_completed'].append('pricing_calculation')
            
            # Step 6: Generate summary
            results['summary'] = {
                'vendor': vendor_result['vendor_name'],
                'invoice_number': extraction_result.invoice_number,
                'invoice_date': extraction_result.invoice_date,
                'total_amount': extraction_result.total_amount,
                'products_extracted': len(extraction_result.products),
                'products_matched': results['matching']['matched'],
                'prices_updated': price_results['updated'],
                'alerts_generated': price_results['alerts_generated']
            }
            
            # Update final status
            await self._update_invoice_status(
                actual_invoice_id, 
                'completed',
                'Processing completed successfully',
                results['summary']
            )
            
            results['status'] = 'completed'
            results['end_time'] = datetime.now()
            results['processing_time'] = (
                results['end_time'] - results['start_time']
            ).total_seconds()
            
            logger.info(f"Pipeline completed for invoice {invoice_id} in {results['processing_time']:.2f}s")
            
        except Exception as e:
            logger.error(f"Pipeline error for invoice {invoice_id}: {e}")
            results['errors'].append(str(e))
            results['status'] = 'failed'
            
            await self._update_invoice_status(
                invoice_id,
                'failed',
                f'Processing failed: {str(e)}'
            )
        
        return results
    
    async def _detect_vendor(self, file_path: str) -> Dict:
        """Detect vendor from invoice"""
        # Extract text for detection
        from parsers.pdf_extractor import PDFExtractor
        extractor = PDFExtractor()
        content = extractor.extract_text_from_pdf(file_path)
        
        # Detect vendor
        result = self.vendor_detector.detect_vendor(content.text)
        
        # Get vendor from database if detected
        if result['detected']:
            vendor_data = self.db.supabase.table('vendors').select('*').eq(
                'name', result['vendor_name']
            ).execute()
            
            if vendor_data.data:
                result['vendor_id'] = vendor_data.data[0]['id']
            else:
                # Create vendor if not exists
                new_vendor = self.db.supabase.table('vendors').insert({
                    'name': result['vendor_name'],
                    'currency': result['currency']
                }).execute()
                
                result['vendor_id'] = new_vendor.data[0]['id']
        
        return result
    
    async def _process_with_claude(self, file_path: str, vendor_key: str) -> Dict:
        """Process invoice with Claude"""
        # Process based on vendor
        result = await self.claude_processor.process_invoice(
            file_path,
            vendor_rules=vendor_key
        )
        
        return result
    
    async def _match_products(self, products: List[Dict], vendor_key: str) -> List[Dict]:
        """Match extracted products to database"""
        matched_products = []
        
        for product in products:
            match_result = self.product_matcher.match_product(
                product,
                vendor_id=vendor_key
            )
            
            matched_products.append({
                'original_name': product['product_name'],
                'matched': match_result.matched,
                'product_id': match_result.product_id,
                'product_name': match_result.product_name,
                'confidence': match_result.confidence,
                'strategy': match_result.strategy,
                'routing': match_result.routing,
                'unit_price': product.get('unit_price'),  # Price per box/package from vendor
                'units_per_pack': product.get('units_per_pack', 1),  # Units per package
                'cost_per_unit': product.get('cost_per_unit'),
                'currency': product.get('currency', 'USD'),
                'units': product.get('units', 1),
                'quantity': product.get('quantity', 1)
            })
        
        return matched_products
    
    async def _update_prices(
        self, 
        invoice_id: str,
        invoice_number: str,
        vendor_id: str,
        matched_products: List[Dict]
    ) -> Dict:
        """Update prices for matched products"""
        return self.price_updater.update_prices_from_invoice(
            invoice_id=invoice_id,
            invoice_number=invoice_number,
            vendor_id=vendor_id,
            matched_products=matched_products
        )
    
    async def _save_invoice(self, invoice_id: str, extraction_result: ProcessedInvoice, vendor_result: Dict) -> Dict:
        """Save invoice to database"""
        invoice_data = {
            'id': invoice_id,
            'invoice_number': extraction_result.invoice_number,
            'invoice_date': extraction_result.invoice_date,
            'vendor_id': vendor_result.get('vendor_id'),
            'vendor_name': vendor_result['vendor_name'],
            'total_amount': extraction_result.total_amount,
            'subtotal': getattr(extraction_result, 'subtotal', None),
            'tax_amount': getattr(extraction_result, 'tax_amount', None),
            'currency': extraction_result.currency or vendor_result.get('currency', 'USD'),
            'processing_status': 'processing',
            'extraction_method': 'claude',
            'created_at': datetime.now().isoformat()
        }
        
        # Try to upsert, but handle duplicate invoice_number gracefully
        try:
            result = self.db.supabase.table('invoices').upsert(invoice_data).execute()
        except Exception as e:
            if 'duplicate key value violates unique constraint' in str(e):
                # If duplicate invoice number, update the existing record by invoice_number
                # and remove the id from invoice_data to avoid conflicts
                update_data = {k: v for k, v in invoice_data.items() if k != 'id'}
                result = self.db.supabase.table('invoices').update(update_data).eq('invoice_number', invoice_data['invoice_number']).execute()
                # If we updated an existing record, we need to get its actual ID for foreign key references
                if result.data and len(result.data) > 0:
                    # Update our invoice_id to match the existing record's ID
                    actual_invoice_id = result.data[0]['id']
                    # Store the actual ID for later use in invoice_items
                    invoice_data['id'] = actual_invoice_id
            else:
                raise e
        
        # Handle case where result.data might be empty
        if result.data and len(result.data) > 0:
            return result.data[0]
        else:
            # If no data returned, return the invoice_data we tried to save
            return invoice_data
    
    async def _save_invoice_items(
        self, 
        invoice_id: str, 
        matched_products: List[Dict],
        original_products: List[Dict]
    ):
        """Save invoice items to database"""
        # First, clean up any existing invoice items for this invoice to prevent duplication
        self.db.supabase.table('invoice_items').delete().eq('invoice_id', invoice_id).execute()
        
        items = []
        
        for i, (matched, original) in enumerate(zip(matched_products, original_products)):
            item = {
                'invoice_id': invoice_id,
                'line_number': i + 1,
                'product_name': original['product_name'],  # Add the required product_name field
                'invoice_product_name': original['product_name'],
                'product_id': matched['product_id'] if matched['matched'] else None,
                'quantity': original.get('quantity', 1),
                'units': original.get('units_per_pack', 1),  # Use units_per_pack from Claude
                'unit_price': original.get('unit_price', 0),
                'total_price': original.get('total', 0),  # Changed from total_amount to total_price
                'total_amount': original.get('total', 0),
                'cost_per_unit': original.get('cost_per_unit'),
                'match_confidence': matched['confidence'],
                'match_strategy': matched['strategy'],
                'routing': matched['routing']
            }
            items.append(item)
        
        if items:
            self.db.supabase.table('invoice_items').insert(items).execute()
    
    async def _update_invoice_status(
        self, 
        invoice_id: str, 
        status: str, 
        message: str,
        summary: Optional[Dict] = None
    ):
        """Update invoice processing status"""
        update_data = {
            'processing_status': status,
            'status_message': message,
            'updated_at': datetime.now().isoformat()
        }
        
        if summary:
            update_data.update({
                'products_found': summary.get('products_extracted'),
                'products_matched': summary.get('products_matched'),
                'alerts_generated': summary.get('alerts_generated')
            })
        
        self.db.supabase.table('invoices').update(
            update_data
        ).eq('id', invoice_id).execute()
        
        # Update queue status
        self.db.supabase.table('processing_queue').update({
            'status': status,
            'updated_at': datetime.now().isoformat()
        }).eq('invoice_id', invoice_id).execute()
    
    async def _match_products_parallel(self, products: List[Dict], vendor_key: str) -> List[Dict]:
        """Match products in parallel for better performance"""
        logger.info(f"Matching {len(products)} products in parallel")
        
        async def match_single_product(product):
            """Match a single product"""
            try:
                match_result = self.product_matcher.match_product(
                    product,
                    vendor_id=vendor_key
                )
                
                return {
                    'original_name': product['product_name'],
                    'matched': match_result.matched,
                    'product_id': match_result.product_id,
                    'product_name': match_result.product_name,
                    'confidence': match_result.confidence,
                    'strategy': match_result.strategy,
                    'routing': match_result.routing,
                    'unit_price': product.get('unit_price'),
                    'units_per_pack': product.get('units_per_pack', 1),
                    'cost_per_unit': product.get('cost_per_unit'),
                    'currency': product.get('currency', 'USD'),
                    'units': product.get('units', 1),
                    'quantity': product.get('quantity', 1)
                }
            except Exception as e:
                logger.error(f"Error matching product {product['product_name']}: {e}")
                return {
                    'original_name': product['product_name'],
                    'matched': False,
                    'product_id': None,
                    'product_name': None,
                    'confidence': 0.0,
                    'strategy': 'error',
                    'routing': 'manual_review',
                    'unit_price': product.get('unit_price'),
                    'units_per_pack': product.get('units_per_pack', 1),
                    'cost_per_unit': product.get('cost_per_unit'),
                    'currency': product.get('currency', 'USD'),
                    'units': product.get('units', 1),
                    'quantity': product.get('quantity', 1),
                    'error': str(e)
                }
        
        # Execute matching in parallel
        tasks = [match_single_product(product) for product in products]
        matched_products = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions that occurred
        results = []
        for i, result in enumerate(matched_products):
            if isinstance(result, Exception):
                logger.error(f"Exception in parallel matching for product {i}: {result}")
                # Create a fallback result
                results.append({
                    'original_name': products[i]['product_name'],
                    'matched': False,
                    'product_id': None,
                    'product_name': None,
                    'confidence': 0.0,
                    'strategy': 'exception',
                    'routing': 'manual_review',
                    'error': str(result)
                })
            else:
                results.append(result)
        
        return results
    
    async def _update_prices_parallel(
        self, 
        invoice_id: str,
        invoice_number: str,
        vendor_id: str,
        matched_products: List[Dict]
    ) -> Dict:
        """Update prices in parallel for matched products"""
        logger.info(f"Updating prices for {len(matched_products)} products in parallel")
        
        # Filter only matched products for price updates
        products_to_update = [p for p in matched_products if p['matched'] and p['product_id']]
        
        if not products_to_update:
            return {
                'updated': 0,
                'alerts_generated': 0,
                'errors': [],
                'message': 'No matched products to update'
            }
        
        # For now, we'll use the existing price updater method
        # In a full parallel implementation, we'd break this down further
        return self.price_updater.update_prices_from_invoice(
            invoice_id=invoice_id,
            invoice_number=invoice_number,
            vendor_id=vendor_id,
            matched_products=matched_products
        )
    
    async def _fallback_extraction(self, file_path: str) -> ProcessedInvoice:
        """Fallback extraction when Claude fails"""
        logger.info("Attempting fallback extraction using template parser")
        
        try:
            # Extract text using PDF extractor
            content = self.pdf_extractor.extract_text_from_pdf(file_path)
            
            # Create a basic ProcessedInvoice with minimal data
            from components.invoice_processing.claude_processor import ProcessedInvoice, InvoiceItem
            
            # Try to extract basic information using simple patterns
            import re
            text = content.text
            
            # Extract invoice number
            invoice_number_match = re.search(r'(?:invoice|inv)\s*#?\s*:?\s*([A-Z0-9-]+)', text, re.IGNORECASE)
            invoice_number = invoice_number_match.group(1) if invoice_number_match else f"FALLBACK-{int(time.time())}"
            
            # Extract date
            date_match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', text)
            invoice_date = date_match.group(1) if date_match else datetime.now().strftime('%Y-%m-%d')
            
            # Extract total amount
            total_match = re.search(r'total\s*:?\s*\$?([0-9,]+\.?[0-9]*)', text, re.IGNORECASE)
            total_amount = float(total_match.group(1).replace(',', '')) if total_match else 0.0
            
            # Create a single generic item if we can't parse products
            fallback_item = InvoiceItem(
                product_name="Unknown Product (Fallback)",
                quantity=1,
                unit_price=total_amount,
                total=total_amount,
                units_per_pack=1,
                cost_per_unit=total_amount
            )
            
            return ProcessedInvoice(
                invoice_number=invoice_number,
                invoice_date=invoice_date,
                total_amount=total_amount,
                currency='USD',
                products=[fallback_item]
            )
            
        except Exception as e:
            logger.error(f"Fallback extraction failed: {e}")
            # Return minimal invoice to prevent complete failure
            from components.invoice_processing.claude_processor import ProcessedInvoice, InvoiceItem
            
            return ProcessedInvoice(
                invoice_number=f"ERROR-{int(time.time())}",
                invoice_date=datetime.now().strftime('%Y-%m-%d'),
                total_amount=0.0,
                currency='USD',
                products=[]
            )
    
    def _get_cached_vendor_rules(self, vendor_key: str) -> Optional[Dict]:
        """Get cached vendor rules if caching is enabled"""
        if not self.config.get('performance', {}).get('cache_vendor_rules', True):
            return None
        
        return self._vendor_rules_cache.get(vendor_key)
    
    def _cache_vendor_rules(self, vendor_key: str, rules: Dict):
        """Cache vendor rules if caching is enabled"""
        if self.config.get('performance', {}).get('cache_vendor_rules', True):
            self._vendor_rules_cache[vendor_key] = rules
    
    def cleanup(self):
        """Cleanup resources"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=True)
        logger.info("Pipeline Orchestrator cleaned up")
    
    async def _calculate_suggested_prices(self, invoice_id: str) -> Dict:
        """Calculate suggested selling prices for invoice products"""
        try:
            # Get invoice items with cost data
            invoice_items = self.db.supabase.table('invoice_items').select(
                'id, product_name, cost_per_unit, unit_price, units, product_id'
            ).eq('invoice_id', invoice_id).execute()
            
            if not invoice_items.data:
                return {'calculated': 0, 'message': 'No invoice items found'}
            
            calculator = PriceCalculator(self.db)
            recommendations = []
            calculated_count = 0
            
            for item in invoice_items.data:
                try:
                    cost_per_unit = item.get('cost_per_unit') or item.get('unit_price')
                    if not cost_per_unit or cost_per_unit <= 0:
                        continue
                    
                    # Prepare product data for pricing calculation
                    product_data = {
                        'product_name': item.get('product_name'),
                        'cost_per_unit': cost_per_unit,
                        'category': 'DEFAULT',  # Will be detected by calculator
                        'units': item.get('units', 1)
                    }
                    
                    # Calculate suggested price
                    pricing_result = calculator.calculate_suggested_price(product_data)
                    
                    if pricing_result.get('success'):
                        # Store pricing recommendation in database
                        pricing_data = {
                            'invoice_id': invoice_id,
                            'product_name': item.get('product_name'),
                            'cost_price': cost_per_unit,
                            'suggested_price': pricing_result['suggested_price'],
                            'min_price': pricing_result['min_price'],
                            'max_price': pricing_result['max_price'],
                            'markup_percentage': pricing_result['markup_percentage'],
                            'category': pricing_result['category'],
                            'confidence': pricing_result['confidence'],
                            'pricing_strategy': pricing_result['pricing_strategy'],
                            'adjustments': pricing_result.get('adjustments', []),
                            'created_at': datetime.now().isoformat(),
                            'is_active': True
                        }
                        
                        # Upsert pricing recommendation
                        self.db.supabase.table('pricing_recommendations').upsert(
                            pricing_data, on_conflict='invoice_id,product_name'
                        ).execute()
                        
                        recommendations.append({
                            'product_name': item.get('product_name'),
                            'cost_price': cost_per_unit,
                            'suggested_price': pricing_result['suggested_price'],
                            'markup_percentage': pricing_result['markup_percentage']
                        })
                        
                        calculated_count += 1
                        
                except Exception as e:
                    logger.warning(f"Failed to calculate price for {item.get('product_name', 'unknown')}: {e}")
                    continue
            
            logger.info(f"Calculated pricing for {calculated_count} products from invoice {invoice_id}")
            
            return {
                'calculated': calculated_count,
                'total_items': len(invoice_items.data),
                'recommendations': recommendations,
                'message': f'Successfully calculated pricing for {calculated_count} products'
            }
            
        except Exception as e:
            logger.error(f"Error calculating suggested prices for invoice {invoice_id}: {e}")
            return {
                'calculated': 0,
                'error': str(e),
                'message': f'Failed to calculate pricing: {str(e)}'
            }