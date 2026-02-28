"""
Invoice Engine Service - Main orchestration service for invoice generation.

This service coordinates PDF generation, schedule matching, and email sending.
Refactored from invoice.py main logic.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.logging import get_logger, request_id_ctx
from app.core.security import generate_invoice_number
from app.models import (
    BillingFrequency,
    Contract,
    Customer,
    ExecutionLog,
    ExecutionMode,
    Invoice,
    InvoiceStatus,
    ScheduleConfig,
    Vendor,
)
from app.schemas import (
    ExecutionSummary,
    InvoiceResponse,
    ManualDateOverrideRequest,
    QuickModeRequest,
    ScheduledRunRequest,
    WizardModeRequest,
)
from app.services.email_service import email_service
from app.services.pdf_service import pdf_service
from app.services.schedule_service import schedule_service


logger = get_logger(__name__)


class InvoiceEngine:
    """Main invoice generation engine."""
    
    def __init__(self):
        self.pdf_service = pdf_service
        self.email_service = email_service
        self.schedule_service = schedule_service
    
    async def get_vendor_address_lines(self, vendor: Vendor) -> list[str]:
        """Build vendor address lines for PDF."""
        lines = [vendor.address_line1]
        if vendor.address_line2:
            lines.append(vendor.address_line2)
        lines.append(f"{vendor.city}, {vendor.province} {vendor.postal_code}")
        return lines
    
    async def get_customer_address_lines(self, customer: Customer) -> list[str]:
        """Build customer address lines for PDF."""
        lines = [customer.address_line1]
        if customer.address_line2:
            lines.append(customer.address_line2)
        lines.append(f"{customer.city}, {customer.province} {customer.postal_code}")
        return lines
    
    async def get_next_invoice_sequence(
        self,
        db: AsyncSession,
        customer_id: str,
        invoice_date: date,
    ) -> int:
        """Get the next invoice sequence number for a customer on a date."""
        result = await db.execute(
            select(func.count(Invoice.id))
            .where(Invoice.customer_id == customer_id)
            .where(Invoice.invoice_date == invoice_date)
        )
        count = result.scalar() or 0
        return count + 1
    
    async def check_duplicate_invoice(
        self,
        db: AsyncSession,
        customer_id: str,
        period_start: date,
        period_end: date,
    ) -> Optional[Invoice]:
        """Check if an invoice already exists for this period."""
        result = await db.execute(
            select(Invoice)
            .where(Invoice.customer_id == customer_id)
            .where(Invoice.period_start == period_start)
            .where(Invoice.period_end == period_end)
            .where(Invoice.status != InvoiceStatus.CANCELLED)
        )
        return result.scalar_one_or_none()
    
    async def generate_invoice(
        self,
        db: AsyncSession,
        customer: Customer,
        run_date: date,
        total_hours: Decimal,
        mode: ExecutionMode,
        period_start: Optional[date] = None,
        period_end: Optional[date] = None,
        rate_per_hour: Optional[Decimal] = None,
        hst_rate: Optional[Decimal] = None,
        extra_fees: Optional[Decimal] = None,
        extra_fees_label: Optional[str] = None,
        payment_terms: Optional[str] = None,
        allow_duplicate: bool = False,
    ) -> Invoice:
        """
        Generate a single invoice for a customer.
        
        Args:
            db: Database session
            customer: Customer to invoice
            run_date: Invoice generation date
            total_hours: Hours to bill
            mode: Execution mode
            period_start: Override period start (computed if None)
            period_end: Override period end (computed if None)
            rate_per_hour: Override rate (uses contract if None)
            hst_rate: Override HST rate (uses contract if None)
            extra_fees: Override extra fees (uses contract if None)
            extra_fees_label: Override label (uses contract if None)
            payment_terms: Override terms (uses contract if None)
            
        Returns:
            Generated Invoice record
        """
        contract = customer.contract
        vendor = customer.vendor
        
        if not contract:
            raise ValueError(f"Customer {customer.name} has no contract configured")
        
        # Use contract values as defaults
        frequency = BillingFrequency(contract.frequency)
        rate = rate_per_hour if rate_per_hour is not None else contract.rate_per_hour
        hst = hst_rate if hst_rate is not None else contract.hst_rate
        fees = extra_fees if extra_fees is not None else contract.extra_fees
        fees_label = extra_fees_label or contract.extra_fees_label
        terms = payment_terms or contract.payment_terms
        
        # Compute billing period if not provided
        if period_start is None or period_end is None:
            period_start, period_end = self.schedule_service.compute_billing_period(
                run_date, frequency
            )
        
        # Check for duplicate unless explicitly allowed (wizard override use-case).
        if not allow_duplicate:
            existing = await self.check_duplicate_invoice(
                db, customer.id, period_start, period_end
            )
            if existing:
                logger.warning(
                    f"Invoice already exists for {customer.name} "
                    f"period {period_start} to {period_end}: {existing.invoice_number}"
                )
                raise ValueError(
                    f"Invoice already exists for this period: {existing.invoice_number}"
                )
        
        # Generate invoice number
        sequence = await self.get_next_invoice_sequence(db, customer.id, run_date)
        invoice_number = generate_invoice_number(
            contract.invoice_prefix,
            datetime.combine(run_date, datetime.min.time()),
            sequence,
        )
        
        # Build address lines
        vendor_address = await self.get_vendor_address_lines(vendor)
        customer_address = await self.get_customer_address_lines(customer)

        # Resolve dynamic names separately for invoice rendering.
        client_name = (customer.name or "").strip()
        contractor_name = (customer.contractor_name or "").strip()

        # If entered the same, prefer vendor default contractor as a better fallback.
        if contractor_name.lower() == client_name.lower() and getattr(vendor, "default_contractor", None):
            contractor_name = vendor.default_contractor.strip()

        if not contractor_name:
            contractor_name = "Contractor"
        
        # Generate PDF
        output_dir = self.pdf_service.get_output_directory()
        pdf_path = output_dir / f"{invoice_number}.pdf"
        
        _, labor_subtotal, subtotal, hst_amount, total = self.pdf_service.generate_invoice_pdf(
            filename=pdf_path,
            invoice_number=invoice_number,
            invoice_date=run_date.strftime("%d/%m/%Y"),
            vendor_name=vendor.name,
            vendor_email=vendor.email,
            vendor_address_lines=vendor_address,
            vendor_hst_number=vendor.hst_number,
            contractor_name=contractor_name,
            customer_name=client_name,
            customer_address_lines=customer_address,
            service_location=customer.service_location,
            period_start=self.schedule_service.format_date(period_start),
            period_end=self.schedule_service.format_date(period_end),
            total_hours=total_hours,
            rate_per_hour=rate,
            hst_rate=hst,
            payment_terms=terms,
            extra_fees=fees,
            extra_fees_label=fees_label,
        )
        
        # Create invoice record
        invoice = Invoice(
            customer_id=customer.id,
            invoice_number=invoice_number,
            invoice_date=run_date,
            period_start=period_start,
            period_end=period_end,
            status=InvoiceStatus.GENERATED,
            total_hours=total_hours,
            rate_per_hour=rate,
            labor_subtotal=labor_subtotal,
            extra_fees=fees,
            extra_fees_label=fees_label,
            subtotal=subtotal,
            hst_rate=hst,
            hst_amount=hst_amount,
            total=total,
            pdf_path=str(pdf_path),
            generation_mode=mode,
        )
        
        db.add(invoice)
        await db.flush()
        
        logger.info(f"Generated invoice {invoice_number} for {customer.name}: ${total}")
        
        return invoice
    
    async def run_quick_mode(
        self,
        db: AsyncSession,
        request: QuickModeRequest,
        triggered_by: Optional[str] = None,
    ) -> ExecutionSummary:
        """
        Run quick mode - generate invoice with minimal inputs.
        
        Args:
            db: Database session
            request: Quick mode request (customer_id, run_date, hours)
            triggered_by: User email or "api"
            
        Returns:
            Execution summary
        """
        start_time = datetime.now(timezone.utc)
        request_id = request_id_ctx.get()
        
        # Create execution log
        exec_log = ExecutionLog(
            run_date=request.run_date,
            mode=ExecutionMode.QUICK,
            started_at=start_time,
            request_id=request_id,
            triggered_by=triggered_by,
        )
        db.add(exec_log)
        
        generated_invoices: list[InvoiceResponse] = []
        failures: list[dict] = []
        
        try:
            # Get customer with contract
            result = await db.execute(
                select(Customer)
                .options(
                    selectinload(Customer.contract),
                    selectinload(Customer.vendor),
                )
                .where(Customer.id == request.customer_id)
                .where(Customer.is_active == True)
            )
            customer = result.scalar_one_or_none()
            
            if not customer:
                raise ValueError(f"Customer not found: {request.customer_id}")
            
            exec_log.customers_loaded = 1
            exec_log.schedule_matches = 1
            
            # Generate invoice
            invoice = await self.generate_invoice(
                db=db,
                customer=customer,
                run_date=request.run_date,
                total_hours=request.total_hours,
                mode=ExecutionMode.QUICK,
            )
            
            exec_log.pdfs_generated = 1
            generated_invoices.append(InvoiceResponse.model_validate(invoice))
            
            # Send email if requested
            if request.send_email:
                try:
                    await self.email_service.send_invoice_email(
                        db=db,
                        invoice=invoice,
                        attachment_path=Path(invoice.pdf_path),
                    )
                    invoice.status = InvoiceStatus.SENT
                    exec_log.emails_sent = 1
                except Exception as e:
                    logger.error(f"Failed to send email for {invoice.invoice_number}: {e}")
                    failures.append({
                        "customer_id": customer.id,
                        "customer_name": customer.name,
                        "error": f"Email failed: {str(e)}",
                    })
                    exec_log.failures = 1
            
            exec_log.completed_at = datetime.now(timezone.utc)
            await db.commit()
            
        except Exception as e:
            logger.error(f"Quick mode failed: {e}")
            exec_log.error_trace = str(e)
            exec_log.failures = 1
            exec_log.completed_at = datetime.now(timezone.utc)
            await db.commit()
            raise
        
        duration = (exec_log.completed_at - start_time).total_seconds()
        
        return ExecutionSummary(
            execution_id=exec_log.id,
            run_date=request.run_date,
            mode=ExecutionMode.QUICK,
            customers_loaded=exec_log.customers_loaded,
            schedule_matches=exec_log.schedule_matches,
            pdfs_generated=exec_log.pdfs_generated,
            emails_sent=exec_log.emails_sent,
            emails_failed=len([f for f in failures if "Email" in f.get("error", "")]),
            failures=failures,
            generated_invoices=generated_invoices,
            download_links=[inv.pdf_path for inv in generated_invoices if inv.pdf_path],
            duration_seconds=duration,
        )
    
    async def run_wizard_mode(
        self,
        db: AsyncSession,
        request: WizardModeRequest,
        triggered_by: Optional[str] = None,
    ) -> ExecutionSummary:
        """
        Run wizard mode - full manual input.
        """
        start_time = datetime.now(timezone.utc)
        request_id = request_id_ctx.get()
        
        exec_log = ExecutionLog(
            run_date=request.invoice_date,
            mode=ExecutionMode.WIZARD,
            started_at=start_time,
            request_id=request_id,
            triggered_by=triggered_by,
        )
        db.add(exec_log)
        
        generated_invoices: list[InvoiceResponse] = []
        failures: list[dict] = []
        
        try:
            # Get customer
            result = await db.execute(
                select(Customer)
                .options(
                    selectinload(Customer.contract),
                    selectinload(Customer.vendor),
                )
                .where(Customer.id == request.customer_id)
                .where(Customer.is_active == True)
            )
            customer = result.scalar_one_or_none()
            
            if not customer:
                raise ValueError(f"Customer not found: {request.customer_id}")
            
            exec_log.customers_loaded = 1
            exec_log.schedule_matches = 1
            
            # Generate invoice with full overrides
            invoice = await self.generate_invoice(
                db=db,
                customer=customer,
                run_date=request.invoice_date,
                total_hours=request.total_hours,
                mode=ExecutionMode.WIZARD,
                period_start=request.period_start,
                period_end=request.period_end,
                rate_per_hour=request.rate_per_hour,
                hst_rate=request.hst_rate,
                extra_fees=request.extra_fees,
                extra_fees_label=request.extra_fees_label,
                payment_terms=request.payment_terms,
                allow_duplicate=request.allow_duplicate,
            )
            
            exec_log.pdfs_generated = 1
            generated_invoices.append(InvoiceResponse.model_validate(invoice))
            
            # Send email if requested
            if request.send_email:
                try:
                    await self.email_service.send_invoice_email(
                        db=db,
                        invoice=invoice,
                        attachment_path=Path(invoice.pdf_path),
                    )
                    invoice.status = InvoiceStatus.SENT
                    exec_log.emails_sent = 1
                except Exception as e:
                    logger.error(f"Failed to send email: {e}")
                    failures.append({
                        "customer_id": customer.id,
                        "customer_name": customer.name,
                        "error": f"Email failed: {str(e)}",
                    })
                    exec_log.failures = 1
            
            exec_log.completed_at = datetime.now(timezone.utc)
            await db.commit()
            
        except Exception as e:
            logger.error(f"Wizard mode failed: {e}")
            exec_log.error_trace = str(e)
            exec_log.failures = 1
            exec_log.completed_at = datetime.now(timezone.utc)
            await db.commit()
            raise
        
        duration = (exec_log.completed_at - start_time).total_seconds()
        
        return ExecutionSummary(
            execution_id=exec_log.id,
            run_date=request.invoice_date,
            mode=ExecutionMode.WIZARD,
            customers_loaded=exec_log.customers_loaded,
            schedule_matches=exec_log.schedule_matches,
            pdfs_generated=exec_log.pdfs_generated,
            emails_sent=exec_log.emails_sent,
            emails_failed=len([f for f in failures if "Email" in f.get("error", "")]),
            failures=failures,
            generated_invoices=generated_invoices,
            download_links=[inv.pdf_path for inv in generated_invoices if inv.pdf_path],
            duration_seconds=duration,
        )
    
    async def run_scheduled(
        self,
        db: AsyncSession,
        request: ScheduledRunRequest,
        triggered_by: Optional[str] = None,
    ) -> ExecutionSummary:
        """
        Run scheduled mode - process customers based on their schedules.
        """
        start_time = datetime.now(timezone.utc)
        request_id = request_id_ctx.get()
        
        mode = ExecutionMode.GENERATE_ALL if request.ignore_schedule else ExecutionMode.SCHEDULED
        
        exec_log = ExecutionLog(
            run_date=request.run_date,
            mode=mode,
            started_at=start_time,
            request_id=request_id,
            triggered_by=triggered_by,
        )
        db.add(exec_log)
        
        generated_invoices: list[InvoiceResponse] = []
        failures: list[dict] = []
        
        try:
            # Get all active customers with contracts and schedules
            query = (
                select(Customer)
                .options(
                    selectinload(Customer.contract),
                    selectinload(Customer.schedule),
                    selectinload(Customer.vendor),
                )
                .where(Customer.is_active == True)
            )
            
            # Filter by customer IDs if provided
            if request.customer_ids:
                query = query.where(Customer.id.in_(request.customer_ids))
            
            result = await db.execute(query)
            customers = result.scalars().all()
            
            exec_log.customers_loaded = len(customers)
            
            # Process each customer
            for customer in customers:
                if not customer.contract:
                    logger.warning(f"Customer {customer.name} has no contract, skipping")
                    continue
                
                if not customer.schedule:
                    logger.warning(f"Customer {customer.name} has no schedule, skipping")
                    continue
                
                frequency = BillingFrequency(customer.contract.frequency)
                
                # Check schedule unless ignore_schedule is set
                if not request.ignore_schedule:
                    if not self.schedule_service.should_invoice_today(
                        request.run_date,
                        frequency,
                        customer.schedule,
                    ):
                        logger.debug(f"Customer {customer.name} not scheduled for {request.run_date}")
                        continue
                
                exec_log.schedule_matches += 1
                
                try:
                    invoice = await self.generate_invoice(
                        db=db,
                        customer=customer,
                        run_date=request.run_date,
                        total_hours=customer.contract.default_hours,
                        mode=mode,
                    )
                    
                    exec_log.pdfs_generated += 1
                    generated_invoices.append(InvoiceResponse.model_validate(invoice))
                    
                    # Send email if requested and auto_send is enabled
                    should_send = request.send_email and (
                        request.ignore_schedule or customer.schedule.auto_send_email
                    )
                    
                    if should_send:
                        try:
                            await self.email_service.send_invoice_email(
                                db=db,
                                invoice=invoice,
                                attachment_path=Path(invoice.pdf_path),
                            )
                            invoice.status = InvoiceStatus.SENT
                            exec_log.emails_sent += 1
                        except Exception as e:
                            logger.error(f"Failed to send email for {customer.name}: {e}")
                            failures.append({
                                "customer_id": customer.id,
                                "customer_name": customer.name,
                                "error": f"Email failed: {str(e)}",
                            })
                    
                    # Update schedule last_run_date
                    customer.schedule.last_run_date = request.run_date
                    customer.schedule.next_run_date = self.schedule_service.compute_next_invoice_date(
                        request.run_date + timedelta(days=1),
                        frequency,
                        customer.schedule,
                    )
                    
                except Exception as e:
                    logger.error(f"Failed to generate invoice for {customer.name}: {e}")
                    failures.append({
                        "customer_id": customer.id,
                        "customer_name": customer.name,
                        "error": str(e),
                    })
                    exec_log.failures += 1
            
            exec_log.completed_at = datetime.now(timezone.utc)
            await db.commit()
            
        except Exception as e:
            logger.error(f"Scheduled run failed: {e}")
            exec_log.error_trace = str(e)
            exec_log.completed_at = datetime.now(timezone.utc)
            await db.commit()
            raise
        
        duration = (exec_log.completed_at - start_time).total_seconds()
        
        return ExecutionSummary(
            execution_id=exec_log.id,
            run_date=request.run_date,
            mode=mode,
            customers_loaded=exec_log.customers_loaded,
            schedule_matches=exec_log.schedule_matches,
            pdfs_generated=exec_log.pdfs_generated,
            emails_sent=exec_log.emails_sent,
            emails_failed=len([f for f in failures if "Email" in f.get("error", "")]),
            failures=failures,
            generated_invoices=generated_invoices,
            download_links=[inv.pdf_path for inv in generated_invoices if inv.pdf_path],
            duration_seconds=duration,
        )
    
    async def run_manual_date_override(
        self,
        db: AsyncSession,
        request: ManualDateOverrideRequest,
        triggered_by: Optional[str] = None,
    ) -> ExecutionSummary:
        """
        Run manual date override mode - specify exact period dates.
        """
        start_time = datetime.now(timezone.utc)
        request_id = request_id_ctx.get()
        
        exec_log = ExecutionLog(
            run_date=request.invoice_date,
            mode=ExecutionMode.MANUAL,
            started_at=start_time,
            request_id=request_id,
            triggered_by=triggered_by,
        )
        db.add(exec_log)
        
        generated_invoices: list[InvoiceResponse] = []
        failures: list[dict] = []
        
        try:
            # Get customer
            result = await db.execute(
                select(Customer)
                .options(
                    selectinload(Customer.contract),
                    selectinload(Customer.vendor),
                )
                .where(Customer.id == request.customer_id)
                .where(Customer.is_active == True)
            )
            customer = result.scalar_one_or_none()
            
            if not customer:
                raise ValueError(f"Customer not found: {request.customer_id}")
            
            exec_log.customers_loaded = 1
            exec_log.schedule_matches = 1
            
            # Generate invoice with manual dates
            invoice = await self.generate_invoice(
                db=db,
                customer=customer,
                run_date=request.invoice_date,
                total_hours=customer.contract.default_hours,
                mode=ExecutionMode.MANUAL,
                period_start=request.period_start,
                period_end=request.period_end,
            )
            
            exec_log.pdfs_generated = 1
            generated_invoices.append(InvoiceResponse.model_validate(invoice))
            
            if request.send_email:
                try:
                    await self.email_service.send_invoice_email(
                        db=db,
                        invoice=invoice,
                        attachment_path=Path(invoice.pdf_path),
                    )
                    invoice.status = InvoiceStatus.SENT
                    exec_log.emails_sent = 1
                except Exception as e:
                    logger.error(f"Failed to send email: {e}")
                    failures.append({
                        "customer_id": customer.id,
                        "customer_name": customer.name,
                        "error": f"Email failed: {str(e)}",
                    })
                    exec_log.failures = 1
            
            exec_log.completed_at = datetime.now(timezone.utc)
            await db.commit()
            
        except Exception as e:
            logger.error(f"Manual mode failed: {e}")
            exec_log.error_trace = str(e)
            exec_log.failures = 1
            exec_log.completed_at = datetime.now(timezone.utc)
            await db.commit()
            raise
        
        duration = (exec_log.completed_at - start_time).total_seconds()
        
        return ExecutionSummary(
            execution_id=exec_log.id,
            run_date=request.invoice_date,
            mode=ExecutionMode.MANUAL,
            customers_loaded=exec_log.customers_loaded,
            schedule_matches=exec_log.schedule_matches,
            pdfs_generated=exec_log.pdfs_generated,
            emails_sent=exec_log.emails_sent,
            emails_failed=len([f for f in failures if "Email" in f.get("error", "")]),
            failures=failures,
            generated_invoices=generated_invoices,
            download_links=[inv.pdf_path for inv in generated_invoices if inv.pdf_path],
            duration_seconds=duration,
        )


# Need this import at top level to avoid circular import
from datetime import timedelta

# Singleton instance  
invoice_engine = InvoiceEngine()
