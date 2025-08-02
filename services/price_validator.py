"""
Price validation service with business rules
"""

import logging
from typing import Dict, List, Tuple, Optional
from decimal import Decimal
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class PriceValidator:
    """Validate price changes according to business rules"""
    
    def __init__(self, config: Optional[Dict] = None):
        # Default validation rules
        self.config = config or {
            'max_increase_percentage': 50.0,  # 50% max increase
            'max_decrease_percentage': 30.0,  # 30% max decrease
            'min_cost': 0.01,
            'max_cost': 10000.00,
            'rapid_change_window_hours': 24,  # Flag rapid changes within 24 hours
            'rapid_change_threshold': 3,      # Max 3 changes in rapid window
        }
        
        # Currency-specific limits
        self.currency_limits = {
            'INR': {'min': 0.01, 'max': 100000.00},
            'USD': {'min': 0.01, 'max': 10000.00},
            'EUR': {'min': 0.01, 'max': 10000.00},
            'GBP': {'min': 0.01, 'max': 10000.00}
        }
    
    def validate_price_change(
        self, 
        old_cost: Optional[float], 
        new_cost: float, 
        currency: str = 'USD',
        price_history: Optional[List[Dict]] = None
    ) -> Tuple[bool, str, Dict]:
        """
        Validate a price change
        
        Returns:
            Tuple of (is_valid, validation_message, validation_details)
        """
        details = {
            'old_cost': old_cost,
            'new_cost': new_cost,
            'currency': currency,
            'checks_passed': [],
            'checks_failed': []
        }
        
        # Check 1: Basic bounds
        bounds_valid, bounds_msg = self._check_price_bounds(new_cost, currency)
        if not bounds_valid:
            details['checks_failed'].append('bounds_check')
            return False, bounds_msg, details
        details['checks_passed'].append('bounds_check')
        
        # Check 2: First-time price (no old cost)
        if old_cost is None or old_cost == 0:
            details['checks_passed'].append('first_time_price')
            return True, "First price entry accepted", details
        
        # Check 3: No change
        if abs(new_cost - old_cost) < 0.001:
            details['checks_passed'].append('no_change')
            return True, "No price change", details
        
        # Check 4: Percentage change limits
        change_valid, change_msg, change_pct = self._check_percentage_change(
            old_cost, new_cost
        )
        details['change_percentage'] = change_pct
        
        if not change_valid:
            details['checks_failed'].append('percentage_change')
            return False, change_msg, details
        details['checks_passed'].append('percentage_change')
        
        # Check 5: Rapid change detection
        if price_history:
            rapid_valid, rapid_msg = self._check_rapid_changes(price_history)
            if not rapid_valid:
                details['checks_failed'].append('rapid_change')
                details['warning'] = rapid_msg
                # This is a warning, not a hard fail
            else:
                details['checks_passed'].append('rapid_change')
        
        # Check 6: Cross-vendor validation (if history available)
        if price_history and abs(change_pct) > 20:
            anomaly_msg = self._check_price_anomaly(
                new_cost, currency, price_history
            )
            if anomaly_msg:
                details['anomaly_warning'] = anomaly_msg
        
        return True, f"Price change of {change_pct:.1f}% validated", details
    
    def _check_price_bounds(self, cost: float, currency: str) -> Tuple[bool, str]:
        """Check if price is within acceptable bounds"""
        limits = self.currency_limits.get(
            currency, 
            {'min': self.config['min_cost'], 'max': self.config['max_cost']}
        )
        
        if cost < limits['min']:
            return False, f"Cost {cost} below minimum {limits['min']} {currency}"
        
        if cost > limits['max']:
            return False, f"Cost {cost} above maximum {limits['max']} {currency}"
        
        return True, "Price within bounds"
    
    def _check_percentage_change(
        self, 
        old_cost: float, 
        new_cost: float
    ) -> Tuple[bool, str, float]:
        """Check if percentage change is within limits"""
        change_pct = ((new_cost - old_cost) / old_cost) * 100
        
        if change_pct > self.config['max_increase_percentage']:
            return False, (
                f"Price increase of {change_pct:.1f}% exceeds "
                f"maximum allowed {self.config['max_increase_percentage']}%"
            ), change_pct
        
        if change_pct < -self.config['max_decrease_percentage']:
            return False, (
                f"Price decrease of {abs(change_pct):.1f}% exceeds "
                f"maximum allowed {self.config['max_decrease_percentage']}%"
            ), change_pct
        
        return True, "Percentage change within limits", change_pct
    
    def _check_rapid_changes(self, price_history: List[Dict]) -> Tuple[bool, str]:
        """Check for rapid price changes"""
        window_start = datetime.now() - timedelta(
            hours=self.config['rapid_change_window_hours']
        )
        
        recent_changes = [
            h for h in price_history 
            if datetime.fromisoformat(h['created_at'].replace('Z', '+00:00')) > window_start
        ]
        
        if len(recent_changes) >= self.config['rapid_change_threshold']:
            return False, (
                f"Rapid price changes detected: {len(recent_changes)} changes "
                f"in last {self.config['rapid_change_window_hours']} hours"
            )
        
        return True, "No rapid changes detected"
    
    def _check_price_anomaly(
        self, 
        new_cost: float, 
        currency: str, 
        price_history: List[Dict]
    ) -> Optional[str]:
        """Check if price is anomalous compared to history"""
        # Get recent prices in same currency
        recent_prices = [
            h['new_cost'] for h in price_history[-10:]  # Last 10 entries
            if h.get('currency') == currency and h.get('new_cost')
        ]
        
        if len(recent_prices) < 3:
            return None
        
        avg_price = sum(recent_prices) / len(recent_prices)
        std_dev = (
            sum((p - avg_price) ** 2 for p in recent_prices) / len(recent_prices)
        ) ** 0.5
        
        # Check if new price is more than 2 standard deviations away
        if std_dev > 0 and abs(new_cost - avg_price) > 2 * std_dev:
            return (
                f"Price {new_cost} {currency} is significantly different from "
                f"recent average {avg_price:.2f} {currency}"
            )
        
        return None