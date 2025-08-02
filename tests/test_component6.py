"""
Test Component 6 with Nikhil Invoice
"""
import asyncio
import os
from dotenv import load_dotenv
from components.invoice_processing.claude_processor import ClaudeInvoiceProcessor

# Load environment variables
load_dotenv()

async def test_nikhil_invoice():
    print("="*60)
    print("COMPONENT 6 TEST: Claude Invoice Processing")
    print("="*60)
    
    # Check for API key
    if not os.getenv('ANTHROPIC_API_KEY'):
        print("❌ Error: ANTHROPIC_API_KEY not found in .env")
        return
    
    # Initialize processor
    processor = ClaudeInvoiceProcessor()
    print("✅ Claude processor initialized")
    
    # Test with Nikhil invoice
    invoice_path = "uploads/Nikhilinvoice.pdf"
    
    if not os.path.exists(invoice_path):
        print(f"❌ Error: {invoice_path} not found")
        return
    
    print(f"\n📄 Processing: {invoice_path}")
    
    try:
        # Process invoice
        invoice = await processor.process_invoice(invoice_path)
        
        # Show results
        print("\n" + processor.generate_summary(invoice))
        
        # Save to database
        print("\n💾 Saving to database...")
        result = await processor.save_to_database(invoice)
        
        if result['success']:
            print(f"✅ Success! Invoice ID: {result['invoice_id']}")
        else:
            print(f"❌ Failed: {result['error']}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_nikhil_invoice())
