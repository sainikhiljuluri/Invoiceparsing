"""
Component 8: Price Update Service
Orchestrates price updates with validation and history tracking
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from decimal import Decimal

from database.price_repository import PriceRepository
from services.alert_manager import AlertManager
from services.pricing_calculator import PriceCalculator

logger = logging.getLogger(__name__)


class PriceUpdater:
    """Service to handle product price updates from invoices"""
    
    def __init__(
        self, 
        price_repo: PriceRepository,
        alert_manager: Optional[AlertManager] = None,
        config: Optional[Dict] = None,
        db_connection = None
    ):
        self.price_repo = price_repo
        self.alert_manager = alert_manager
        self.config = config or {}
        self.db = db_connection
        self.pricing_calculator = PriceCalculator(db_connection) if db_connection else None
        
    def update_prices_from_invoice(
        self, 
        invoice_id: str,
        invoice_number: str,
        vendor_id: str,
        matched_products: List[Dict]
    ) -> Dict:
        """Update prices from invoice data"""
        results = {
            'updated': 0,
            'alerts_generated': 0,
            'errors': []
        }
        
        for product in matched_products:
            if not product['matched']:
                continue
                
            try:
                # Update product cost per unit (cost per individual item, not per box/package)
                old_cost_data = self.price_repo.get_current_product_cost(product['product_id'])
                old_cost = old_cost_data.get('cost') if old_cost_data else None
                
                # Use Claude's already-calculated cost per unit (Claude Component 6 does this correctly)
                new_cost = product.get('cost_per_unit')
                
                # Fallback: calculate if Claude didn't provide cost_per_unit
                if not new_cost:
                    unit_price = product.get('unit_price')
                    units_per_pack = product.get('units_per_pack', 1)
                    if unit_price and units_per_pack > 0:
                        new_cost = round(unit_price / units_per_pack, 2)
                    else:
                        new_cost = unit_price
                
                if new_cost and old_cost != new_cost:
                    # Record price history
                    history_data = {
                        'product_id': product['product_id'],
                        'old_cost': old_cost,
                        'new_cost': new_cost,
                        'currency': 'USD',  # Default currency
                        'invoice_id': invoice_id,
                        'invoice_number': invoice_number,
                        'vendor_id': vendor_id,
                        'change_reason': 'invoice_update'
                    }
                    self.price_repo.create_price_history_entry(history_data)
                    
                    # Update current cost
                    cost_data = {
                        'cost': new_cost,
                        'currency': 'USD',  # Default currency
                        'invoice_number': invoice_number,
                        'vendor_id': vendor_id
                    }
                    self.price_repo.update_product_cost(
                        product['product_id'],
                        cost_data
                    )
                    
                    results['updated'] += 1
                    
                    # Generate alert if significant change
                    if old_cost and abs(new_cost - old_cost) / old_cost > 0.1:  # 10% change
                        if self.alert_manager:
                            self.alert_manager.create_price_alert(
                                product_id=product['product_id'],
                                alert_type='significant_price_change',
                                message=f"Price changed from {old_cost} to {new_cost}",
                                priority='medium',
                                invoice_id=invoice_id
                            )
                            results['alerts_generated'] += 1
                            
            except Exception as e:
                logger.error(f"Error updating price for {product['product_id']}: {e}")
                results['errors'].append(str(e))
        
        return results
    
    def update_product_price(
        self,
        product_id: str,
        new_cost: float,
        currency: str,
        invoice_id: str,
        invoice_number: str,
        vendor_id: Optional[str] = None,
        update_reason: str = 'invoice_update'
    ) -> Dict:
        """
        Update a single product's price with validation
        
        Returns:
            Update result with status and details
        """
        result = {
            'product_id': product_id,
            'status': 'pending',
            'old_cost': None,
            'new_cost': new_cost,
            'currency': currency,
            'change_percentage': None,
            'validation_details': {},
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            # Get current product info
            current = self.price_repo.get_current_product_cost(product_id)
            if not current:
                result['status'] = 'failed'
                result['error'] = 'Product not found'
                return result
            
            result['product_name'] = current['name']
            result['old_cost'] = current.get('cost')
            
            # Get price history for validation
            price_history = self.price_repo.get_price_history(product_id, days=30)
            
            # Validate the price change
            is_valid, message, validation_details = self.validator.validate_price_change(
                old_cost=current.get('cost'),
                new_cost=new_cost,
                currency=currency,
                price_history=price_history
            )
            
            result['validation_details'] = validation_details
            result['change_percentage'] = validation_details.get('change_percentage')
            
            if not is_valid:
                result['status'] = 'skipped'
                result['reason'] = message
                logger.warning(f"Price validation failed for {product_id}: {message}")
                return result
            
            # Check for warnings
            if validation_details.get('warning'):
                result['warning'] = validation_details['warning']
            
            # Update the product cost
            cost_updated = self.price_repo.update_product_cost(
                product_id,
                {
                    'cost': new_cost,
                    'currency': currency,
                    'invoice_number': invoice_number,
                    'vendor_id': vendor_id
                }
            )
            
            if not cost_updated:
                result['status'] = 'failed'
                result['error'] = 'Failed to update product cost'
                return result
            
            # Create price history entry
            history_created = self.price_repo.create_price_history_entry({
                'product_id': product_id,
                'old_cost': current.get('cost'),
                'new_cost': new_cost,
                'currency': currency,
                'change_percentage': result['change_percentage'],
                'invoice_id': invoice_id,
                'invoice_number': invoice_number,
                'vendor_id': vendor_id,
                'change_reason': update_reason
            })
            
            if not history_created:
                logger.warning(f"Failed to create price history for {product_id}")
            
            result['status'] = 'updated'
            result['message'] = message
            
            # Check for anomalies or trends
            if abs(result.get('change_percentage', 0)) > 10:
                trends = self.price_repo.get_price_trends(product_id)
                if trends['volatility'] == 'high':
                    result['alert'] = f"High price volatility detected: {trends['volatility']}"
            
            logger.info(
                f"Updated price for {product_id}: "
                f"{current.get('cost')} → {new_cost} {currency} "
                f"({result.get('change_percentage', 0):.1f}% change)"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error updating price for {product_id}: {e}")
            result['status'] = 'failed'
            result['error'] = str(e)
            return result
    
    def bulk_update_prices(
        self,
        price_updates: List[Dict],
        validation_mode: str = 'strict'
    ) -> Dict:
        """
        Bulk update prices with different validation modes
        
        Args:
            price_updates: List of price update dictionaries
            validation_mode: 'strict', 'relaxed', or 'force'
        """
        # Temporarily adjust validator based on mode
        original_config = self.validator.config.copy()
        
        if validation_mode == 'relaxed':
            self.validator.config['max_increase_percentage'] = 100.0
            self.validator.config['max_decrease_percentage'] = 50.0
        elif validation_mode == 'force':
            self.validator.config['max_increase_percentage'] = 999.0
            self.validator.config['max_decrease_percentage'] = 99.0
        
        results = {
            'total': len(price_updates),
            'updated': 0,
            'skipped': 0,
            'failed': 0,
            'details': []
        }
        
        for update in price_updates:
            result = self.update_product_price(**update)
            results['details'].append(result)
            
            if result['status'] == 'updated':
                results['updated'] += 1
            elif result['status'] == 'skipped':
                results['skipped'] += 1
            else:
                results['failed'] += 1
        
        # Restore original config
        self.validator.config = original_config
        
        return results
    
    def update_product_costs_with_pricing(self, matched_products: List[Dict], 
                                        invoice_info: Dict) -> Dict:
        """Update costs and calculate suggested selling prices"""
        
        results = {
            'updated': 0,
            'skipped': 0,
            'failed': 0,
            'updates': [],
            'pricing_suggestions': []
        }
        
        for product in matched_products:
            if product['routing'] == 'auto_approve':
                # Update cost using existing method
                update_result = self._update_single_product(
                    product_id=product['product_id'],
                    new_cost=product['cost_per_unit'],
                    invoice_info=invoice_info
                )
                
                # Calculate suggested selling price if pricing calculator is available
                if self.pricing_calculator and product.get('cost_per_unit'):
                    try:
                        product_info = {
                            'product_name': product['product_name'],
                            'cost_per_unit': product['cost_per_unit'],
                            'brand': product.get('brand'),
                            'category': product.get('category'),
                            'units': product.get('units_per_box', 1)
                        }
                        
                        pricing = self.pricing_calculator.calculate_suggested_price(product_info)
                        
                        # Store pricing suggestion if successful
                        if pricing.get('success'):
                            self._store_pricing_suggestion(
                                product['product_id'], 
                                pricing,
                                invoice_info.get('invoice_number')
                            )
                            results['pricing_suggestions'].append({
                                'product_name': product['product_name'],
                                'cost_price': product['cost_per_unit'],
                                'suggested_price': pricing['suggested_price'],
                                'markup_percentage': pricing['markup_percentage'],
                                'category': pricing['category'],
                                'confidence': pricing['confidence']
                            })
                            
                            logger.info(f"Calculated suggested price for {product['product_name']}: "
                                       f"₹{pricing['suggested_price']:.2f} ({pricing['markup_percentage']:.1f}% markup)")
                    
                    except Exception as e:
                        logger.warning(f"Failed to calculate pricing for {product['product_name']}: {e}")
                
                # Update results based on cost update status
                if update_result.get('status') == 'updated':
                    results['updated'] += 1
                elif update_result.get('status') == 'skipped':
                    results['skipped'] += 1
                else:
                    results['failed'] += 1
                
                results['updates'].append(update_result)
        
        return results
    
    def _update_single_product(self, product_id: str, new_cost: float, invoice_info: Dict) -> Dict:
        """Update single product cost (simplified version for pricing integration)"""
        try:
            # Get current cost
            old_cost_data = self.price_repo.get_current_product_cost(product_id)
            old_cost = old_cost_data.get('cost') if old_cost_data else None
            
            if old_cost != new_cost:
                # Update the product cost
                cost_updated = self.price_repo.update_product_cost(
                    product_id,
                    {
                        'cost': new_cost,
                        'currency': 'USD',
                        'invoice_number': invoice_info.get('invoice_number'),
                        'vendor_id': invoice_info.get('vendor_id')
                    }
                )
                
                if cost_updated:
                    return {
                        'status': 'updated',
                        'product_id': product_id,
                        'old_cost': old_cost,
                        'new_cost': new_cost
                    }
                else:
                    return {
                        'status': 'failed',
                        'product_id': product_id,
                        'error': 'Failed to update product cost'
                    }
            else:
                return {
                    'status': 'skipped',
                    'product_id': product_id,
                    'reason': 'Cost unchanged'
                }
                
        except Exception as e:
            logger.error(f"Error updating product {product_id}: {e}")
            return {
                'status': 'failed',
                'product_id': product_id,
                'error': str(e)
            }
    
    def _store_pricing_suggestion(self, product_id: str, pricing: Dict, invoice_number: str):
        """Store pricing suggestion in database"""
        if not self.db or not pricing.get('success'):
            return
        
        try:
            # Store in product_pricing table
            pricing_data = {
                'product_id': product_id,
                'cost_price': pricing['cost_per_unit'],
                'suggested_price': pricing['suggested_price'],
                'min_price': pricing['min_price'],
                'max_price': pricing['max_price'],
                'markup_percentage': pricing['markup_percentage'],
                'adjustments': {
                    'category': pricing['category'],
                    'confidence': pricing['confidence'],
                    'strategy': pricing['pricing_strategy'],
                    'invoice_number': invoice_number,
                    'source': 'automatic_invoice_processing'
                }
            }
            
            self.db.supabase.table('product_pricing').insert(pricing_data).execute()
            
            # Update products table with suggested selling price
            self.db.supabase.table('products').update({
                'selling_price': pricing['suggested_price'],
                'last_price_update': 'now()'
            }).eq('id', product_id).execute()
            
            logger.info(f"Stored pricing suggestion for product {product_id}")
            
        except Exception as e:
            logger.error(f"Error storing pricing suggestion: {e}")