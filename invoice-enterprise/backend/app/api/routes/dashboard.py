"""
Dashboard API routes - Stats and overview data.
"""

from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.logging import get_logger
from app.models import (
    BillingFrequency,
    Customer,
    EmailLog,
    EmailStatus,
    ExecutionLog,
    Invoice,
    InvoiceStatus,
)
from app.schemas import DashboardStats, UpcomingInvoice
from app.services import schedule_service


logger = get_logger(__name__)
router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
):
    """
    Get dashboard statistics.
    """
    today = date.today()
    first_of_month = today.replace(day=1)
    
    # Total invoices this month
    invoices_result = await db.execute(
        select(func.count(Invoice.id))
        .where(Invoice.invoice_date >= first_of_month)
        .where(Invoice.status != InvoiceStatus.CANCELLED)
    )
    total_invoices = invoices_result.scalar() or 0
    
    # Total revenue this month
    revenue_result = await db.execute(
        select(func.sum(Invoice.total))
        .where(Invoice.invoice_date >= first_of_month)
        .where(Invoice.status != InvoiceStatus.CANCELLED)
    )
    total_revenue = revenue_result.scalar() or Decimal("0.00")
    
    # Pending emails
    pending_result = await db.execute(
        select(func.count(EmailLog.id))
        .where(EmailLog.status.in_([EmailStatus.PENDING, EmailStatus.QUEUED]))
    )
    pending_emails = pending_result.scalar() or 0
    
    # Count customers with upcoming scheduled invoices (next 7 days)
    upcoming_result = await db.execute(
        select(func.count(Customer.id))
        .join(Customer.schedule)
        .where(Customer.is_active == True)
    )
    upcoming_scheduled = upcoming_result.scalar() or 0
    
    # Last execution log
    last_run_result = await db.execute(
        select(ExecutionLog)
        .order_by(ExecutionLog.started_at.desc())
        .limit(1)
    )
    last_run = last_run_result.scalar_one_or_none()
    
    return DashboardStats(
        total_invoices_this_month=total_invoices,
        total_revenue_this_month=total_revenue,
        pending_emails=pending_emails,
        upcoming_scheduled=upcoming_scheduled,
        last_run_date=last_run.run_date if last_run else None,
        last_run_status=(
            "success" if last_run and last_run.failures == 0 else
            "failed" if last_run else None
        ),
    )


@router.get("/upcoming-invoices", response_model=list[UpcomingInvoice])
async def get_upcoming_invoices(
    days_ahead: int = 14,
    db: AsyncSession = Depends(get_db),
):
    """
    Get list of upcoming scheduled invoices.
    """
    result = await db.execute(
        select(Customer)
        .options(
            selectinload(Customer.contract),
            selectinload(Customer.schedule),
        )
        .where(Customer.is_active == True)
    )
    customers = result.scalars().all()
    
    upcoming = []
    today = date.today()
    cutoff = today + timedelta(days=days_ahead)
    
    for customer in customers:
        if not customer.contract or not customer.schedule:
            continue
        
        if not customer.schedule.is_enabled:
            continue
        
        frequency = BillingFrequency(customer.contract.frequency)
        next_date = schedule_service.compute_next_invoice_date(
            today, frequency, customer.schedule
        )
        
        if next_date <= cutoff:
            estimated = (
                customer.contract.default_hours * customer.contract.rate_per_hour
                + customer.contract.extra_fees
            ) * (1 + customer.contract.hst_rate)
            
            upcoming.append(UpcomingInvoice(
                customer_id=customer.id,
                customer_name=customer.name,
                next_invoice_date=next_date,
                frequency=frequency,
                estimated_amount=estimated.quantize(Decimal("0.01")),
            ))
    
    # Sort by date
    upcoming.sort(key=lambda x: x.next_invoice_date)
    
    return upcoming


@router.get("/recent-activity")
async def get_recent_activity(
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
):
    """
    Get recent invoice generation activity.
    """
    result = await db.execute(
        select(ExecutionLog)
        .order_by(ExecutionLog.started_at.desc())
        .limit(limit)
    )
    logs = result.scalars().all()
    
    return [{
        "id": log.id,
        "run_date": log.run_date.isoformat(),
        "mode": log.mode.value,
        "started_at": log.started_at.isoformat(),
        "completed_at": log.completed_at.isoformat() if log.completed_at else None,
        "pdfs_generated": log.pdfs_generated,
        "emails_sent": log.emails_sent,
        "failures": log.failures,
        "triggered_by": log.triggered_by,
    } for log in logs]


@router.get("/revenue-by-month")
async def get_revenue_by_month(
    months: int = 6,
    db: AsyncSession = Depends(get_db),
):
    """
    Get monthly revenue for the last N months.
    """
    today = date.today()
    data = []
    
    for i in range(months - 1, -1, -1):
        # Calculate month start/end
        if today.month - i < 1:
            year = today.year - 1
            month = 12 + (today.month - i)
        else:
            year = today.year
            month = today.month - i
        
        month_start = date(year, month, 1)
        if month == 12:
            month_end = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = date(year, month + 1, 1) - timedelta(days=1)
        
        # Query revenue
        result = await db.execute(
            select(func.sum(Invoice.total))
            .where(Invoice.invoice_date >= month_start)
            .where(Invoice.invoice_date <= month_end)
            .where(Invoice.status != InvoiceStatus.CANCELLED)
        )
        revenue = result.scalar() or Decimal("0.00")
        
        # Query count
        count_result = await db.execute(
            select(func.count(Invoice.id))
            .where(Invoice.invoice_date >= month_start)
            .where(Invoice.invoice_date <= month_end)
            .where(Invoice.status != InvoiceStatus.CANCELLED)
        )
        count = count_result.scalar() or 0
        
        data.append({
            "month": month_start.strftime("%Y-%m"),
            "month_name": month_start.strftime("%b %Y"),
            "revenue": float(revenue),
            "invoice_count": count,
        })
    
    return data
