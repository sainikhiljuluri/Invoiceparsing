"""
Entity extraction from queries
"""

import re
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dateutil import parser


class EntityExtractor:
    """Extract entities from user queries"""
    
    def __init__(self, supabase_client):
        self.client = supabase_client
        self._load_entity_lists()
    
    def _load_entity_lists(self):
        """Load known entities from database"""
        try:
            # Load products
            products = self.client.table('products').select('name').execute()
            self.known_products = [p['name'].lower() for p in products.data]
            
            # Load vendors
            vendors = self.client.table('vendors').select('name').execute()
            self.known_vendors = [v['name'].lower() for v in vendors.data]
        except Exception as e:
            print(f"Error loading entity lists: {e}")
            self.known_products = []
            self.known_vendors = []
    
    async def extract(self, query: str) -> Dict[str, Any]:
        """Extract all entities from query"""
        entities = {}
        
        # Extract products
        products = self._extract_products(query)
        if products:
            entities['products'] = products
        
        # Extract vendors
        vendors = self._extract_vendors(query)
        if vendors:
            entities['vendors'] = vendors
        
        # Extract dates
        dates = self._extract_dates(query)
        if dates:
            entities['dates'] = dates
        
        # Extract amounts
        amounts = self._extract_amounts(query)
        if amounts:
            entities['amounts'] = amounts
        
        # Extract time periods
        period = self._extract_time_period(query)
        if period:
            entities['time_period'] = period
        
        # Extract invoice numbers
        invoice_numbers = self._extract_invoice_numbers(query)
        if invoice_numbers:
            entities['invoice_numbers'] = invoice_numbers
        
        return entities
    
    def _extract_products(self, query: str) -> List[str]:
        """Extract product names with improved fuzzy matching"""
        query_lower = query.lower()
        found = []
        
        # Extract key terms from query
        query_words = [word for word in query_lower.split() if len(word) > 2]
        
        # Try direct database search with key terms - check both products and invoice_items
        for word in query_words:
            if len(word) > 3:  # Only search meaningful words
                # First check invoice_items table for actual purchased products
                try:
                    invoice_result = self.client.table('invoice_items').select('product_name').ilike(
                        'product_name', f'%{word}%'
                    ).limit(10).execute()
                    
                    for item in invoice_result.data:
                        product_name = item['product_name']
                        product_lower = product_name.lower()
                        
                        # Score the match based on word overlap
                        product_words = product_lower.split()
                        score = sum(1 for qword in query_words if qword in product_words)
                        
                        # If good match (multiple words match), add it
                        if score >= 2 or (score >= 1 and len(query_words) <= 2):
                            if product_name not in found:
                                found.append(product_name)
                                
                except Exception:
                    pass
                
                # Then check products table
                try:
                    result = self.client.table('products').select('name').ilike(
                        'name', f'%{word}%'
                    ).limit(10).execute()
                    
                    for product in result.data:
                        product_name = product['name']
                        product_lower = product_name.lower()
                        
                        # Score the match based on word overlap
                        product_words = product_lower.split()
                        score = sum(1 for qword in query_words if qword in product_words)
                        
                        # If good match (multiple words match), add it
                        if score >= 2 or (score >= 1 and len(query_words) <= 2):
                            if product_name not in found:
                                found.append(product_name)
                                
                except Exception:
                    continue
        
        # If still no matches, try the old exact substring method
        if not found:
            for product in self.known_products:
                if product in query_lower:
                    try:
                        result = self.client.table('products').select('name').ilike(
                            'name', f'%{product}%'
                        ).limit(1).execute()
                        
                        if result.data:
                            found.append(result.data[0]['name'])
                    except Exception:
                        continue
        
        return found[:5]  # Limit to top 5 matches
    
    def _extract_vendors(self, query: str) -> List[str]:
        """Extract vendor names"""
        query_lower = query.lower()
        found = []
        
        for vendor in self.known_vendors:
            if vendor in query_lower:
                # Get original case
                try:
                    result = self.client.table('vendors').select('name').ilike(
                        'name', f'%{vendor}%'
                    ).limit(1).execute()
                    
                    if result.data:
                        found.append(result.data[0]['name'])
                except Exception:
                    continue
        
        return found
    
    def _extract_dates(self, query: str) -> List[str]:
        """Extract dates from query"""
        dates = []
        
        # Date patterns
        patterns = [
            r'\d{1,2}/\d{1,2}/\d{4}',
            r'\d{4}-\d{2}-\d{2}',
            r'\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            dates.extend(matches)
        
        return dates
    
    def _extract_amounts(self, query: str) -> List[float]:
        """Extract monetary amounts"""
        amounts = []
        
        # Amount patterns
        pattern = r'[₹$]\s*(\d+(?:,\d{3})*(?:\.\d{2})?)'
        matches = re.findall(pattern, query)
        
        for match in matches:
            try:
                amount = float(match.replace(',', ''))
                amounts.append(amount)
            except ValueError:
                pass
        
        return amounts
    
    def _extract_time_period(self, query: str) -> Optional[str]:
        """Extract time period references"""
        query_lower = query.lower()
        
        periods = {
            'today': 0,
            'yesterday': 1,
            'this week': 7,
            'last week': 14,
            'this month': 30,
            'last month': 60,
            'this year': 365
        }
        
        for period, days in periods.items():
            if period in query_lower:
                return period
        
        return None
    
    def _extract_invoice_numbers(self, query: str) -> List[str]:
        """Extract invoice numbers from query"""
        invoice_numbers = []
        
        # Pattern for invoice numbers like INV-2025-0087, INV-001, etc.
        patterns = [
            r'INV-\d{4}-\d{4}',  # INV-2025-0087
            r'INV-\d{3,}',       # INV-001, INV-12345
            r'invoice\s+(?:number\s+)?([A-Z0-9-]+)',  # invoice number ABC-123
            r'invoice\s+([A-Z0-9-]+)',  # invoice ABC-123
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0] if match[0] else match[1]
                invoice_numbers.append(match.upper())
        
        # Remove duplicates while preserving order
        seen = set()
        unique_invoices = []
        for inv in invoice_numbers:
            if inv not in seen:
                seen.add(inv)
                unique_invoices.append(inv)
        
        return unique_invoices
