"""
Job match routes: list matches with job details, save/apply actions.
Fix #17: Added Pydantic response_model on all endpoints.
Fix #8: is_synthetic exposed in embedded job objects.
"""
import uuid
import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.match import JobMatch
from app.models.resume import Resume
from app.schemas import MatchOut, MatchToggleOut, MatchStatsOut, JobInMatchOut

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/matches", tags=["matches"])


# Fix #21: /stats is registered BEFORE /{match_id} routes to avoid ambiguity
@router.get("/stats", response_model=MatchStatsOut)
async def match_stats(db: AsyncSession = Depends(get_db)):
    """Return dashboard statistics."""
    total_q = await db.execute(select(func.count(JobMatch.id)))
    total = total_q.scalar_one()

    high_q = await db.execute(
        select(func.count(JobMatch.id)).where(JobMatch.match_score >= 70)
    )
    high = high_q.scalar_one()

    saved_q = await db.execute(
        select(func.count(JobMatch.id)).where(JobMatch.is_saved == True)
    )
    saved = saved_q.scalar_one()

    applied_q = await db.execute(
        select(func.count(JobMatch.id)).where(JobMatch.is_applied == True)
    )
    applied = applied_q.scalar_one()

    return MatchStatsOut(
        total_matches=total,
        high_score_matches=high,
        saved_jobs=saved,
        applied_jobs=applied,
    )


@router.get("/", response_model=List[MatchOut])
async def list_matches(
    resume_id: Optional[uuid.UUID] = Query(None),
    min_score: float = Query(0.0, ge=0, le=100),
    saved_only: bool = Query(False),
    applied_only: bool = Query(False),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """
    List all job matches. Optionally filter by resume, score threshold,
    saved or applied status. Includes full job details.
    """
    stmt = (
        select(JobMatch)
        .options(selectinload(JobMatch.job), selectinload(JobMatch.resume))
        .where(JobMatch.match_score >= min_score)
    )
    if resume_id:
        stmt = stmt.where(JobMatch.resume_id == resume_id)
    else:
        # Default: active resume
        active = await db.execute(
            select(Resume).where(Resume.is_active == True).order_by(Resume.created_at.desc())
        )
        active_resume = active.scalar_one_or_none()
        if active_resume:
            stmt = stmt.where(JobMatch.resume_id == active_resume.id)

    if saved_only:
        stmt = stmt.where(JobMatch.is_saved == True)
    if applied_only:
        stmt = stmt.where(JobMatch.is_applied == True)

    stmt = stmt.order_by(JobMatch.match_score.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    matches = result.scalars().all()

    return [_to_match_out(m) for m in matches]


@router.patch("/{match_id}/save", response_model=MatchToggleOut)
async def toggle_save(match_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Toggle the saved state of a job match."""
    m = await _get_match(match_id, db)
    m.is_saved = not m.is_saved
    await db.commit()
    return MatchToggleOut(id=m.id, is_saved=m.is_saved)


@router.patch("/{match_id}/apply", response_model=MatchToggleOut)
async def toggle_applied(match_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Mark a job match as applied."""
    m = await _get_match(match_id, db)
    m.is_applied = not m.is_applied
    await db.commit()
    return MatchToggleOut(id=m.id, is_applied=m.is_applied)


# ─── Helpers ─────────────────────────────────────────────────────────────────

async def _get_match(match_id: uuid.UUID, db: AsyncSession) -> JobMatch:
    result = await db.execute(
        select(JobMatch)
        .options(selectinload(JobMatch.job))
        .where(JobMatch.id == match_id)
    )
    m = result.scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=404, detail="Match not found")
    return m


def _to_match_out(m: JobMatch) -> MatchOut:
    """Convert ORM JobMatch to typed MatchOut schema."""
    job = m.job
    job_out = None
    if job:
        job_out = JobInMatchOut(
            id=job.id,
            title=job.title,
            company=job.company,
            location=job.location or "",
            description=job.description or "",
            requirements=job.requirements or "",
            url=job.url or "",
            source=job.source or "",
            employment_type=job.employment_type or "",
            posted_date=job.posted_date or "",
            is_synthetic=job.is_synthetic,
        )
    return MatchOut(
        id=m.id,
        match_score=m.match_score,
        explanation=m.explanation,
        is_saved=m.is_saved,
        is_applied=m.is_applied,
        is_notified=m.is_notified,
        created_at=m.created_at,
        job=job_out,
    )
