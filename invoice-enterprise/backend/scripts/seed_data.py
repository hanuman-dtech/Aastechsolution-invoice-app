#!/usr/bin/env python3
"""
Database seed script for Invoice Enterprise Console.
Creates demo data for development and testing.

Usage:
    python -m scripts.seed_data
"""
import asyncio
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.core.security import get_password_hash, encrypt_smtp_password
from app.models.models import (
    User, Vendor, Customer, Contract, ScheduleConfig,
    Invoice, InvoiceLine, SmtpConfig, ExecutionLog,
    BillingFrequency, InvoiceStatus, ExecutionMode, UserRole
)


async def seed_database():
    """Seed the database with demo data."""
    async with async_session_factory() as db:
        print("🌱 Starting database seeding...")
        
        # Check if data already exists
        from sqlalchemy import select
        existing_user = await db.execute(select(User).limit(1))
        if existing_user.scalar_one_or_none():
            print("⚠️  Database already has data. Skipping seed.")
            return
        
        # Create admin user
        admin_user = User(
            id=str(uuid.uuid4()),
            email="admin@invoiceenterprise.local",
            hashed_password=get_password_hash("admin123"),
            full_name="System Administrator",
            role=UserRole.ADMIN,
            is_active=True,
        )
        db.add(admin_user)
        print("✅ Created admin user: admin@invoiceenterprise.local / admin123")
        
        # Create viewer user
        viewer_user = User(
            id=str(uuid.uuid4()),
            email="viewer@invoiceenterprise.local",
            hashed_password=get_password_hash("viewer123"),
            full_name="Read Only User",
            role=UserRole.VIEWER,
            is_active=True,
        )
        db.add(viewer_user)
        print("✅ Created viewer user: viewer@invoiceenterprise.local / viewer123")
        
        # Create vendor (your company)
        vendor = Vendor(
            id=str(uuid.uuid4()),
            name="AAS Tech Solutions Inc.",
            email="billing@aastechsolutions.local",
            address_line1="123 Tech Street",
            address_line2="Suite 456",
            city="Toronto",
            province="ON",
            postal_code="M5V 1A1",
            country="Canada",
            hst_number="123456789RT0001",
            default_contractor="John Developer",
            is_active=True,
        )
        db.add(vendor)
        print(f"✅ Created vendor: {vendor.name}")
        
        # Create SMTP config (for Mailhog in dev)
        smtp_config = SmtpConfig(
            id=str(uuid.uuid4()),
            vendor_id=vendor.id,
            name="Development (Mailhog)",
            host="mailhog",
            port=1025,
            username="",
            encrypted_password=encrypt_smtp_password(""),
            from_email="invoices@aastechsolutions.local",
            from_name="AAS Tech Solutions Billing",
            use_tls=False,
            is_active=True,
        )
        db.add(smtp_config)
        print("✅ Created SMTP config for Mailhog")
        
        # Create customers
        customers_data = [
            {
                "name": "Acme Corporation",
                "email": "ap@acmecorp.local",
                "address_line1": "500 Business Avenue",
                "city": "Mississauga",
                "province": "ON",
                "postal_code": "L5B 2T4",
                "contractor_name": "John Developer",
                "service_location": "Mississauga, Ontario",
                "contract": {
                    "invoice_prefix": "ACME",
                    "frequency": BillingFrequency.BIWEEKLY,
                    "default_hours": Decimal("80"),
                    "rate_per_hour": Decimal("125.00"),
                    "hst_rate": Decimal("0.13"),
                    "payment_terms": "Net 15",
                    "extra_fees": Decimal("0"),
                },
                "schedule": {
                    "is_enabled": True,
                    "auto_send_email": False,
                    "billing_weekday": 4,  # Friday
                    "anchor_date": date(2026, 1, 3),
                    "billing_day": 1,
                },
            },
            {
                "name": "Global Tech Industries",
                "email": "accounts@globaltech.local",
                "address_line1": "1000 Innovation Drive",
                "address_line2": "Building C",
                "city": "Toronto",
                "province": "ON",
                "postal_code": "M5J 2N8",
                "contractor_name": "Jane Engineer",
                "service_location": "Toronto, Ontario",
                "contract": {
                    "invoice_prefix": "GTI",
                    "frequency": BillingFrequency.MONTHLY,
                    "default_hours": Decimal("160"),
                    "rate_per_hour": Decimal("150.00"),
                    "hst_rate": Decimal("0.13"),
                    "payment_terms": "Monthly",
                    "extra_fees": Decimal("500.00"),
                    "extra_fees_label": "Cloud Infrastructure",
                },
                "schedule": {
                    "is_enabled": True,
                    "auto_send_email": True,
                    "billing_weekday": 0,  # Monday
                    "anchor_date": date(2026, 1, 1),
                    "billing_day": 1,
                },
            },
            {
                "name": "StartupXYZ Inc.",
                "email": "finance@startupxyz.local",
                "address_line1": "25 Startup Lane",
                "city": "Waterloo",
                "province": "ON",
                "postal_code": "N2L 3G1",
                "contractor_name": "John Developer",
                "service_location": "Remote / Ontario",
                "contract": {
                    "invoice_prefix": "SXYZ",
                    "frequency": BillingFrequency.WEEKLY,
                    "default_hours": Decimal("40"),
                    "rate_per_hour": Decimal("100.00"),
                    "hst_rate": Decimal("0.13"),
                    "payment_terms": "Due on Receipt",
                },
                "schedule": {
                    "is_enabled": True,
                    "auto_send_email": False,
                    "billing_weekday": 4,  # Friday
                    "anchor_date": date(2026, 1, 3),
                    "billing_day": 1,
                },
            },
            {
                "name": "Enterprise Solutions Ltd.",
                "email": "invoices@enterprisesol.local",
                "address_line1": "2500 Corporate Blvd",
                "address_line2": "Floor 15",
                "city": "Ottawa",
                "province": "ON",
                "postal_code": "K1P 5G3",
                "contractor_name": "Senior Consultant",
                "service_location": "Ottawa, Ontario",
                "contract": {
                    "invoice_prefix": "ESL",
                    "frequency": BillingFrequency.MONTHLY,
                    "default_hours": Decimal("120"),
                    "rate_per_hour": Decimal("175.00"),
                    "hst_rate": Decimal("0.13"),
                    "payment_terms": "Net 30",
                    "extra_fees": Decimal("1000.00"),
                    "extra_fees_label": "Project Management Fee",
                    "notes": "Priority support client. Contact Sarah at ext 234 for approvals.",
                },
                "schedule": {
                    "is_enabled": False,  # Manual invoicing
                    "auto_send_email": False,
                    "billing_weekday": 0,
                    "anchor_date": date(2026, 1, 1),
                    "billing_day": 1,
                },
            },
        ]
        
        for cust_data in customers_data:
            customer = Customer(
                id=str(uuid.uuid4()),
                vendor_id=vendor.id,
                name=cust_data["name"],
                email=cust_data["email"],
                address_line1=cust_data["address_line1"],
                address_line2=cust_data.get("address_line2"),
                city=cust_data["city"],
                province=cust_data["province"],
                postal_code=cust_data["postal_code"],
                country="Canada",
                contractor_name=cust_data["contractor_name"],
                service_location=cust_data["service_location"],
                is_active=True,
            )
            db.add(customer)
            
            # Add contract
            contract_data = cust_data["contract"]
            contract = Contract(
                id=str(uuid.uuid4()),
                customer_id=customer.id,
                invoice_prefix=contract_data["invoice_prefix"],
                frequency=contract_data["frequency"],
                default_hours=contract_data["default_hours"],
                rate_per_hour=contract_data["rate_per_hour"],
                hst_rate=contract_data["hst_rate"],
                payment_terms=contract_data["payment_terms"],
                extra_fees=contract_data.get("extra_fees", Decimal("0")),
                extra_fees_label=contract_data.get("extra_fees_label", "Other Fees"),
                notes=contract_data.get("notes"),
                is_active=True,
            )
            db.add(contract)
            
            # Add schedule config
            schedule_data = cust_data["schedule"]
            schedule = ScheduleConfig(
                id=str(uuid.uuid4()),
                customer_id=customer.id,
                is_enabled=schedule_data["is_enabled"],
                auto_send_email=schedule_data["auto_send_email"],
                timezone="America/Toronto",
                billing_weekday=schedule_data["billing_weekday"],
                anchor_date=schedule_data["anchor_date"],
                billing_day=schedule_data["billing_day"],
            )
            db.add(schedule)
            
            print(f"✅ Created customer: {customer.name} (prefix: {contract.invoice_prefix})")
        
        # Create some sample invoices for history
        acme_customer = await db.execute(
            select(Customer).where(Customer.name == "Acme Corporation")
        )
        acme = acme_customer.scalar_one()
        acme_contract = await db.execute(
            select(Contract).where(Contract.customer_id == acme.id)
        )
        acme_contract = acme_contract.scalar_one()
        
        sample_invoices = [
            {
                "invoice_number": "ACME-2026-001",
                "invoice_date": date(2026, 1, 17),
                "period_start": date(2026, 1, 3),
                "period_end": date(2026, 1, 16),
                "status": InvoiceStatus.SENT,
                "total_hours": Decimal("80"),
            },
            {
                "invoice_number": "ACME-2026-002",
                "invoice_date": date(2026, 1, 31),
                "period_start": date(2026, 1, 17),
                "period_end": date(2026, 1, 30),
                "status": InvoiceStatus.SENT,
                "total_hours": Decimal("76"),
            },
            {
                "invoice_number": "ACME-2026-003",
                "invoice_date": date(2026, 2, 14),
                "period_start": date(2026, 1, 31),
                "period_end": date(2026, 2, 13),
                "status": InvoiceStatus.GENERATED,
                "total_hours": Decimal("80"),
            },
        ]
        
        for inv_data in sample_invoices:
            labor = inv_data["total_hours"] * acme_contract.rate_per_hour
            extra = acme_contract.extra_fees
            subtotal = labor + extra
            hst = subtotal * acme_contract.hst_rate
            total = subtotal + hst
            
            invoice = Invoice(
                id=str(uuid.uuid4()),
                customer_id=acme.id,
                invoice_number=inv_data["invoice_number"],
                invoice_date=inv_data["invoice_date"],
                period_start=inv_data["period_start"],
                period_end=inv_data["period_end"],
                status=inv_data["status"],
                total_hours=inv_data["total_hours"],
                rate_per_hour=acme_contract.rate_per_hour,
                labor_subtotal=labor,
                extra_fees=extra,
                extra_fees_label=acme_contract.extra_fees_label,
                subtotal=subtotal,
                hst_rate=acme_contract.hst_rate,
                hst_amount=hst,
                total=total,
                generation_mode=ExecutionMode.SCHEDULED,
            )
            db.add(invoice)
            
            # Add invoice lines
            line1 = InvoiceLine(
                id=str(uuid.uuid4()),
                invoice_id=invoice.id,
                description=f"Software Development Services ({inv_data['period_start']} - {inv_data['period_end']})",
                quantity=inv_data["total_hours"],
                unit_price=acme_contract.rate_per_hour,
                line_total=labor,
                sort_order=1,
            )
            db.add(line1)
            
            print(f"✅ Created invoice: {inv_data['invoice_number']}")
        
        # Create sample execution logs
        log1 = ExecutionLog(
            id=str(uuid.uuid4()),
            run_date=date(2026, 2, 14),
            mode=ExecutionMode.SCHEDULED,
            started_at=datetime(2026, 2, 14, 0, 5, 0, tzinfo=timezone.utc),
            completed_at=datetime(2026, 2, 14, 0, 5, 12, tzinfo=timezone.utc),
            customers_loaded=4,
            schedule_matches=2,
            pdfs_generated=2,
            emails_sent=1,
            failures=0,
            triggered_by="celery-beat",
        )
        db.add(log1)
        
        log2 = ExecutionLog(
            id=str(uuid.uuid4()),
            run_date=date(2026, 2, 13),
            mode=ExecutionMode.QUICK,
            started_at=datetime(2026, 2, 13, 14, 30, 0, tzinfo=timezone.utc),
            completed_at=datetime(2026, 2, 13, 14, 30, 5, tzinfo=timezone.utc),
            customers_loaded=1,
            schedule_matches=1,
            pdfs_generated=1,
            emails_sent=0,
            failures=0,
            triggered_by="admin@invoiceenterprise.local",
        )
        db.add(log2)
        print("✅ Created execution logs")
        
        await db.commit()
        print("\n🎉 Database seeding completed successfully!")
        print("\nDemo credentials:")
        print("  Admin: admin@invoiceenterprise.local / admin123")
        print("  Viewer: viewer@invoiceenterprise.local / viewer123")


if __name__ == "__main__":
    asyncio.run(seed_database())
