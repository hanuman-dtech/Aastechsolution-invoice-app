"""
Celery worker configuration and tasks.

Background tasks for email sending, PDF regeneration, and scheduled runs.
"""

import asyncio
from datetime import date
from pathlib import Path

from celery import Celery

from app.core.config import settings
from app.core.logging import get_logger, setup_logging


logger = get_logger(__name__)

# Create Celery app
celery_app = Celery(
    "invoice_enterprise",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # Beat schedule for periodic tasks
    beat_schedule={
        "scheduled-invoice-run": {
            "task": "app.worker.tasks.scheduled_run_task",
            "schedule": 86400.0,  # Daily (configure hour via crontab in production)
        },
    },
)


def run_async(coro):
    """Helper to run async code in Celery tasks."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, name="app.worker.tasks.send_email_task", max_retries=3)
def send_email_task(self, invoice_id: str):
    """
    Background task to send an invoice email.
    
    Retries up to 3 times with exponential backoff.
    """
    setup_logging()
    logger.info(f"Celery task: Sending email for invoice {invoice_id}")
    
    async def _send():
        from app.core.database import get_db_context
        from app.models import Invoice
        from app.services import email_service
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        
        async with get_db_context() as db:
            result = await db.execute(
                select(Invoice)
                .options(
                    selectinload(Invoice.customer).selectinload(Customer.vendor)
                )
                .where(Invoice.id == invoice_id)
            )
            invoice = result.scalar_one_or_none()
            
            if not invoice:
                logger.error(f"Invoice not found: {invoice_id}")
                return {"success": False, "error": "Invoice not found"}
            
            if not invoice.pdf_path:
                logger.error(f"PDF not found for invoice: {invoice_id}")
                return {"success": False, "error": "PDF not found"}
            
            try:
                await email_service.send_invoice_email(
                    db=db,
                    invoice=invoice,
                    attachment_path=Path(invoice.pdf_path),
                )
                return {"success": True, "invoice_id": invoice_id}
            except Exception as e:
                logger.error(f"Failed to send email: {e}")
                raise
    
    try:
        return run_async(_send())
    except Exception as exc:
        # Retry with exponential backoff
        retry_delay = 60 * (2 ** self.request.retries)  # 1min, 2min, 4min
        logger.warning(f"Email task failed, retrying in {retry_delay}s: {exc}")
        raise self.retry(exc=exc, countdown=retry_delay)


@celery_app.task(bind=True, name="app.worker.tasks.regenerate_pdf_task")
def regenerate_pdf_task(self, invoice_id: str):
    """
    Background task to regenerate an invoice PDF.
    """
    setup_logging()
    logger.info(f"Celery task: Regenerating PDF for invoice {invoice_id}")
    
    async def _regenerate():
        from app.core.database import get_db_context
        from app.models import Invoice, Customer
        from app.services import pdf_service, schedule_service
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        
        async with get_db_context() as db:
            result = await db.execute(
                select(Invoice)
                .options(
                    selectinload(Invoice.customer).selectinload(Customer.vendor)
                )
                .where(Invoice.id == invoice_id)
            )
            invoice = result.scalar_one_or_none()
            
            if not invoice:
                logger.error(f"Invoice not found: {invoice_id}")
                return {"success": False, "error": "Invoice not found"}
            
            customer = invoice.customer
            vendor = customer.vendor
            
            # Build address lines
            vendor_address = [vendor.address_line1]
            if vendor.address_line2:
                vendor_address.append(vendor.address_line2)
            vendor_address.append(f"{vendor.city}, {vendor.province} {vendor.postal_code}")
            
            customer_address = [customer.address_line1]
            if customer.address_line2:
                customer_address.append(customer.address_line2)
            customer_address.append(f"{customer.city}, {customer.province} {customer.postal_code}")
            
            # Regenerate PDF
            output_dir = pdf_service.get_output_directory()
            pdf_path = output_dir / f"{invoice.invoice_number}.pdf"
            
            pdf_service.generate_invoice_pdf(
                filename=pdf_path,
                invoice_number=invoice.invoice_number,
                invoice_date=invoice.invoice_date.strftime("%d/%m/%Y"),
                vendor_name=vendor.name,
                vendor_email=vendor.email,
                vendor_address_lines=vendor_address,
                vendor_hst_number=vendor.hst_number,
                contractor_name=customer.contractor_name,
                customer_name=customer.name,
                customer_address_lines=customer_address,
                service_location=customer.service_location,
                period_start=schedule_service.format_date(invoice.period_start),
                period_end=schedule_service.format_date(invoice.period_end),
                total_hours=invoice.total_hours,
                rate_per_hour=invoice.rate_per_hour,
                hst_rate=invoice.hst_rate,
                payment_terms=customer.contract.payment_terms if customer.contract else "Monthly",
                extra_fees=invoice.extra_fees,
                extra_fees_label=invoice.extra_fees_label,
            )
            
            invoice.pdf_path = str(pdf_path)
            await db.commit()
            
            return {"success": True, "invoice_id": invoice_id, "pdf_path": str(pdf_path)}
    
    return run_async(_regenerate())


@celery_app.task(bind=True, name="app.worker.tasks.scheduled_run_task")
def scheduled_run_task(self, run_date_str: str | None = None, send_email: bool = False):
    """
    Background task for scheduled invoice generation.
    
    This runs daily (via Celery Beat) to generate invoices for
    customers whose schedule matches today's date.
    """
    setup_logging()
    
    run_date = date.fromisoformat(run_date_str) if run_date_str else date.today()
    logger.info(f"Celery task: Scheduled run for {run_date.isoformat()}")
    
    async def _run():
        from app.core.database import get_db_context
        from app.schemas import ScheduledRunRequest
        from app.services import invoice_engine
        
        request = ScheduledRunRequest(
            run_date=run_date,
            ignore_schedule=False,
            send_email=send_email,
        )
        
        async with get_db_context() as db:
            result = await invoice_engine.run_scheduled(
                db=db,
                request=request,
                triggered_by="celery_scheduler",
            )
            return {
                "execution_id": result.execution_id,
                "pdfs_generated": result.pdfs_generated,
                "emails_sent": result.emails_sent,
                "failures": len(result.failures),
            }
    
    return run_async(_run())


# Import at end to avoid circular imports
from app.models import Customer
