#!/usr/bin/env python3
"""
Simple test script to verify upload functionality without queue
"""

import os
import sys
import asyncio
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import aiofiles
import uuid

# Add project root to path
sys.path.append('/Users/sainikhiljuluri/Desktop/invoice-parser-supabase')

from database.connection import DatabaseConnection

app = FastAPI(title="Simple Upload Test")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/test-upload")
async def test_upload(file: UploadFile = File(...)):
    """Simple upload test without queue"""
    try:
        # Validate file
        if not file.filename.endswith('.pdf'):
            return {"error": "Only PDF files are supported"}
        
        # Generate unique ID
        invoice_id = str(uuid.uuid4())
        
        # Save file
        upload_dir = "uploads"
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, f"{invoice_id}_{file.filename}")
        
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # Test database connection
        db = DatabaseConnection()
        
        # Try to insert a simple invoice record
        invoice_data = {
            'id': invoice_id,
            'invoice_number': f'TEST-{invoice_id[:8]}',
            'vendor_name': 'Test Vendor',
            'processing_status': 'uploaded'
        }
        
        result = db.supabase.table('invoices').insert(invoice_data).execute()
        
        return {
            "success": True,
            "invoice_id": invoice_id,
            "filename": file.filename,
            "file_size": len(content),
            "file_path": file_path,
            "database_result": "success",
            "message": "Upload successful - database connection working!"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Upload failed"
        }

@app.get("/")
async def root():
    return {"message": "Simple upload test server", "endpoint": "/test-upload"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
