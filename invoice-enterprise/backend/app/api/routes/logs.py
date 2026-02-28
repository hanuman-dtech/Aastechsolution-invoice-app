"""
Execution Logs API routes.
"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import get_logger
from app.models import ExecutionLog, ExecutionMode
from app.schemas import ExecutionLogResponse


logger = get_logger(__name__)
router = APIRouter(prefix="/execution-logs", tags=["Execution Logs"])


@router.get("", response_model=list[ExecutionLogResponse])
async def list_execution_logs(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    mode: Optional[ExecutionMode] = Query(default=None),
    start_date: Optional[date] = Query(default=None),
    end_date: Optional[date] = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """
    List execution logs with pagination and filters.
    """
    query = select(ExecutionLog)
    
    if mode:
        query = query.where(ExecutionLog.mode == mode)
    
    if start_date:
        query = query.where(ExecutionLog.run_date >= start_date)
    
    if end_date:
        query = query.where(ExecutionLog.run_date <= end_date)
    
    # Apply pagination
    offset = (page - 1) * per_page
    query = query.order_by(ExecutionLog.started_at.desc()).offset(offset).limit(per_page)
    
    result = await db.execute(query)
    logs = result.scalars().all()
    
    return [ExecutionLogResponse.model_validate(log) for log in logs]


@router.get("/{log_id}", response_model=ExecutionLogResponse)
async def get_execution_log(
    log_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get a single execution log with full details.
    """
    result = await db.execute(
        select(ExecutionLog).where(ExecutionLog.id == log_id)
    )
    log = result.scalar_one_or_none()
    
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Execution log not found: {log_id}",
        )
    
    return ExecutionLogResponse.model_validate(log)


@router.get("/stats/summary")
async def get_execution_stats(
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    """
    Get execution statistics for the last N days.
    """
    from datetime import timedelta
    cutoff = date.today() - timedelta(days=days)
    
    # Total runs
    total_result = await db.execute(
        select(func.count(ExecutionLog.id))
        .where(ExecutionLog.run_date >= cutoff)
    )
    total_runs = total_result.scalar() or 0
    
    # Successful runs (failures = 0)
    success_result = await db.execute(
        select(func.count(ExecutionLog.id))
        .where(ExecutionLog.run_date >= cutoff)
        .where(ExecutionLog.failures == 0)
    )
    successful_runs = success_result.scalar() or 0
    
    # Total PDFs generated
    pdfs_result = await db.execute(
        select(func.sum(ExecutionLog.pdfs_generated))
        .where(ExecutionLog.run_date >= cutoff)
    )
    total_pdfs = pdfs_result.scalar() or 0
    
    # Total emails sent
    emails_result = await db.execute(
        select(func.sum(ExecutionLog.emails_sent))
        .where(ExecutionLog.run_date >= cutoff)
    )
    total_emails = emails_result.scalar() or 0
    
    # Runs by mode
    mode_result = await db.execute(
        select(ExecutionLog.mode, func.count(ExecutionLog.id))
        .where(ExecutionLog.run_date >= cutoff)
        .group_by(ExecutionLog.mode)
    )
    runs_by_mode = {row[0].value: row[1] for row in mode_result.all()}
    
    return {
        "period_days": days,
        "total_runs": total_runs,
        "successful_runs": successful_runs,
        "failed_runs": total_runs - successful_runs,
        "success_rate": (successful_runs / total_runs * 100) if total_runs > 0 else 0,
        "total_pdfs_generated": total_pdfs,
        "total_emails_sent": total_emails,
        "runs_by_mode": runs_by_mode,
    }
