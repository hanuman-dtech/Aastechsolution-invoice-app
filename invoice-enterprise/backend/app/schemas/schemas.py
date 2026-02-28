"""
Pydantic schemas for API request/response validation.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.models import (
    BillingFrequency,
    EmailStatus,
    ExecutionMode,
    InvoiceStatus,
    UserRole,
)


# Base schemas with common config
class BaseSchema(BaseModel):
    """Base schema with common configuration."""
    
    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True,
        validate_assignment=True,
    )


# ============== User Schemas ==============

class UserBase(BaseSchema):
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=255)
    role: UserRole = UserRole.VIEWER


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)


class UserUpdate(BaseSchema):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    id: str
    is_active: bool
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class UserLogin(BaseSchema):
    email: EmailStr
    password: str


class TokenResponse(BaseSchema):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


# ============== Vendor Schemas ==============

class VendorBase(BaseSchema):
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    address_line1: str = Field(..., max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: str = Field(..., max_length=100)
    province: str = Field(..., max_length=100)
    postal_code: str = Field(..., max_length=20)
    country: str = Field(default="Canada", max_length=100)
    hst_number: str = Field(..., max_length=50)
    default_contractor: str = Field(..., max_length=255)


class VendorCreate(VendorBase):
    pass


class VendorUpdate(BaseSchema):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    address_line1: Optional[str] = Field(None, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    province: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: Optional[str] = Field(None, max_length=100)
    hst_number: Optional[str] = Field(None, max_length=50)
    default_contractor: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None


class VendorResponse(VendorBase):
    id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


# ============== Customer Schemas ==============

class CustomerBase(BaseSchema):
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    address_line1: str = Field(..., max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: str = Field(..., max_length=100)
    province: str = Field(..., max_length=100)
    postal_code: str = Field(..., max_length=20)
    country: str = Field(default="Canada", max_length=100)
    contractor_name: str = Field(..., max_length=255)
    service_location: str = Field(default="Ontario, Canada", max_length=255)


class CustomerCreate(CustomerBase):
    vendor_id: str
    payment_terms: Optional[str] = Field(default=None, max_length=50)


class CustomerUpdate(BaseSchema):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    address_line1: Optional[str] = Field(None, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    province: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: Optional[str] = Field(None, max_length=100)
    contractor_name: Optional[str] = Field(None, max_length=255)
    service_location: Optional[str] = Field(None, max_length=255)
    payment_terms: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = None


class CustomerResponse(CustomerBase):
    id: str
    vendor_id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    # Computed fields
    last_invoiced_date: Optional[date] = None
    next_invoice_date: Optional[date] = None


class CustomerWithContract(CustomerResponse):
    contract: Optional["ContractResponse"] = None
    schedule: Optional["ScheduleConfigResponse"] = None


# ============== Contract Schemas ==============

class ContractBase(BaseSchema):
    invoice_prefix: str = Field(..., min_length=1, max_length=10)
    frequency: BillingFrequency = BillingFrequency.MONTHLY
    default_hours: Decimal = Field(default=Decimal("40.00"), ge=0)
    rate_per_hour: Decimal = Field(..., ge=0)
    hst_rate: Decimal = Field(default=Decimal("0.13"), ge=0, le=1)
    payment_terms: str = Field(default="Monthly", max_length=50)
    extra_fees: Decimal = Field(default=Decimal("0.00"), ge=0)
    extra_fees_label: str = Field(default="Other Fees", max_length=100)
    notes: Optional[str] = None


class ContractCreate(ContractBase):
    customer_id: str


class ContractUpdate(BaseSchema):
    invoice_prefix: Optional[str] = Field(None, min_length=1, max_length=10)
    frequency: Optional[BillingFrequency] = None
    default_hours: Optional[Decimal] = Field(None, ge=0)
    rate_per_hour: Optional[Decimal] = Field(None, ge=0)
    hst_rate: Optional[Decimal] = Field(None, ge=0, le=1)
    payment_terms: Optional[str] = Field(None, max_length=50)
    extra_fees: Optional[Decimal] = Field(None, ge=0)
    extra_fees_label: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class ContractResponse(ContractBase):
    id: str
    customer_id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


# ============== Schedule Config Schemas ==============

class ScheduleConfigBase(BaseSchema):
    is_enabled: bool = True
    auto_send_email: bool = False
    timezone: str = Field(default="America/Toronto", max_length=50)
    billing_weekday: int = Field(default=4, ge=0, le=6)  # 0=Mon, 6=Sun
    anchor_date: date = Field(default_factory=lambda: date(2026, 1, 2))
    billing_day: int = Field(default=1, ge=1, le=31)


class ScheduleConfigCreate(ScheduleConfigBase):
    customer_id: str


class ScheduleConfigUpdate(BaseSchema):
    is_enabled: Optional[bool] = None
    auto_send_email: Optional[bool] = None
    timezone: Optional[str] = Field(None, max_length=50)
    billing_weekday: Optional[int] = Field(None, ge=0, le=6)
    anchor_date: Optional[date] = None
    billing_day: Optional[int] = Field(None, ge=1, le=31)


class ScheduleConfigResponse(ScheduleConfigBase):
    id: str
    customer_id: str
    last_run_date: Optional[date] = None
    next_run_date: Optional[date] = None
    created_at: datetime
    updated_at: datetime


# ============== Invoice Schemas ==============

class InvoiceBase(BaseSchema):
    invoice_date: date
    period_start: date
    period_end: date
    total_hours: Decimal = Field(..., ge=0)
    rate_per_hour: Decimal = Field(..., ge=0)
    extra_fees: Decimal = Field(default=Decimal("0.00"), ge=0)
    extra_fees_label: str = Field(default="Other Fees", max_length=100)
    hst_rate: Decimal = Field(default=Decimal("0.13"), ge=0, le=1)


class QuickModeRequest(BaseSchema):
    """Quick mode - only 3 inputs."""
    customer_id: str
    run_date: date
    total_hours: Decimal = Field(..., ge=0)
    send_email: bool = False


class WizardModeRequest(BaseSchema):
    """Wizard mode - full manual input."""
    customer_id: str
    invoice_date: date
    period_start: date
    period_end: date
    total_hours: Decimal = Field(..., ge=0)
    rate_per_hour: Decimal = Field(..., ge=0)
    hst_rate: Decimal = Field(default=Decimal("0.13"), ge=0, le=1)
    extra_fees: Decimal = Field(default=Decimal("0.00"), ge=0)
    extra_fees_label: str = Field(default="Other Fees", max_length=100)
    payment_terms: str = Field(default="Monthly", max_length=50)
    send_email: bool = False
    allow_duplicate: bool = False


class ScheduledRunRequest(BaseSchema):
    """Scheduled run request."""
    run_date: date
    ignore_schedule: bool = False
    send_email: bool = False
    customer_ids: Optional[list[str]] = None  # If None, run for all


class ManualDateOverrideRequest(BaseSchema):
    """Manual date override mode."""
    customer_id: str
    invoice_date: date
    period_start: date
    period_end: date
    send_email: bool = False


class InvoiceCreate(InvoiceBase):
    customer_id: str
    generation_mode: ExecutionMode


class InvoiceResponse(InvoiceBase):
    id: str
    customer_id: str
    invoice_number: str
    status: InvoiceStatus
    labor_subtotal: Decimal
    subtotal: Decimal
    hst_amount: Decimal
    total: Decimal
    pdf_path: Optional[str] = None
    generation_mode: ExecutionMode
    created_at: datetime
    updated_at: datetime


class InvoiceWithCustomer(InvoiceResponse):
    customer: CustomerResponse


class InvoiceListResponse(BaseSchema):
    items: list[InvoiceResponse]
    total: int
    page: int
    per_page: int
    pages: int


# ============== Invoice Line Schemas ==============

class InvoiceLineBase(BaseSchema):
    description: str = Field(..., max_length=500)
    quantity: Decimal = Field(..., ge=0)
    unit_price: Decimal = Field(..., ge=0)
    sort_order: int = 0


class InvoiceLineCreate(InvoiceLineBase):
    invoice_id: str


class InvoiceLineResponse(InvoiceLineBase):
    id: str
    invoice_id: str
    line_total: Decimal
    created_at: datetime
    updated_at: datetime


# ============== Email Log Schemas ==============

class EmailLogResponse(BaseSchema):
    id: str
    invoice_id: str
    recipient_email: str
    subject: str
    status: EmailStatus
    error_message: Optional[str] = None
    sent_at: Optional[datetime] = None
    retry_count: int
    created_at: datetime
    updated_at: datetime


class ResendEmailRequest(BaseSchema):
    invoice_id: str


# ============== Execution Log Schemas ==============

class ExecutionLogResponse(BaseSchema):
    id: str
    run_date: date
    mode: ExecutionMode
    started_at: datetime
    completed_at: Optional[datetime] = None
    customers_loaded: int
    schedule_matches: int
    pdfs_generated: int
    emails_sent: int
    failures: int
    error_trace: Optional[str] = None
    request_id: Optional[str] = None
    triggered_by: Optional[str] = None
    created_at: datetime


# ============== SMTP Config Schemas ==============

class SmtpConfigBase(BaseSchema):
    name: str = Field(..., min_length=1, max_length=100)
    host: str = Field(..., max_length=255)
    port: int = Field(default=587, ge=1, le=65535)
    username: str = Field(..., max_length=255)
    from_email: EmailStr
    from_name: Optional[str] = Field(None, max_length=255)
    use_tls: bool = True


class SmtpConfigCreate(SmtpConfigBase):
    vendor_id: Optional[str] = None
    password: str = Field(..., min_length=1)


class SmtpConfigUpdate(BaseSchema):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    host: Optional[str] = Field(None, max_length=255)
    port: Optional[int] = Field(None, ge=1, le=65535)
    username: Optional[str] = Field(None, max_length=255)
    password: Optional[str] = None  # Only update if provided
    from_email: Optional[EmailStr] = None
    from_name: Optional[str] = Field(None, max_length=255)
    use_tls: Optional[bool] = None
    is_active: Optional[bool] = None


class SmtpConfigResponse(SmtpConfigBase):
    id: str
    vendor_id: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class SmtpTestRequest(BaseSchema):
    config_id: str
    test_email: EmailStr


class SmtpTestResponse(BaseSchema):
    success: bool
    message: str


# ============== Execution Summary Schemas ==============

class ExecutionSummary(BaseSchema):
    """Summary returned after invoice generation."""
    execution_id: str
    run_date: date
    mode: ExecutionMode
    customers_loaded: int
    schedule_matches: int
    pdfs_generated: int
    emails_sent: int
    emails_failed: int
    failures: list[dict]  # [{customer_id, customer_name, error}]
    generated_invoices: list[InvoiceResponse]
    download_links: list[str]
    duration_seconds: float


# ============== Dashboard Schemas ==============

class DashboardStats(BaseSchema):
    total_invoices_this_month: int
    total_revenue_this_month: Decimal
    pending_emails: int
    upcoming_scheduled: int
    last_run_date: Optional[date] = None
    last_run_status: Optional[str] = None


class UpcomingInvoice(BaseSchema):
    customer_id: str
    customer_name: str
    next_invoice_date: date
    frequency: BillingFrequency
    estimated_amount: Decimal


# Forward references
CustomerWithContract.model_rebuild()
