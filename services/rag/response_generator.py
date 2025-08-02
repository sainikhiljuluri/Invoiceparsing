"""
Response generation using Claude AI
"""

import os
import logging
from typing import Dict, List, Any, Optional
from anthropic import Anthropic

logger = logging.getLogger(__name__)


class ResponseGenerator:
    """Generate responses using Claude AI"""
    
    def __init__(self):
        self.client = Anthropic(
            api_key=os.getenv('ANTHROPIC_API_KEY')
        )
        self.model = os.getenv('CLAUDE_MODEL', 'claude-3-5-sonnet-20241022')
        self.temperature = float(os.getenv('RAG_TEMPERATURE', '0.7'))
    
    async def generate(self, query: str, intent: Dict, entities: Dict,
                      retrieved_info: Dict, context: List = None) -> Dict[str, Any]:
        """Generate response using Claude"""
        
        try:
            # Build prompt
            prompt = self._build_prompt(query, intent, entities, retrieved_info, context)
            
            # Generate response
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                temperature=self.temperature,
                messages=[{"role": "user", "content": prompt}]
            )
            
            answer = response.content[0].text
            
            # Generate follow-up suggestions
            suggestions = self._generate_suggestions(intent, entities)
            
            return {
                'answer': answer,
                'suggestions': suggestions,
                'intent': intent['type'],
                'confidence': intent['confidence'],
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Response generation error: {e}")
            return {
                'answer': "I'm sorry, I encountered an error generating a response.",
                'error': str(e),
                'success': False
            }
    
    def _build_prompt(self, query: str, intent: Dict, entities: Dict,
                     retrieved_info: Dict, context: List = None) -> str:
        """Build prompt for Claude"""
        
        prompt_parts = [
            "You are an AI assistant for an invoice processing system.",
            "Answer the user's question based on the provided information.",
            "",
            f"User Question: {query}",
            f"Intent: {intent['type']} (confidence: {intent['confidence']:.2f})",
            ""
        ]
        
        # Add entities
        if entities:
            prompt_parts.append("Entities found:")
            for entity_type, values in entities.items():
                prompt_parts.append(f"- {entity_type}: {values}")
            prompt_parts.append("")
        
        # Add retrieved information
        if retrieved_info.get('data'):
            prompt_parts.append("Relevant Information:")
            
            if intent['type'] == 'cost_query':
                for product, info in retrieved_info['data'].items():
                    cost = info.get('cost_per_unit', 0)
                    source = info.get('source', 'unknown')
                    product_name = info.get('product_name', product)
                    
                    # Show cost with source information
                    if source == 'invoice_items_table':
                        invoice_number = info.get('invoice_number', 'Unknown')
                        invoice_date = info.get('invoice_date', 'Unknown')
                        if invoice_date != 'Unknown' and len(invoice_date) > 10:
                            invoice_date = invoice_date[:10]  # Format date to YYYY-MM-DD
                        
                        prompt_parts.append(
                            f"- {product_name}: ₹{cost:.2f} per unit (from actual purchase)"
                        )
                        if invoice_number and invoice_date:
                            prompt_parts.append(f"- **Invoice Number**: {invoice_number}")
                            prompt_parts.append(f"- **Invoice Date**: {invoice_date}")
                            vendor_name = info.get('vendor_name', 'Unknown')
                            if vendor_name and vendor_name != 'Unknown':
                                prompt_parts.append(f"- **Vendor**: {vendor_name}")
            
            elif intent['type'] == 'pricing_query':
                data = retrieved_info['data']
                if 'pricing_result' in data:
                    pricing = data['pricing_result']
                    prompt_parts.append(f"Pricing calculation for {pricing['product_name']}:")
                    prompt_parts.append(f"- Cost Price: ₹{pricing['cost_per_unit']:.2f}")
                    if pricing.get('invoice_number') and pricing.get('invoice_date'):
                        prompt_parts.append(f"- **Invoice Number**: {pricing['invoice_number']}")
                        prompt_parts.append(f"- **Invoice Date**: {pricing['invoice_date']}")
                        if pricing.get('vendor_name'):
                            prompt_parts.append(f"- **Vendor**: {pricing['vendor_name']}")
                    prompt_parts.append(f"- Suggested Price: ₹{pricing['suggested_price']:.2f}")
                    prompt_parts.append(f"- Markup: {pricing['markup_percentage']:.1f}%")
                    prompt_parts.append(f"- Price Range: {pricing['price_range']}")
                    prompt_parts.append(f"- Category: {pricing['category']}")
                    prompt_parts.append(f"- Market Position: {pricing['competitor_analysis']['market_position']}")
                    prompt_parts.append(f"- Confidence: {pricing['confidence']}")
                    if pricing.get('adjustments'):
                        prompt_parts.append("Pricing adjustments applied:")
                        for adj in pricing['adjustments']:
                            prompt_parts.append(f"  • {adj}")
                    prompt_parts.append(f"Strategy: {pricing['pricing_strategy']}")
                elif 'guidance' in data:
                    prompt_parts.append(data['guidance'])
                    prompt_parts.append("\n**Examples:**")
                    for example in data['examples']:
                        prompt_parts.append(f"- {example}")
                    prompt_parts.append(f"\n{data['help_text']}")
                elif 'error' in data:
                    prompt_parts.append(f"Error: {data['error']}")
            
            elif intent['type'] == 'pricing_analysis':
                data = retrieved_info['data']
                if 'analysis_result' in data:
                    analysis = data['analysis_result']
                    if 'error' not in analysis:
                        prompt_parts.append(f"Pricing analysis for {data['product_name']}:")
                        if 'price_metrics' in analysis:
                            metrics = analysis['price_metrics']
                            prompt_parts.append(f"- Average cost: ₹{metrics.get('avg_cost', 0):.2f}")
                            prompt_parts.append(f"- Average selling price: ₹{metrics.get('avg_selling_price', 0):.2f}")
                            prompt_parts.append(f"- Cost trend: {metrics.get('cost_trend', 'stable')}")
                        if 'margin_analysis' in analysis:
                            margins = analysis['margin_analysis']
                            if 'avg_margin_percentage' in margins:
                                prompt_parts.append(f"- Average margin: {margins['avg_margin_percentage']:.1f}%")
                        if 'recommendations' in analysis:
                            prompt_parts.append("Recommendations:")
                            for rec in analysis['recommendations']:
                                prompt_parts.append(f"  • {rec}")
                    else:
                        prompt_parts.append(f"Analysis error: {analysis['error']}")
                elif 'error' in data:
                    prompt_parts.append(f"Error: {data['error']}")
            
            elif intent['type'] == 'bulk_pricing':
                data = retrieved_info['data']
                if 'bulk_pricing_results' in data:
                    results = data['bulk_pricing_results']
                    prompt_parts.append(f"Bulk pricing for {data['category']} category ({data['products_processed']} products):")
                    for result in results[:5]:  # Show top 5
                        if result.get('success'):
                            prompt_parts.append(f"- {result['product_name']}: ₹{result['suggested_price']:.2f} ({result['markup_percentage']:.1f}% markup)")
                elif 'error' in data:
                    prompt_parts.append(f"Error: {data['error']}")
                    
                    # Add recent purchase history if available
                    if 'recent_purchases' in info and len(info['recent_purchases']) > 1:
                        prompt_parts.append("  Recent purchase history:")
                        for purchase in info['recent_purchases'][:3]:
                            prompt_parts.append(
                                f"    - ₹{purchase['price']:.2f} on {purchase['date'][:10]} (Invoice: {purchase['invoice']})"
                            )
            
            elif intent['type'] == 'trend_analysis':
                if 'data' in retrieved_info and retrieved_info['data']:
                    prompt_parts.append("Recent product purchases and price information:")
                    
                    # Show product trends
                    for product_name, purchases in list(retrieved_info['data'].items())[:10]:
                        if purchases:
                            latest_purchase = purchases[0]  # Most recent
                            prompt_parts.append(
                                f"- {product_name}: ₹{latest_purchase['cost']:.2f} (Invoice: {latest_purchase['invoice_number']}, Date: {latest_purchase['date'][:10]})"
                            )
                            
                            # Show price history if multiple purchases
                            if len(purchases) > 1:
                                prompt_parts.append(f"  Recent purchase history:")
                                for purchase in purchases[:3]:
                                    prompt_parts.append(
                                        f"    - ₹{purchase['cost']:.2f} on {purchase['date'][:10]} (Invoice: {purchase['invoice_number']})"
                                    )
                
                elif 'raw_items' in retrieved_info and retrieved_info['raw_items']:
                    prompt_parts.append("Recent invoice items with pricing:")
                    for item in retrieved_info['raw_items'][:15]:
                        cost = item.get('cost_per_unit') or item.get('unit_price') or 0
                        invoice_info = item.get('invoices', {})
                        invoice_number = invoice_info.get('invoice_number', 'Unknown') if invoice_info else 'Unknown'
                        prompt_parts.append(
                            f"- {item['product_name']}: ₹{cost:.2f} (Invoice: {invoice_number}, Date: {item['created_at'][:10]})"
                        )
            
            elif intent['type'] == 'anomaly_check':
                if retrieved_info['data']:
                    prompt_parts.append("Detected anomalies:")
                    for anomaly in retrieved_info['data'][:5]:
                        prompt_parts.append(
                            f"- {anomaly['product_name']}: {anomaly['description']}"
                        )
                else:
                    prompt_parts.append("No significant anomalies detected.")
            
            elif intent['type'] == 'product_details':
                if retrieved_info['data']:
                    prompt_parts.append("Product Details:")
                    for product_name, details in retrieved_info['data'].items():
                        prompt_parts.append(f"**{product_name}:**")
                        prompt_parts.append(f"- Brand: {details['brand']}")
                        prompt_parts.append(f"- Category: {details['category']}")
                        if details.get('sub_category') and details['sub_category'] != 'Unknown':
                            prompt_parts.append(f"- Sub-category: {details['sub_category']}")
                        prompt_parts.append(f"- Barcode: {details['barcode']}")
                        if details.get('sku') and details['sku'] != 'Not available':
                            prompt_parts.append(f"- SKU: {details['sku']}")
                        if details.get('pack_size') and details['pack_size'] != 'Unknown':
                            prompt_parts.append(f"- Pack Size: {details['pack_size']}")
                        if details.get('cost') and details['cost'] > 0:
                            prompt_parts.append(f"- Cost: ₹{details['cost']:.2f}")
                        if details.get('price') and details['price'] > 0:
                            prompt_parts.append(f"- Price: ₹{details['price']:.2f}")
                        prompt_parts.append(f"- Status: {'Active' if details.get('is_active', True) else 'Inactive'}")
                        if details.get('is_discontinued', False):
                            prompt_parts.append(f"- DISCONTINUED")
                else:
                    prompt_parts.append("No product details found for the requested items.")
            
            prompt_parts.append("")
        
        # Add conversation context
        if context:
            prompt_parts.append("Previous conversation:")
            for turn in context[-3:]:  # Last 3 turns
                prompt_parts.append(f"User: {turn['user_query']}")
                prompt_parts.append(f"Assistant: {turn['assistant_response']}")
            prompt_parts.append("")
        
        prompt_parts.extend([
            "Instructions:",
            "- Provide a helpful, accurate response",
            "- Use the retrieved information when available",
            "- Be concise but informative",
            "- Format monetary amounts in Indian Rupees (₹)",
            "- If no relevant data is found, say so clearly"
        ])
        
        return "\n".join(prompt_parts)
    
    def _generate_suggestions(self, intent: Dict, entities: Dict) -> List[str]:
        """Generate follow-up suggestions"""
        
        suggestions = []
        
        if intent['type'] == 'cost_query':
            suggestions = [
                "Show price trends for this product",
                "Compare with other vendors",
                "Check for recent price changes"
            ]
        
        elif intent['type'] == 'trend_analysis':
            suggestions = [
                "Show anomalies in pricing",
                "Compare vendor performance",
                "Get cost optimization suggestions"
            ]
        
        elif intent['type'] == 'anomaly_check':
            suggestions = [
                "Show detailed anomaly analysis",
                "Get recommendations to fix issues",
                "View recent invoice processing"
            ]
        
        else:
            suggestions = [
                "Show recent invoice summary",
                "Check for price anomalies",
                "Compare vendor costs"
            ]
        
        return suggestions[:3]  # Return max 3 suggestions
