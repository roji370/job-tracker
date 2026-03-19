"""
Job routes: list, search, get by ID, deactivate.
Fix #17: Added Pydantic response_model on all endpoints.
Fix #8: is_synthetic exposed in all responses.
"""
import uuid
import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func

from app.database import get_db
from app.models.job import Job
from app.schemas import JobOut, JobDeactivateOut, JobPaginatedOut

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/", response_model=JobPaginatedOut)
async def list_jobs(
    source: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    active_only: bool = Query(True),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List all scraped jobs with optional filtering."""
    filters = []
    if active_only:
        filters.append(Job.is_active == True)
    if source:
        filters.append(Job.source == source)
    if search:
        term = f"%{search}%"
        filters.append(
            or_(
                Job.title.ilike(term),
                Job.company.ilike(term),
                Job.location.ilike(term),
                Job.description.ilike(term),
            )
        )
        
    # Count query
    count_stmt = select(func.count(Job.id))
    for f in filters:
        count_stmt = count_stmt.where(f)
    
    count_result = await db.execute(count_stmt)
    total_jobs = count_result.scalar_one()

    # Data query
    stmt = select(Job)
    for f in filters:
        stmt = stmt.where(f)

    stmt = stmt.order_by(Job.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    
    return {
        "items": result.scalars().all(),
        "total": total_jobs
    }


@router.get("/{job_id}", response_model=JobOut)
async def get_job(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Get a specific job by ID."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.patch("/{job_id}/deactivate", response_model=JobDeactivateOut)
async def deactivate_job(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Mark a job as inactive (hidden from listings)."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    job.is_active = False
    await db.commit()
    return {"message": "Job deactivated", "id": job.id}
