"""
SQLAlchemy database models for Invoice Enterprise Console.
"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


# Enums
class BillingFrequency(str, Enum):
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"


class InvoiceStatus(str, Enum):
    DRAFT = "draft"
    GENERATED = "generated"
    SENT = "sent"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class EmailStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    SENT = "sent"
    FAILED = "failed"
    BOUNCED = "bounced"


class ExecutionMode(str, Enum):
    SCHEDULED = "scheduled"
    QUICK = "quick"
    WIZARD = "wizard"
    MANUAL = "manual"
    GENERATE_ALL = "generate_all"


class UserRole(str, Enum):
    ADMIN = "admin"
    FINANCE = "finance"
    VIEWER = "viewer"


# Mixin for common timestamp fields
class TimestampMixin:
    """Mixin for created_at and updated_at timestamps."""
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


# Models
class User(Base, TimestampMixin):
    """User model for authentication and authorization."""
    
    __tablename__ = "users"
    
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(String(50), default=UserRole.VIEWER, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Indexes
    __table_args__ = (
        Index("ix_users_email_active", "email", "is_active"),
    )


class Vendor(Base, TimestampMixin):
    """Vendor/company information (the entity sending invoices)."""
    
    __tablename__ = "vendors"
    
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    address_line1: Mapped[str] = mapped_column(String(255), nullable=False)
    address_line2: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    province: Mapped[str] = mapped_column(String(100), nullable=False)
    postal_code: Mapped[str] = mapped_column(String(20), nullable=False)
    country: Mapped[str] = mapped_column(String(100), default="Canada", nullable=False)
    hst_number: Mapped[str] = mapped_column(String(50), nullable=False)
    default_contractor: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Relationships
    customers: Mapped[list["Customer"]] = relationship(back_populates="vendor", lazy="selectin")


class Customer(Base, TimestampMixin):
    """Customer model - entities that receive invoices."""
    
    __tablename__ = "customers"
    
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    vendor_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("vendors.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    address_line1: Mapped[str] = mapped_column(String(255), nullable=False)
    address_line2: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    province: Mapped[str] = mapped_column(String(100), nullable=False)
    postal_code: Mapped[str] = mapped_column(String(20), nullable=False)
    country: Mapped[str] = mapped_column(String(100), default="Canada", nullable=False)
    contractor_name: Mapped[str] = mapped_column(String(255), nullable=False)
    service_location: Mapped[str] = mapped_column(String(255), default="Ontario, Canada", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Relationships
    vendor: Mapped["Vendor"] = relationship(back_populates="customers", lazy="selectin")
    contract: Mapped[Optional["Contract"]] = relationship(back_populates="customer", uselist=False, lazy="selectin")
    schedule: Mapped[Optional["ScheduleConfig"]] = relationship(back_populates="customer", uselist=False, lazy="selectin")
    invoices: Mapped[list["Invoice"]] = relationship(back_populates="customer", lazy="selectin")
    
    # Indexes
    __table_args__ = (
        Index("ix_customers_vendor_active", "vendor_id", "is_active"),
        Index("ix_customers_name", "name"),
    )


class Contract(Base, TimestampMixin):
    """Contract/billing configuration for a customer."""
    
    __tablename__ = "contracts"
    
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    customer_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("customers.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    invoice_prefix: Mapped[str] = mapped_column(String(10), nullable=False)
    frequency: Mapped[BillingFrequency] = mapped_column(
        String(20),
        default=BillingFrequency.MONTHLY,
        nullable=False,
    )
    default_hours: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("40.00"),
        nullable=False,
    )
    rate_per_hour: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )
    hst_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 4),
        default=Decimal("0.1300"),
        nullable=False,
    )
    payment_terms: Mapped[str] = mapped_column(String(50), default="Monthly", nullable=False)
    extra_fees: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    extra_fees_label: Mapped[str] = mapped_column(String(100), default="Other Fees", nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Relationships
    customer: Mapped["Customer"] = relationship(back_populates="contract", lazy="selectin")


class ScheduleConfig(Base, TimestampMixin):
    """Schedule configuration for automatic invoice generation."""
    
    __tablename__ = "schedule_configs"
    
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    customer_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("customers.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    auto_send_email: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), default="America/Toronto", nullable=False)
    
    # Schedule fields
    billing_weekday: Mapped[int] = mapped_column(Integer, default=4, nullable=False)  # 0=Mon, 4=Fri
    anchor_date: Mapped[date] = mapped_column(Date, default=date(2026, 1, 2), nullable=False)
    billing_day: Mapped[int] = mapped_column(Integer, default=1, nullable=False)  # 1-31 for monthly
    
    # Tracking
    last_run_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    next_run_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    # Relationships
    customer: Mapped["Customer"] = relationship(back_populates="schedule", lazy="selectin")


class Invoice(Base, TimestampMixin):
    """Generated invoice record."""
    
    __tablename__ = "invoices"
    
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    customer_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
    )
    invoice_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[InvoiceStatus] = mapped_column(
        String(20),
        default=InvoiceStatus.GENERATED,
        nullable=False,
    )
    
    # Financial data (Decimal for accuracy)
    total_hours: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    rate_per_hour: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    labor_subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    extra_fees: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    extra_fees_label: Mapped[str] = mapped_column(String(100), default="Other Fees", nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    hst_rate: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    hst_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    
    # File storage
    pdf_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Metadata
    generation_mode: Mapped[ExecutionMode] = mapped_column(String(20), nullable=False)
    
    # Relationships
    customer: Mapped["Customer"] = relationship(back_populates="invoices", lazy="selectin")
    lines: Mapped[list["InvoiceLine"]] = relationship(back_populates="invoice", lazy="selectin")
    email_logs: Mapped[list["EmailLog"]] = relationship(back_populates="invoice", lazy="selectin")
    
    # Indexes
    __table_args__ = (
        Index("ix_invoices_customer_date", "customer_id", "invoice_date"),
        Index("ix_invoices_status", "status"),
        Index("ix_invoices_number", "invoice_number"),
    )


class InvoiceLine(Base, TimestampMixin):
    """Individual line items on an invoice."""
    
    __tablename__ = "invoice_lines"
    
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    invoice_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Relationships
    invoice: Mapped["Invoice"] = relationship(back_populates="lines", lazy="selectin")


class EmailLog(Base, TimestampMixin):
    """Email sending log for audit trail."""
    
    __tablename__ = "email_logs"
    
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    invoice_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=False,
    )
    recipient_email: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[EmailStatus] = mapped_column(
        String(20),
        default=EmailStatus.PENDING,
        nullable=False,
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Relationships
    invoice: Mapped["Invoice"] = relationship(back_populates="email_logs", lazy="selectin")
    
    # Indexes
    __table_args__ = (
        Index("ix_email_logs_status", "status"),
        Index("ix_email_logs_invoice", "invoice_id"),
    )


class ExecutionLog(Base, TimestampMixin):
    """Execution log for tracking invoice generation runs."""
    
    __tablename__ = "execution_logs"
    
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    run_date: Mapped[date] = mapped_column(Date, nullable=False)
    mode: Mapped[ExecutionMode] = mapped_column(String(20), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Results
    customers_loaded: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    schedule_matches: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pdfs_generated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    emails_sent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Error tracking
    error_trace: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Request tracking
    request_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    triggered_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # User email or "scheduler"
    
    # Indexes
    __table_args__ = (
        Index("ix_execution_logs_run_date", "run_date"),
        Index("ix_execution_logs_mode", "mode"),
    )


class SmtpConfig(Base, TimestampMixin):
    """SMTP configuration (can be per-vendor or global)."""
    
    __tablename__ = "smtp_configs"
    
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    vendor_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("vendors.id", ondelete="CASCADE"),
        nullable=True,  # NULL = global default
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int] = mapped_column(Integer, default=587, nullable=False)
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    encrypted_password: Mapped[str] = mapped_column(String(500), nullable=False)  # Encrypted
    from_email: Mapped[str] = mapped_column(String(255), nullable=False)
    from_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    use_tls: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Indexes
    __table_args__ = (
        Index("ix_smtp_configs_vendor", "vendor_id"),
    )
