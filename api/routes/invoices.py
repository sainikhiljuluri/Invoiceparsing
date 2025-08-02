"""
Invoice processing routes
"""

import os
import logging
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, File, UploadFile, HTTPException, BackgroundTasks, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import aiofiles
import uuid

from services.pipeline_orchestrator import PipelineOrchestrator
from services.processing_queue import ProcessingQueue

logger = logging.getLogger(__name__)
router = APIRouter()

# Request/Response models
class InvoiceUploadResponse(BaseModel):
    invoice_id: str
    status: str
    message: str
    queue_position: Optional[int]

class InvoiceStatusResponse(BaseModel):
    invoice_id: str
    status: str
    progress: int
    current_step: str
    vendor: Optional[str]
    products_found: Optional[int]
    products_matched: Optional[int]
    alerts_generated: Optional[int]
    errors: List[str]
    created_at: datetime
    updated_at: datetime

@router.post("/upload", response_model=InvoiceUploadResponse)
async def upload_invoice(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    priority: int = Query(default=5, ge=1, le=10)
):
    """
    Upload an invoice for processing
    
    Priority: 1 (highest) to 10 (lowest)
    """
    # Validate file
    if not file.filename.endswith('.pdf'):
        raise HTTPException(400, "Only PDF files are supported")
    
    if file.size > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(400, "File size exceeds 10MB limit")
    
    try:
        # Generate unique ID
        invoice_id = str(uuid.uuid4())
        
        # Save uploaded file
        upload_dir = "uploads"
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, f"{invoice_id}_{file.filename}")
        
        # Read file content once
        content = await file.read()
        file_size = len(content)
        
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)
        
        # Get dependencies from app state
        from api.main import db, queue, pipeline
        
        # STEP 1: Create invoice record FIRST (required for FK constraint)
        try:
            invoice_data = {
                'id': invoice_id,
                'invoice_number': f'INV-{invoice_id[:8]}',
                'vendor_name': 'Processing...',
                'processing_status': 'queued'
            }
            
            result = db.supabase.table('invoices').insert(invoice_data).execute()
            logger.info(f"Invoice record created for {invoice_id}")
            
        except Exception as e:
            logger.error(f"Failed to create invoice record: {e}")
            return {"error": f"Failed to create invoice record: {str(e)}"}
        
        # STEP 2: Add to processing queue (now that invoice exists)
        try:
            queue_item = queue.add_to_queue({
                'id': invoice_id,
                'filename': file.filename,
                'file_path': file_path,
                'priority': priority,
                'file_size': file_size
            })
            logger.info(f"Invoice {invoice_id} added to processing queue")
            
        except Exception as e:
            logger.error(f"Queue insertion failed: {e}")
            return {"error": f"Failed to queue invoice for processing: {str(e)}"}
        
        # Get queue position
        position = queue.get_queue_position(invoice_id)
        
        # Process in background with full AI pipeline
        background_tasks.add_task(
            pipeline.process_invoice,
            invoice_id,
            file_path
        )
        logger.info(f"Invoice {invoice_id} queued for AI processing")
        
        return InvoiceUploadResponse(
            invoice_id=invoice_id,
            status="queued",
            message=f"Invoice queued for processing",
            queue_position=position
        )
        
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(500, f"Upload failed: {str(e)}")

@router.get("/{invoice_id}/status", response_model=InvoiceStatusResponse)
async def get_invoice_status(invoice_id: str):
    """Get the processing status of an invoice"""
    from api.main import db
    
    try:
        # Get invoice info
        result = db.supabase.table('invoices').select('*').eq('id', invoice_id).execute()
        
        if not result.data:
            raise HTTPException(404, "Invoice not found")
        
        invoice = result.data[0]
        
        # Calculate progress
        progress = 0
        current_step = "Queued"
        
        status = invoice.get('processing_status', 'queued')
        if status == 'processing':
            progress = 25
            current_step = "Extracting text"
        elif status == 'matching':
            progress = 50
            current_step = "Matching products"
        elif status == 'updating':
            progress = 75
            current_step = "Updating prices"
        elif status == 'completed':
            progress = 100
            current_step = "Completed"
        elif status == 'failed':
            progress = 0
            current_step = "Failed"
        
        return InvoiceStatusResponse(
            invoice_id=invoice_id,
            status=status,
            progress=progress,
            current_step=current_step,
            vendor=invoice.get('vendor_name'),
            products_found=invoice.get('products_found'),
            products_matched=invoice.get('products_matched'),
            alerts_generated=invoice.get('alerts_generated'),
            errors=queue_item.get('error_details', []),
            created_at=invoice.get('created_at'),
            updated_at=invoice.get('updated_at')
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Status check error: {e}")
        raise HTTPException(500, f"Status check failed: {str(e)}")

@router.get("/{invoice_id}/results")
async def get_invoice_results(invoice_id: str):
    """Get detailed results of processed invoice"""
    from api.main import db
    
    try:
        # Get invoice with all related data
        invoice_result = db.supabase.table('invoices').select(
            '*, vendors(name), invoice_items(*, products(name, brand))'
        ).eq('id', invoice_id).execute()
        
        if not invoice_result.data:
            raise HTTPException(404, "Invoice not found")
        
        invoice = invoice_result.data[0]
        
        # Get price updates
        updates_result = db.supabase.table('price_history').select(
            '*, products(name)'
        ).eq('invoice_id', invoice_id).execute()
        
        # Get alerts
        alerts_result = db.supabase.table('price_alerts').select(
            '*, products(name)'
        ).eq('invoice_id', invoice_id).execute()
        
        return {
            "invoice": {
                "id": invoice['id'],
                "number": invoice['invoice_number'],
                "date": invoice['invoice_date'],
                "vendor": invoice['vendors']['name'] if invoice.get('vendors') else None,
                "total": invoice['total_amount'],
                "status": invoice['processing_status']
            },
            "items": [
                {
                    "product_name": item['invoice_product_name'],
                    "matched_product": item['products']['name'] if item.get('products') else None,
                    "quantity": item['quantity'],
                    "unit_price": item['unit_price'],
                    "total": item['total_amount'],
                    "match_confidence": item.get('match_confidence')
                }
                for item in invoice.get('invoice_items', [])
            ],
            "price_updates": [
                {
                    "product": update['products']['name'] if update.get('products') else None,
                    "old_cost": update['old_cost'],
                    "new_cost": update['new_cost'],
                    "change_percentage": update['change_percentage']
                }
                for update in updates_result.data
            ],
            "alerts": [
                {
                    "type": alert['alert_type'],
                    "priority": alert['priority'],
                    "message": alert['alert_message'],
                    "product": alert['products']['name'] if alert.get('products') else None
                }
                for alert in alerts_result.data
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Results retrieval error: {e}")
        raise HTTPException(500, f"Failed to retrieve results: {str(e)}")

@router.get("/")
async def list_invoices(
    status: Optional[str] = None,
    vendor_id: Optional[str] = None,
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0)
):
    """List invoices with filtering"""
    from api.main import db
    
    try:
        query = db.supabase.table('invoices').select(
            'id, invoice_number, invoice_date, vendor_name, total_amount, processing_status, created_at'
        )
        
        if status:
            query = query.eq('processing_status', status)
        if vendor_id:
            query = query.eq('vendor_id', vendor_id)
        
        result = await query.order('created_at', desc=True).range(offset, offset + limit - 1).execute()
        
        return {
            "invoices": result.data,
            "total": len(result.data),
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"List invoices error: {e}")
        raise HTTPException(500, f"Failed to list invoices: {str(e)}")