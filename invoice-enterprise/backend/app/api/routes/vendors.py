"""
Vendor API routes.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.logging import get_logger
from app.models import Vendor
from app.schemas import VendorCreate, VendorResponse, VendorUpdate


logger = get_logger(__name__)
router = APIRouter(prefix="/vendors", tags=["Vendors"])


@router.get("", response_model=list[VendorResponse])
async def list_vendors(
    active_only: bool = Query(default=True),
    db: AsyncSession = Depends(get_db),
):
    """
    List all vendors.
    """
    query = select(Vendor)
    
    if active_only:
        query = query.where(Vendor.is_active == True)
    
    query = query.order_by(Vendor.name)
    
    result = await db.execute(query)
    vendors = result.scalars().all()
    
    return [VendorResponse.model_validate(v) for v in vendors]


@router.get("/{vendor_id}", response_model=VendorResponse)
async def get_vendor(
    vendor_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get a single vendor.
    """
    result = await db.execute(
        select(Vendor).where(Vendor.id == vendor_id)
    )
    vendor = result.scalar_one_or_none()
    
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vendor not found: {vendor_id}",
        )
    
    return VendorResponse.model_validate(vendor)


@router.post("", response_model=VendorResponse, status_code=status.HTTP_201_CREATED)
async def create_vendor(
    data: VendorCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new vendor.
    """
    vendor = Vendor(**data.model_dump())
    db.add(vendor)
    await db.commit()
    await db.refresh(vendor)
    
    return VendorResponse.model_validate(vendor)


@router.patch("/{vendor_id}", response_model=VendorResponse)
async def update_vendor(
    vendor_id: str,
    data: VendorUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Update a vendor.
    """
    result = await db.execute(
        select(Vendor).where(Vendor.id == vendor_id)
    )
    vendor = result.scalar_one_or_none()
    
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vendor not found: {vendor_id}",
        )
    
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(vendor, key, value)
    
    await db.commit()
    await db.refresh(vendor)
    
    return VendorResponse.model_validate(vendor)


@router.delete("/{vendor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vendor(
    vendor_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Soft-delete a vendor.
    """
    result = await db.execute(
        select(Vendor).where(Vendor.id == vendor_id)
    )
    vendor = result.scalar_one_or_none()
    
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vendor not found: {vendor_id}",
        )
    
    vendor.is_active = False
    await db.commit()
