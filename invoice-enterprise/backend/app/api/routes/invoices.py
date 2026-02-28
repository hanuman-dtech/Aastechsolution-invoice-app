"""
Invoice API routes - Main invoice generation endpoints.
"""

from datetime import date
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.logging import get_logger
from app.models import Invoice, InvoiceStatus, ExecutionMode
from app.schemas import (
    ExecutionSummary,
    InvoiceListResponse,
    InvoiceResponse,
    InvoiceWithCustomer,
    ManualDateOverrideRequest,
    QuickModeRequest,
    ResendEmailRequest,
    ScheduledRunRequest,
    WizardModeRequest,
)
from app.services import invoice_engine, email_service


logger = get_logger(__name__)
router = APIRouter(prefix="/invoices", tags=["Invoices"])


@router.post("/run/quick", response_model=ExecutionSummary)
async def run_quick_mode(
    request: QuickModeRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Quick mode invoice generation.
    
    Requires only 3 inputs:
    - Customer ID
    - Run date
    - Total hours
    """
    try:
        result = await invoice_engine.run_quick_mode(
            db=db,
            request=request,
            triggered_by="api",
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Quick mode error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Invoice generation failed: {str(e)}",
        )


@router.post("/run/wizard", response_model=ExecutionSummary)
async def run_wizard_mode(
    request: WizardModeRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Wizard mode invoice generation with full manual control.
    """
    try:
        result = await invoice_engine.run_wizard_mode(
            db=db,
            request=request,
            triggered_by="api",
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Wizard mode error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Invoice generation failed: {str(e)}",
        )


@router.post("/run/scheduled", response_model=ExecutionSummary)
async def run_scheduled(
    request: ScheduledRunRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Run scheduled invoice generation.
    
    Processes all customers whose schedule matches the run_date.
    Set ignore_schedule=true to generate for all customers.
    """
    try:
        result = await invoice_engine.run_scheduled(
            db=db,
            request=request,
            triggered_by="api",
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Scheduled run error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Invoice generation failed: {str(e)}",
        )


@router.post("/run/generate-all", response_model=ExecutionSummary)
async def run_generate_all(
    run_date: date = Query(default_factory=date.today),
    send_email: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate invoices for all active customers (ignoring schedules).
    """
    request = ScheduledRunRequest(
        run_date=run_date,
        ignore_schedule=True,
        send_email=send_email,
    )
    return await run_scheduled(request, db)


@router.post("/run/manual-override", response_model=ExecutionSummary)
async def run_manual_date_override(
    request: ManualDateOverrideRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Manual date override mode - specify exact billing period dates.
    """
    try:
        result = await invoice_engine.run_manual_date_override(
            db=db,
            request=request,
            triggered_by="api",
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Manual override error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Invoice generation failed: {str(e)}",
        )


@router.get("", response_model=InvoiceListResponse)
async def list_invoices(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    customer_id: Optional[str] = Query(default=None),
    status_filter: Optional[InvoiceStatus] = Query(default=None, alias="status"),
    start_date: Optional[date] = Query(default=None),
    end_date: Optional[date] = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """
    List invoices with pagination and filters.
    """
    query = select(Invoice).options(selectinload(Invoice.customer))
    count_query = select(func.count(Invoice.id))
    
    # Apply filters
    if customer_id:
        query = query.where(Invoice.customer_id == customer_id)
        count_query = count_query.where(Invoice.customer_id == customer_id)
    
    if status_filter:
        query = query.where(Invoice.status == status_filter)
        count_query = count_query.where(Invoice.status == status_filter)
    
    if start_date:
        query = query.where(Invoice.invoice_date >= start_date)
        count_query = count_query.where(Invoice.invoice_date >= start_date)
    
    if end_date:
        query = query.where(Invoice.invoice_date <= end_date)
        count_query = count_query.where(Invoice.invoice_date <= end_date)
    
    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Apply pagination
    offset = (page - 1) * per_page
    query = query.order_by(Invoice.invoice_date.desc()).offset(offset).limit(per_page)
    
    result = await db.execute(query)
    invoices = result.scalars().all()
    
    pages = (total + per_page - 1) // per_page
    
    return InvoiceListResponse(
        items=[InvoiceResponse.model_validate(inv) for inv in invoices],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.get("/{invoice_id}", response_model=InvoiceWithCustomer)
async def get_invoice(
    invoice_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get a single invoice by ID.
    """
    result = await db.execute(
        select(Invoice)
        .options(selectinload(Invoice.customer))
        .where(Invoice.id == invoice_id)
    )
    invoice = result.scalar_one_or_none()
    
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice not found: {invoice_id}",
        )
    
    return InvoiceWithCustomer.model_validate(invoice)


@router.get("/{invoice_id}/download")
async def download_invoice_pdf(
    invoice_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Download the PDF file for an invoice.
    """
    result = await db.execute(
        select(Invoice).where(Invoice.id == invoice_id)
    )
    invoice = result.scalar_one_or_none()
    
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice not found: {invoice_id}",
        )
    
    if not invoice.pdf_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF not found for this invoice",
        )
    
    pdf_path = Path(invoice.pdf_path)
    if not pdf_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF file not found on server",
        )
    
    return FileResponse(
        path=pdf_path,
        filename=pdf_path.name,
        media_type="application/pdf",
    )


@router.post("/{invoice_id}/resend-email")
async def resend_invoice_email(
    invoice_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Resend the email for an existing invoice.
    """
    result = await db.execute(
        select(Invoice)
        .options(
            selectinload(Invoice.customer).selectinload(Customer.vendor)
        )
        .where(Invoice.id == invoice_id)
    )
    invoice = result.scalar_one_or_none()
    
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice not found: {invoice_id}",
        )
    
    if not invoice.pdf_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot send email: PDF not found",
        )
    
    try:
        email_log = await email_service.send_invoice_email(
            db=db,
            invoice=invoice,
            attachment_path=Path(invoice.pdf_path),
        )
        
        # Update invoice status
        invoice.status = InvoiceStatus.SENT
        await db.commit()
        
        return {
            "success": True,
            "message": f"Email sent to {invoice.customer.email}",
            "email_log_id": email_log.id,
        }
    except Exception as e:
        logger.error(f"Failed to resend email: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send email: {str(e)}",
        )


@router.patch("/{invoice_id}/status")
async def update_invoice_status(
    invoice_id: str,
    new_status: InvoiceStatus,
    db: AsyncSession = Depends(get_db),
):
    """
    Update invoice status (e.g., mark as paid).
    """
    result = await db.execute(
        select(Invoice).where(Invoice.id == invoice_id)
    )
    invoice = result.scalar_one_or_none()
    
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice not found: {invoice_id}",
        )
    
    invoice.status = new_status
    await db.commit()
    
    return InvoiceResponse.model_validate(invoice)


# Import Customer model at module level
from app.models import Customer
