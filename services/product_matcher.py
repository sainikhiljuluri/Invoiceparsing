"""
Component 7: Advanced Product Matching System
Implements 6-strategy matching with confidence-based routing
"""

import re
import logging
from typing import Optional, Dict, List
from dataclasses import dataclass
from fuzzywuzzy import fuzz
import re
import json
from datetime import datetime
from database.product_repository import ProductRepository
from services.embedding_generator import EmbeddingGenerator
from config.database import get_supabase_client

logger = logging.getLogger(__name__)


@dataclass
class MatchResult:
    """Container for product match results"""
    matched: bool
    product_id: Optional[str]
    product_name: Optional[str]
    confidence: float
    strategy: str
    routing: str
    details: Dict
    alternatives: List[Dict] = None


class ProductMatcher:
    """
    Advanced product matching system with 6 strategies:
    1. Learned mappings (100% confidence)
    2. Exact barcode match
    3. Structured format (Brand+Product+Size)
    4. Advanced normalization
    5. AI semantic search
    6. Fuzzy string matching
    """
    
    def __init__(self, product_repo: ProductRepository, 
                 embedding_generator: Optional[EmbeddingGenerator] = None,
                 config: Optional[Dict] = None):
        self.product_repo = product_repo
        self.embedding_gen = embedding_generator or EmbeddingGenerator()
        
        # Use config if provided, otherwise use defaults
        default_thresholds = {
            'auto_approve': 0.90,     # Raised from 0.85 - only very high confidence matches
            'review_priority_2': 0.75, # Raised from 0.70 - good matches need review
            'review_priority_1': 0.60, # Raised from 0.30 - moderate matches need review
            'creation_queue': 0.0      # Below 0.60 - suggest creating new product
        }
        
        if config:
            self.thresholds = {
                'auto_approve': config.get('auto_approve_threshold', default_thresholds['auto_approve']),
                'review_priority_2': config.get('review_threshold', default_thresholds['review_priority_2']),
                'review_priority_1': default_thresholds['review_priority_1'],
                'creation_queue': default_thresholds['creation_queue']
            }
        else:
            self.thresholds = default_thresholds
        
        # Known brand list (should be loaded from database)
        self.known_brands = [
            'DEEP', 'HALDIRAM', "HALDIRAM'S", 'ANAND', 'DECCAN', 
            'VADILAL', 'BRITANNIA', 'PARLE', 'MTR', 'GITS', 
            'SWAD', 'LAXMI', 'SHAN', 'MDH', 'EVEREST', 'PATANJALI',
            'AMUL', 'MOTHER DAIRY', 'NESTLE', 'CADBURY'
        ]
    
    def match_product(self, product_info: Dict, vendor_id: Optional[str] = None) -> MatchResult:
        """
        Main matching function that tries all strategies
        
        Args:
            product_info: Dict with product_name, units, cost_per_unit, etc.
            vendor_id: Optional vendor ID for vendor-specific mappings
            
        Returns:
            MatchResult with confidence and routing information
        """
        product_name = product_info.get('product_name', '')
        if not product_name:
            return self._no_match_result("No product name provided")
        
        logger.info(f"Matching product: {product_name}")
        
        # Strategy 1: Check learned mappings (highest priority)
        learned_match = self._strategy_learned_mappings(product_name)
        if learned_match and learned_match.confidence >= 0.95:
            logger.info(f"Found learned mapping with confidence {learned_match.confidence}")
            return learned_match
        
        # Strategy 2: Exact barcode match (if barcode provided)
        if product_info.get('barcode'):
            barcode_match = self._strategy_barcode_match(product_info['barcode'])
            if barcode_match and barcode_match.matched:
                return barcode_match
        
        # Strategy 3: Structured format matching
        structured_match = self._strategy_structured_match(product_name)
        if structured_match and structured_match.confidence >= 0.85:
            return structured_match
        
        # Strategy 4: Advanced normalization
        normalized_match = self._strategy_normalized_match(product_name)
        if normalized_match and normalized_match.confidence >= 0.80:
            return normalized_match
        
        # Strategy 5: AI semantic search (if embeddings available)
        semantic_match = self._strategy_semantic_search(product_name)
        if semantic_match and semantic_match.confidence >= 0.75:
            return semantic_match
        
        # Strategy 6: Fuzzy string matching (fallback)
        fuzzy_match = self._strategy_fuzzy_match(product_name)
        if fuzzy_match and fuzzy_match.confidence >= 0.30:
            return fuzzy_match
        
        # No match found - send to creation queue
        return self._no_match_result(
            "No matching product found",
            alternatives=self._get_top_suggestions(product_name)
        )
    
    def _strategy_learned_mappings(self, product_name: str) -> Optional[MatchResult]:
        """Strategy 1: Check previously learned mappings"""
        mapping = self.product_repo.get_learned_mappings(product_name)
        
        if mapping:
            product = mapping['product']
            confidence = mapping['confidence']
            
            return MatchResult(
                matched=True,
                product_id=product['id'],
                product_name=product['name'],
                confidence=confidence,
                strategy='learned_mapping',
                routing=self._determine_routing(confidence),
                details={
                    'mapping_id': mapping['mapping_id'],
                    'original_confidence': confidence
                }
            )
        
        return None
    
    def _strategy_barcode_match(self, barcode: str) -> Optional[MatchResult]:
        """Strategy 2: Exact barcode matching"""
        product = self.product_repo.search_by_barcode(barcode)
        
        if product:
            return MatchResult(
                matched=True,
                product_id=product['id'],
                product_name=product['name'],
                confidence=1.0,  # Barcode match is 100% confident
                strategy='barcode_match',
                routing='auto_approve',
                details={'barcode': barcode}
            )
        
        return None
    
    def _strategy_structured_match(self, product_name: str) -> Optional[MatchResult]:
        """Strategy 3: Structured format matching (Brand + Product + Size)"""
        # Parse product structure
        parsed = self._parse_product_structure(product_name)
        
        if not parsed['brand']:
            return None
        
        # Search by brand and keywords
        products = self.product_repo.search_by_brand_and_keywords(
            parsed['brand'],
            parsed['keywords']
        )
        
        if not products:
            return None
        
        # Score each result
        best_match = None
        best_score = 0
        
        for product in products:
            score = self._calculate_structured_score(parsed, product)
            if score > best_score:
                best_score = score
                best_match = product
        
        if best_match and best_score >= 0.70:
            return MatchResult(
                matched=True,
                product_id=best_match['id'],
                product_name=best_match['name'],
                confidence=best_score,
                strategy='structured_match',
                routing=self._determine_routing(best_score),
                details={
                    'parsed_brand': parsed['brand'],
                    'matched_brand': best_match.get('brand'),
                    'keyword_matches': parsed['keywords']
                }
            )
        
        return None
    
    def _strategy_normalized_match(self, product_name: str) -> Optional[MatchResult]:
        """Strategy 4: Advanced normalization and matching"""
        # Normalize the product name
        normalized = self._normalize_product_name(product_name)
        
        # Try exact match on normalized name
        product = self.product_repo.search_by_exact_name(normalized)
        
        if product:
            # Calculate confidence based on how much normalization was needed
            original_clean = re.sub(r'[^a-zA-Z0-9\s]', '', product_name.upper())
            normalized_clean = re.sub(r'[^a-zA-Z0-9\s]', '', normalized)
            
            similarity = fuzz.ratio(original_clean, normalized_clean) / 100
            confidence = 0.85 * similarity  # Max 85% for normalized match
            
            return MatchResult(
                matched=True,
                product_id=product['id'],
                product_name=product['name'],
                confidence=confidence,
                strategy='normalized_match',
                routing=self._determine_routing(confidence),
                details={
                    'original': product_name,
                    'normalized': normalized
                }
            )
        
        return None
    
    def _strategy_semantic_search(self, product_name: str) -> Optional[MatchResult]:
        """Strategy 5: AI semantic search using embeddings"""
        if not self.embedding_gen.model:
            return None
        
        # Generate embedding for search query
        query_embedding = self.embedding_gen.generate_embedding(product_name)
        
        # Search by vector similarity
        similar_products = self.product_repo.search_by_vector_similarity(
            query_embedding,
            threshold=0.70
        )
        
        if not similar_products:
            return None
        
        # Best match is first result (already sorted by similarity)
        best_match = similar_products[0]
        confidence = best_match.get('similarity', 0.75)
        
        return MatchResult(
            matched=True,
            product_id=best_match['id'],
            product_name=best_match['name'],
            confidence=confidence,
            strategy='semantic_search',
            routing=self._determine_routing(confidence),
            details={
                'similarity_score': confidence,
                'alternatives': [
                    {'id': p['id'], 'name': p['name'], 'score': p.get('similarity', 0)}
                    for p in similar_products[1:4]  # Top 3 alternatives
                ]
            }
        )
    
    def _strategy_fuzzy_match(self, product_name: str) -> Optional[MatchResult]:
        """Strategy 6: Enhanced fuzzy string matching with brand awareness"""
        # Get all products for fuzzy matching
        all_products = self.product_repo.get_all_products_for_fuzzy_match()
        
        if not all_products:
            return None
        
        # Parse invoice product for brand and keywords
        invoice_parsed = self._parse_product_structure(product_name)
        
        # Calculate enhanced fuzzy scores
        matches = []
        for product in all_products:
            # Parse database product
            db_parsed = self._parse_product_structure(product['name'])
            
            # Multiple scoring methods
            ratio = fuzz.ratio(product_name.lower(), product['name'].lower())
            partial = fuzz.partial_ratio(product_name.lower(), product['name'].lower())
            token_sort = fuzz.token_sort_ratio(product_name.lower(), product['name'].lower())
            token_set = fuzz.token_set_ratio(product_name.lower(), product['name'].lower())
            
            # Base weighted average
            base_score = (ratio * 0.2 + partial * 0.2 + token_sort * 0.3 + token_set * 0.3) / 100
            
            # Brand bonus/penalty
            brand_bonus = 0.0
            if invoice_parsed['brand'] and db_parsed['brand']:
                if invoice_parsed['brand'].upper() == db_parsed['brand'].upper():
                    brand_bonus = 0.2  # 20% bonus for exact brand match
                else:
                    brand_bonus = -0.15  # 15% penalty for different brands
            
            # Keyword matching bonus
            keyword_bonus = 0.0
            if invoice_parsed['keywords'] and db_parsed['keywords']:
                common_keywords = set(invoice_parsed['keywords']) & set(db_parsed['keywords'])
                if common_keywords:
                    keyword_bonus = len(common_keywords) / max(len(invoice_parsed['keywords']), len(db_parsed['keywords'])) * 0.1
            
            # Size matching bonus
            size_bonus = 0.0
            if invoice_parsed['size'] and db_parsed['size']:
                try:
                    inv_size = float(invoice_parsed['size'])
                    db_size = float(db_parsed['size'])
                    if abs(inv_size - db_size) / max(inv_size, db_size) < 0.1:  # Within 10%
                        size_bonus = 0.1
                except:
                    pass
            
            # Final enhanced score
            enhanced_score = min(1.0, base_score + brand_bonus + keyword_bonus + size_bonus)
            
            # Higher threshold for better quality matches
            if enhanced_score >= 0.60:  # Raised from 0.30 to 0.60
                matches.append({
                    'product': product,
                    'score': enhanced_score,
                    'details': {
                        'ratio': ratio,
                        'partial': partial,
                        'token_sort': token_sort,
                        'token_set': token_set,
                        'brand_bonus': brand_bonus,
                        'keyword_bonus': keyword_bonus,
                        'size_bonus': size_bonus,
                        'base_score': base_score
                    }
                })
        
        if not matches:
            return None
        
        # Sort by score
        matches.sort(key=lambda x: x['score'], reverse=True)
        best_match = matches[0]
        
        return MatchResult(
            matched=True,
            product_id=best_match['product']['id'],
            product_name=best_match['product']['name'],
            confidence=best_match['score'],
            strategy='fuzzy_match',
            routing=self._determine_routing(best_match['score']),
            details=best_match['details'],
            alternatives=[
                {
                    'id': m['product']['id'],
                    'name': m['product']['name'],
                    'score': m['score']
                }
                for m in matches[1:4]  # Top 3 alternatives
            ]
        )
    
    def _parse_product_structure(self, product_name: str) -> Dict:
        """Parse product name into structured components"""
        result = {
            'brand': None,
            'keywords': [],
            'size': None,
            'unit': None
        }
        
        # Clean the name
        clean_name = product_name.strip().upper()
        
        # Check for known brands
        for brand in self.known_brands:
            if clean_name.startswith(brand.upper()):
                result['brand'] = brand
                # Remove brand from name
                clean_name = clean_name[len(brand):].strip()
                break
        
        # Extract size/unit (e.g., 500G, 1KG, 7OZ)
        size_pattern = r'(\d+(?:\.\d+)?)\s*(G|GM|GRAM|KG|KILOGRAM|OZ|OUNCE|L|LTR|LITRE|ML|LB|POUND)'
        size_match = re.search(size_pattern, clean_name)
        if size_match:
            result['size'] = size_match.group(1)
            result['unit'] = size_match.group(2)
            # Remove size from name
            clean_name = re.sub(size_pattern, '', clean_name).strip()
        
        # Remaining words are keywords
        keywords = clean_name.split()
        result['keywords'] = [k for k in keywords if len(k) > 2]  # Filter short words
        
        return result
    
    def _normalize_product_name(self, name: str) -> str:
        """Advanced product name normalization"""
        # Convert to uppercase
        normalized = name.upper()
        
        # Expand common abbreviations
        abbreviations = {
            r'\bGM\b': 'GRAM',
            r'\bKG\b': 'KILOGRAM', 
            r'\bLB\b': 'POUND',
            r'\bOZ\b': 'OUNCE',
            r'\bPKT\b': 'PACKET',
            r'\bPCS\b': 'PIECES',
            r'\bVEG\b': 'VEGETABLE',
            r'\bMTR\b': 'MTR',  # Keep brand names
            r'\bLTR\b': 'LITRE'
        }
        
        for abbr, full in abbreviations.items():
            normalized = re.sub(abbr, full, normalized)
        
        # Remove special characters except spaces
        normalized = re.sub(r'[^A-Z0-9\s]', ' ', normalized)
        
        # Clean up spaces
        normalized = ' '.join(normalized.split())
        
        return normalized
    
    def _calculate_structured_score(self, parsed: Dict, product: Dict) -> float:
        """Calculate match score for structured matching"""
        score = 0.0
        
        # Brand match (40% weight)
        if parsed['brand'] and product.get('brand'):
            if parsed['brand'].upper() == product['brand'].upper():
                score += 0.4
        
        # Keyword matches (40% weight)
        product_name_upper = product['name'].upper()
        matched_keywords = 0
        for keyword in parsed['keywords']:
            if keyword in product_name_upper:
                matched_keywords += 1
        
        if parsed['keywords']:
            keyword_score = matched_keywords / len(parsed['keywords'])
            score += 0.4 * keyword_score
        
        # Size match (20% weight)
        if parsed['size'] and product.get('size'):
            if parsed['size'] in product['size']:
                score += 0.2
        
        return score
    
    def _determine_routing(self, confidence: float) -> str:
        """Determine routing based on confidence score"""
        if confidence >= self.thresholds['auto_approve']:
            return 'auto_approve'
        elif confidence >= self.thresholds['review_priority_2']:
            return 'review_priority_2'
        elif confidence >= self.thresholds['review_priority_1']:
            return 'review_priority_1'
        else:
            return 'creation_queue'
    
    def _get_top_suggestions(self, product_name: str, limit: int = 5) -> List[Dict]:
        """Get top product suggestions for failed matches"""
        suggestions = []
        
        # Try fuzzy search with lower threshold
        all_products = self.product_repo.get_all_products_for_fuzzy_match()
        
        for product in all_products:
            score = fuzz.token_set_ratio(product_name.lower(), product['name'].lower()) / 100
            if score >= 0.20:  # Lower threshold for suggestions
                suggestions.append({
                    'id': product['id'],
                    'name': product['name'],
                    'score': score
                })
        
        # Sort and limit
        suggestions.sort(key=lambda x: x['score'], reverse=True)
        return suggestions[:limit]
    
    def route_for_review(self, match_result: MatchResult, product_info: Dict, invoice_id: str, invoice_item_id: str = None) -> bool:
        """Send item to human review queue"""
        try:
            supabase = get_supabase_client()
            
            # Determine priority based on routing
            priority_map = {
                'review_priority_1': 1,  # High priority (low confidence)
                'review_priority_2': 2,  # Medium priority (medium confidence)
                'creation_queue': 1      # High priority (needs new product)
            }
            
            priority = priority_map.get(match_result.routing, 2)
            
            # Get top suggestions for the review interface
            suggestions = self._get_top_suggestions(product_info.get('product_name', ''), limit=5)
            
            # Prepare review item data
            review_item = {
                'invoice_id': invoice_id,
                'product_name': product_info.get('product_name', ''),
                'confidence': match_result.confidence,
                'strategy': match_result.strategy,
                'routing': match_result.routing,
                'suggested_matches': suggestions,
                'metadata': {
                    'units': product_info.get('units', 0),
                    'cost_per_unit': product_info.get('cost_per_unit', 0),
                    'vendor': product_info.get('vendor', ''),
                    'original_text': product_info.get('original_text', ''),
                    'match_details': match_result.details
                }
            }
            
            # Insert into human_review_queue table
            result = supabase.table('human_review_queue').insert({
                'invoice_id': invoice_id,
                'invoice_item_id': invoice_item_id,
                'product_info': json.dumps(review_item),
                'priority': priority,
                'status': 'pending',
                'created_at': datetime.now().isoformat()
            }).execute()
            
            if result.data:
                logger.info(f"Sent item to review queue: {product_info.get('product_name', '')} (confidence: {match_result.confidence:.2f})")
                return True
            else:
                logger.error(f"Failed to send item to review queue: {result}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending item to review queue: {str(e)}")
            return False
    
    def _no_match_result(self, reason: str, alternatives: List[Dict] = None) -> MatchResult:
        """Create result for no match found"""
        return MatchResult(
            matched=False,
            product_id=None,
            product_name=None,
            confidence=0.0,
            strategy='no_match',
            routing='creation_queue',
            details={'reason': reason},
            alternatives=alternatives or []
        )