"""
SMTP Configuration API routes.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import get_logger
from app.core.security import decrypt_value, encrypt_value
from app.models import SmtpConfig
from app.schemas import SmtpConfigCreate, SmtpConfigResponse, SmtpConfigUpdate, SmtpTestRequest, SmtpTestResponse
from app.services import email_service


logger = get_logger(__name__)
router = APIRouter(prefix="/smtp-configs", tags=["SMTP Configuration"])


@router.get("", response_model=list[SmtpConfigResponse])
async def list_smtp_configs(
    vendor_id: Optional[str] = Query(default=None),
    active_only: bool = Query(default=True),
    db: AsyncSession = Depends(get_db),
):
    """
    List SMTP configurations.
    """
    query = select(SmtpConfig)
    
    if vendor_id:
        query = query.where(SmtpConfig.vendor_id == vendor_id)
    
    if active_only:
        query = query.where(SmtpConfig.is_active == True)
    
    result = await db.execute(query)
    configs = result.scalars().all()
    
    return [SmtpConfigResponse.model_validate(c) for c in configs]


@router.get("/{config_id}", response_model=SmtpConfigResponse)
async def get_smtp_config(
    config_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get a single SMTP configuration.
    """
    result = await db.execute(
        select(SmtpConfig).where(SmtpConfig.id == config_id)
    )
    config = result.scalar_one_or_none()
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"SMTP config not found: {config_id}",
        )
    
    return SmtpConfigResponse.model_validate(config)


@router.post("", response_model=SmtpConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_smtp_config(
    data: SmtpConfigCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new SMTP configuration.
    
    Password will be encrypted before storage.
    """
    config_data = data.model_dump(exclude={"password"})
    config_data["encrypted_password"] = encrypt_value(data.password)
    
    config = SmtpConfig(**config_data)
    db.add(config)
    await db.commit()
    await db.refresh(config)
    
    return SmtpConfigResponse.model_validate(config)


@router.patch("/{config_id}", response_model=SmtpConfigResponse)
async def update_smtp_config(
    config_id: str,
    data: SmtpConfigUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Update an SMTP configuration.
    
    Password will only be updated if provided.
    """
    result = await db.execute(
        select(SmtpConfig).where(SmtpConfig.id == config_id)
    )
    config = result.scalar_one_or_none()
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"SMTP config not found: {config_id}",
        )
    
    update_data = data.model_dump(exclude_unset=True, exclude={"password"})
    
    # Handle password separately (encrypt if provided)
    if data.password is not None:
        config.encrypted_password = encrypt_value(data.password)
    
    for key, value in update_data.items():
        setattr(config, key, value)
    
    await db.commit()
    await db.refresh(config)
    
    return SmtpConfigResponse.model_validate(config)


@router.delete("/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_smtp_config(
    config_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Soft-delete an SMTP configuration.
    """
    result = await db.execute(
        select(SmtpConfig).where(SmtpConfig.id == config_id)
    )
    config = result.scalar_one_or_none()
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"SMTP config not found: {config_id}",
        )
    
    config.is_active = False
    await db.commit()


@router.post("/{config_id}/test", response_model=SmtpTestResponse)
async def test_smtp_config(
    config_id: str,
    test_email: str = Query(..., description="Email address to send test to"),
    db: AsyncSession = Depends(get_db),
):
    """
    Test an SMTP configuration by sending a test email.
    """
    result = await db.execute(
        select(SmtpConfig).where(SmtpConfig.id == config_id)
    )
    config = result.scalar_one_or_none()
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"SMTP config not found: {config_id}",
        )
    
    # Decrypt password and test
    password = decrypt_value(config.encrypted_password)
    
    success, message = await email_service.test_smtp_connection(
        smtp_host=config.host,
        smtp_port=config.port,
        smtp_user=config.username,
        smtp_password=password,
        test_email=test_email,
        use_tls=config.use_tls,
    )
    
    return SmtpTestResponse(success=success, message=message)
