"""
Invoice Processing Orchestrator - Integration of Components 6, 7, and 8
Coordinates the complete flow from PDF invoice to price updates
"""

import logging
import asyncio
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass

# Component imports
from components.invoice_processing.claude_processor import ClaudeInvoiceProcessor
from services.product_matcher import ProductMatcher, MatchResult
from services.price_updater import PriceUpdater
from services.human_review_manager import HumanReviewManager
from database.connection import DatabaseConnection
from database.product_repository import ProductRepository
from database.price_repository import PriceRepository
from services.embedding_generator import EmbeddingGenerator
from services.price_validator import PriceValidator

logger = logging.getLogger(__name__)

@dataclass
class ProcessingResult:
    """Result of complete invoice processing"""
    invoice_id: str
    status: str  # 'completed', 'partial', 'failed'
    products_processed: int
    products_auto_approved: int
    products_needs_review: int
    products_created: int
    price_updates: int
    errors: List[str]
    processing_time: float

class InvoiceOrchestrator:
    """
    Orchestrates the complete invoice processing workflow:
    1. Component 6: Extract invoice data using Claude AI
    2. Component 7: Match products using advanced matching strategies
    3. Component 8: Update prices with validation and audit trail
    """
    
    def __init__(self):
        """Initialize all components"""
        self.db = DatabaseConnection()
        
        # Initialize repositories
        self.product_repo = ProductRepository(self.db.supabase)
        self.price_repo = PriceRepository(self.db.supabase)
        
        # Initialize services
        self.embedding_gen = EmbeddingGenerator()
        self.claude_processor = ClaudeInvoiceProcessor()
        self.product_matcher = ProductMatcher(self.product_repo, self.embedding_gen)
        self.price_validator = PriceValidator()
        self.price_updater = PriceUpdater(self.price_repo, self.price_validator)
        self.review_manager = HumanReviewManager(self.db.supabase)
        
        logger.info("Invoice orchestrator initialized with all components")
    
    async def process_invoice(self, pdf_path: str) -> ProcessingResult:
        """
        Process a complete invoice through all components
        
        Args:
            pdf_path: Path to the PDF invoice file
            
        Returns:
            ProcessingResult with complete processing statistics
        """
        start_time = datetime.now()
        errors = []
        
        try:
            logger.info(f"Starting complete invoice processing for: {pdf_path}")
            
            # Step 1: Component 6 - Extract invoice data using Claude
            logger.info("Step 1: Extracting invoice data with Claude AI...")
            processed_invoice = await self.claude_processor.process_invoice(pdf_path)
            
            if not processed_invoice:
                return ProcessingResult(
                    invoice_id="unknown",
                    status="failed",
                    products_processed=0,
                    products_auto_approved=0,
                    products_needs_review=0,
                    products_created=0,
                    price_updates=0,
                    errors=["Failed to extract invoice data"],
                    processing_time=0.0
                )
            
            logger.info(f"Extracted {len(processed_invoice.products)} products from invoice")
            
            # Step 2: Component 7 - Match products using advanced strategies
            logger.info("Step 2: Matching products using advanced strategies...")
            matched_products = []
            
            for product in processed_invoice.products:
                # Convert to format expected by product matcher
                product_info = {
                    'product_name': product.product_name,
                    'units': product.quantity,
                    'cost_per_unit': product.unit_price / product.quantity if product.quantity > 0 else product.unit_price,
                    'unit_price': product.unit_price,
                    'total': product.total,
                    'currency': processed_invoice.currency
                }
                
                # Match the product
                match_result = self.product_matcher.match_product(
                    product_info, 
                    vendor_id=processed_invoice.vendor.vendor_id
                )
                
                # Store matched product with routing info
                matched_product = {
                    'original_product': product,
                    'product_info': product_info,
                    'match_result': match_result,
                    'routing': match_result.routing
                }
                matched_products.append(matched_product)
                
                # Add to human review queue if needed
                if 'review' in match_result.routing:
                    await self._add_to_review_queue(matched_product, processed_invoice)
            
            # Step 3: Component 8 - Update prices for auto-approved products
            logger.info("Step 3: Updating prices for auto-approved products...")
            price_update_results = await self._update_prices(
                matched_products, 
                processed_invoice
            )
            
            # Calculate statistics
            stats = self._calculate_statistics(matched_products, price_update_results)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"Invoice processing completed in {processing_time:.2f} seconds")
            logger.info(f"Statistics: {stats['auto_approved']} auto-approved, "
                       f"{stats['needs_review']} need review, "
                       f"{stats['created']} need creation, "
                       f"{stats['price_updates']} price updates")
            
            return ProcessingResult(
                invoice_id=processed_invoice.invoice_id,
                status="completed",
                products_processed=len(matched_products),
                products_auto_approved=stats['auto_approved'],
                products_needs_review=stats['needs_review'],
                products_created=stats['created'],
                price_updates=stats['price_updates'],
                errors=errors,
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"Error in invoice processing: {e}")
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return ProcessingResult(
                invoice_id="unknown",
                status="failed",
                products_processed=0,
                products_auto_approved=0,
                products_needs_review=0,
                products_created=0,
                price_updates=0,
                errors=[str(e)],
                processing_time=processing_time
            )
    
    async def _add_to_review_queue(self, matched_product: Dict, invoice) -> None:
        """Add product to human review queue"""
        try:
            await self.review_manager.add_to_queue(
                invoice_id=invoice.invoice_id,
                product_name=matched_product['original_product'].product_name,
                extracted_data=matched_product['product_info'],
                match_candidates=matched_product['match_result'].alternatives,
                confidence=matched_product['match_result'].confidence,
                routing_reason=matched_product['match_result'].reason
            )
        except Exception as e:
            logger.error(f"Error adding to review queue: {e}")
    
    async def _update_prices(self, matched_products: List[Dict], invoice) -> Dict:
        """Update prices for auto-approved products"""
        update_results = {
            'updated': 0,
            'skipped': 0,
            'failed': 0,
            'details': []
        }
        
        for matched_product in matched_products:
            if matched_product['routing'] == 'auto_approve' and matched_product['match_result'].matched:
                try:
                    # Update price using Component 8
                    result = self.price_updater.update_product_price(
                        product_id=matched_product['match_result'].product_id,
                        new_cost=matched_product['product_info']['cost_per_unit'],
                        currency=matched_product['product_info']['currency'],
                        invoice_id=invoice.invoice_id,
                        invoice_number=invoice.invoice_number,
                        vendor_id=invoice.vendor.vendor_id
                    )
                    
                    if result['status'] == 'updated':
                        update_results['updated'] += 1
                    else:
                        update_results['skipped'] += 1
                    
                    update_results['details'].append(result)
                    
                except Exception as e:
                    logger.error(f"Error updating price for {matched_product['match_result'].product_id}: {e}")
                    update_results['failed'] += 1
        
        return update_results
    
    def _calculate_statistics(self, matched_products: List[Dict], price_results: Dict) -> Dict:
        """Calculate processing statistics"""
        stats = {
            'auto_approved': 0,
            'needs_review': 0,
            'created': 0,
            'price_updates': price_results.get('updated', 0)
        }
        
        for matched_product in matched_products:
            routing = matched_product['routing']
            if routing == 'auto_approve':
                stats['auto_approved'] += 1
            elif 'review' in routing:
                stats['needs_review'] += 1
            elif routing == 'creation_queue':
                stats['created'] += 1
        
        return stats
    
    async def get_processing_status(self, invoice_id: str) -> Dict:
        """Get current processing status for an invoice"""
        try:
            # Query database for invoice status
            invoice_query = self.db.supabase.table('invoices').select('*').eq('id', invoice_id).execute()
            
            if not invoice_query.data:
                return {'error': 'Invoice not found'}
            
            invoice = invoice_query.data[0]
            
            # Get review queue items
            review_items = await self.review_manager.get_pending_reviews(invoice_id=invoice_id)
            
            return {
                'invoice_id': invoice_id,
                'status': invoice.get('status', 'unknown'),
                'products_total': invoice.get('total_products', 0),
                'products_processed': invoice.get('processed_products', 0),
                'pending_reviews': len(review_items),
                'last_updated': invoice.get('updated_at')
            }
            
        except Exception as e:
            logger.error(f"Error getting processing status: {e}")
            return {'error': str(e)}
    
    async def process_batch(self, pdf_paths: List[str]) -> List[ProcessingResult]:
        """Process multiple invoices in batch"""
        results = []
        
        for pdf_path in pdf_paths:
            try:
                result = await self.process_invoice(pdf_path)
                results.append(result)
                
                # Add small delay between processing to avoid overwhelming the system
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error processing {pdf_path}: {e}")
                results.append(ProcessingResult(
                    invoice_id="unknown",
                    status="failed",
                    products_processed=0,
                    products_auto_approved=0,
                    products_needs_review=0,
                    products_created=0,
                    price_updates=0,
                    errors=[str(e)],
                    processing_time=0.0
                ))
        
        return results
