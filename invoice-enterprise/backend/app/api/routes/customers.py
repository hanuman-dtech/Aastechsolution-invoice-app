"""
Customer API routes.
"""

from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.logging import get_logger
from app.models import BillingFrequency, Contract, Customer, Invoice, ScheduleConfig, Vendor
from app.schemas import (
    ContractCreate,
    ContractResponse,
    ContractUpdate,
    CustomerCreate,
    CustomerResponse,
    CustomerUpdate,
    CustomerWithContract,
    ScheduleConfigCreate,
    ScheduleConfigResponse,
    ScheduleConfigUpdate,
)
from app.services import schedule_service


logger = get_logger(__name__)
router = APIRouter(prefix="/customers", tags=["Customers"])


@router.get("", response_model=list[CustomerWithContract])
async def list_customers(
    vendor_id: Optional[str] = Query(default=None),
    active_only: bool = Query(default=True),
    db: AsyncSession = Depends(get_db),
):
    """
    List all customers with their contracts and schedules.
    """
    query = (
        select(Customer)
        .options(
            selectinload(Customer.contract),
            selectinload(Customer.schedule),
            selectinload(Customer.vendor),
        )
    )
    
    if vendor_id:
        query = query.where(Customer.vendor_id == vendor_id)
    
    if active_only:
        query = query.where(Customer.is_active == True)
    
    query = query.order_by(Customer.name)
    
    result = await db.execute(query)
    customers = result.scalars().all()
    
    # Compute last/next invoice dates
    response = []
    for customer in customers:
        customer_data = CustomerWithContract.model_validate(customer)
        
        # Get last invoiced date
        last_invoice_result = await db.execute(
            select(Invoice.invoice_date)
            .where(Invoice.customer_id == customer.id)
            .order_by(Invoice.invoice_date.desc())
            .limit(1)
        )
        last_invoice_date = last_invoice_result.scalar_one_or_none()
        customer_data.last_invoiced_date = last_invoice_date
        
        # Compute next invoice date
        if customer.contract and customer.schedule:
            frequency = BillingFrequency(customer.contract.frequency)
            from_date = date.today()
            customer_data.next_invoice_date = schedule_service.compute_next_invoice_date(
                from_date, frequency, customer.schedule
            )
        
        response.append(customer_data)
    
    return response


@router.get("/{customer_id}", response_model=CustomerWithContract)
async def get_customer(
    customer_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get a single customer with contract and schedule.
    """
    result = await db.execute(
        select(Customer)
        .options(
            selectinload(Customer.contract),
            selectinload(Customer.schedule),
            selectinload(Customer.vendor),
        )
        .where(Customer.id == customer_id)
    )
    customer = result.scalar_one_or_none()
    
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer not found: {customer_id}",
        )
    
    customer_data = CustomerWithContract.model_validate(customer)
    
    # Get last invoiced date
    last_invoice_result = await db.execute(
        select(Invoice.invoice_date)
        .where(Invoice.customer_id == customer.id)
        .order_by(Invoice.invoice_date.desc())
        .limit(1)
    )
    customer_data.last_invoiced_date = last_invoice_result.scalar_one_or_none()
    
    # Compute next invoice date
    if customer.contract and customer.schedule:
        frequency = BillingFrequency(customer.contract.frequency)
        customer_data.next_invoice_date = schedule_service.compute_next_invoice_date(
            date.today(), frequency, customer.schedule
        )
    
    return customer_data


@router.post("", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
async def create_customer(
    data: CustomerCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new customer.
    """
    # Verify vendor exists
    vendor_result = await db.execute(
        select(Vendor).where(Vendor.id == data.vendor_id)
    )
    if not vendor_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Vendor not found: {data.vendor_id}",
        )
    
    customer_data = data.model_dump(exclude={"payment_terms"})
    customer = Customer(**customer_data)
    db.add(customer)
    await db.flush()

    # Create default contract + schedule so invoice generation works immediately.
    prefix_seed = "".join(ch for ch in customer.name.upper() if ch.isalnum())[:4]
    invoice_prefix = prefix_seed if prefix_seed else "INV"

    contract = Contract(
        customer_id=customer.id,
        invoice_prefix=invoice_prefix,
        frequency=BillingFrequency.MONTHLY,
        default_hours=Decimal("40.00"),
        rate_per_hour=Decimal("50.00"),
        hst_rate=Decimal("0.13"),
        payment_terms=data.payment_terms or "Monthly",
        extra_fees=Decimal("0.00"),
        extra_fees_label="Other Fees",
    )
    schedule = ScheduleConfig(
        customer_id=customer.id,
        is_enabled=True,
        auto_send_email=False,
        timezone="America/Toronto",
        billing_weekday=4,
        anchor_date=date.today(),
        billing_day=1,
    )

    db.add(contract)
    db.add(schedule)
    await db.commit()
    await db.refresh(customer)
    
    return CustomerResponse.model_validate(customer)


