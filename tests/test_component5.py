import asyncio
from components.c5_product_loader import ProductDataLoader

async def test():
    loader = ProductDataLoader()
    df = loader.load_excel_file('Milpitas_New.xlsx')
    
    # Show sample data
    print("\nSample Excel data:")
    sample = df[['Product Name', 'Price', 'Cost', 'Barcode']].head(5)
    print(sample)
    
    # Process first 5 products
    await loader.process_batch(df.head(5), 1)
    print(f"\nTest complete: {loader.stats}")

asyncio.run(test())