@router.patch("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: str,
    data: CustomerUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Update a customer.
    """
    result = await db.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    customer = result.scalar_one_or_none()
    
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer not found: {customer_id}",
        )
    
    update_data = data.model_dump(exclude_unset=True, exclude={"payment_terms"})
    for key, value in update_data.items():
        setattr(customer, key, value)

    # Persist per-customer payment terms on contract.
    if data.payment_terms is not None:
        contract_result = await db.execute(
            select(Contract).where(Contract.customer_id == customer_id)
        )
        contract = contract_result.scalar_one_or_none()

        if contract:
            contract.payment_terms = data.payment_terms
        else:
            # Safety fallback: create a default contract if missing.
            prefix_seed = "".join(ch for ch in customer.name.upper() if ch.isalnum())[:4]
            invoice_prefix = prefix_seed if prefix_seed else "INV"
            db.add(
                Contract(
                    customer_id=customer.id,
                    invoice_prefix=invoice_prefix,
                    frequency=BillingFrequency.MONTHLY,
                    default_hours=Decimal("40.00"),
                    rate_per_hour=Decimal("50.00"),
                    hst_rate=Decimal("0.13"),
                    payment_terms=data.payment_terms,
                    extra_fees=Decimal("0.00"),
                    extra_fees_label="Other Fees",
                )
            )
    
    await db.commit()
    await db.refresh(customer)
    
    return CustomerResponse.model_validate(customer)


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_customer(
    customer_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Soft-delete a customer (set is_active = false).
    """
    result = await db.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    customer = result.scalar_one_or_none()
    
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer not found: {customer_id}",
        )
    
    customer.is_active = False
    await db.commit()


# === Contract Routes ===

@router.post("/{customer_id}/contract", response_model=ContractResponse, status_code=status.HTTP_201_CREATED)
async def create_contract(
    customer_id: str,
    data: ContractCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a contract for a customer.
    """
    # Verify customer exists
    customer_result = await db.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    if not customer_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer not found: {customer_id}",
        )
    
    # Check for existing contract
    existing_result = await db.execute(
        select(Contract).where(Contract.customer_id == customer_id)
    )
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Customer already has a contract",
        )
    
    contract_data = data.model_dump()
    contract_data["customer_id"] = customer_id
    
    contract = Contract(**contract_data)
    db.add(contract)
    await db.commit()
    await db.refresh(contract)
    
    return ContractResponse.model_validate(contract)


@router.patch("/{customer_id}/contract", response_model=ContractResponse)
async def update_contract(
    customer_id: str,
    data: ContractUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Update a customer's contract.
    """
    result = await db.execute(
        select(Contract).where(Contract.customer_id == customer_id)
    )
    contract = result.scalar_one_or_none()
    
    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contract not found for customer: {customer_id}",
        )
    
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(contract, key, value)
    
    await db.commit()
    await db.refresh(contract)
    
    return ContractResponse.model_validate(contract)


# === Schedule Routes ===

@router.post("/{customer_id}/schedule", response_model=ScheduleConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_schedule(
    customer_id: str,
    data: ScheduleConfigCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a schedule configuration for a customer.
    """
    # Verify customer exists
    customer_result = await db.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    if not customer_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer not found: {customer_id}",
        )
    
    # Check for existing schedule
    existing_result = await db.execute(
        select(ScheduleConfig).where(ScheduleConfig.customer_id == customer_id)
    )
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Customer already has a schedule",
        )
    
    schedule_data = data.model_dump()
    schedule_data["customer_id"] = customer_id
    
    schedule = ScheduleConfig(**schedule_data)
    db.add(schedule)
    await db.commit()
    await db.refresh(schedule)
    
    return ScheduleConfigResponse.model_validate(schedule)


@router.patch("/{customer_id}/schedule", response_model=ScheduleConfigResponse)
async def update_schedule(
    customer_id: str,
    data: ScheduleConfigUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Update a customer's schedule configuration.
    """
    result = await db.execute(
        select(ScheduleConfig).where(ScheduleConfig.customer_id == customer_id)
    )
    schedule = result.scalar_one_or_none()
    
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule not found for customer: {customer_id}",
        )
    
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(schedule, key, value)
    
    await db.commit()
    await db.refresh(schedule)
    
    return ScheduleConfigResponse.model_validate(schedule)


@router.post("/{customer_id}/schedule/toggle", response_model=ScheduleConfigResponse)
async def toggle_schedule(
    customer_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Toggle schedule enabled/disabled state.
    """
    result = await db.execute(
        select(ScheduleConfig).where(ScheduleConfig.customer_id == customer_id)
    )
    schedule = result.scalar_one_or_none()
    
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule not found for customer: {customer_id}",
        )
    
    schedule.is_enabled = not schedule.is_enabled
    await db.commit()
    await db.refresh(schedule)
    
    return ScheduleConfigResponse.model_validate(schedule)


@router.get("/{customer_id}/next-invoice-preview")
async def preview_next_invoice(
    customer_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Preview the next invoice date and computed billing period.
    """
    result = await db.execute(
        select(Customer)
        .options(
            selectinload(Customer.contract),
            selectinload(Customer.schedule),
        )
        .where(Customer.id == customer_id)
    )
    customer = result.scalar_one_or_none()
    
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer not found: {customer_id}",
        )
    
    if not customer.contract or not customer.schedule:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Customer has no contract or schedule configured",
        )
    
    frequency = BillingFrequency(customer.contract.frequency)
    next_date = schedule_service.compute_next_invoice_date(
        date.today(), frequency, customer.schedule
    )
    period_start, period_end = schedule_service.compute_billing_period(
        next_date, frequency
    )
    
    estimated_amount = (
        customer.contract.default_hours * customer.contract.rate_per_hour
        + customer.contract.extra_fees
    ) * (1 + customer.contract.hst_rate)
    
    return {
        "customer_id": customer.id,
        "customer_name": customer.name,
        "next_invoice_date": next_date.isoformat(),
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "frequency": frequency.value,
        "estimated_amount": float(estimated_amount.quantize(Decimal("0.01"))),
        "message": f"Next invoice will be generated on: {schedule_service.format_date(next_date)}",
    }


from decimal import Decimal
