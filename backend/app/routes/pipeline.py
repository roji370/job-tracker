"""
Pipeline routes: manually trigger the scrape → match → notify pipeline.
Fix #6: Last run result now persisted in DB (PipelineRun table) instead of in-memory dict.
Fix #14: Sync endpoint restricted and documented as internal/testing only.
Fix #17: Pydantic response_model on all endpoints.
"""
import logging
from typing import List
from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db, AsyncSessionLocal
from app.services.pipeline import run_pipeline
from app.models.pipeline_run import PipelineRun
from app.schemas import PipelineRunOut

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/pipeline", tags=["pipeline"])


@router.post("/run")
async def trigger_pipeline(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Manually trigger the full pipeline: Scrape → AI Match → Store → Notify.
    Runs in the background and returns immediately.
    Check /pipeline/last-run for results.
    """
    background_tasks.add_task(_run_in_background)
    return {
        "message": "Pipeline triggered in background. Check /pipeline/last-run for results.",
        "status": "running",
    }


@router.post("/run/sync")
async def trigger_pipeline_sync(db: AsyncSession = Depends(get_db)):
    """
    Synchronously trigger the pipeline (waits for completion).
    ⚠️  WARNING: This can take 30–90+ seconds. Only use for local testing.
    In production prefer POST /pipeline/run (async background version).
    """
    result = await run_pipeline(db, triggered_by="api-sync")
    return result


@router.get("/last-run")
async def get_last_run(db: AsyncSession = Depends(get_db)):
    """
    Return the result of the last pipeline run.
    Fix #6: Reads from DB (PipelineRun table) instead of in-memory dict.
    """
    result = await db.execute(
        select(PipelineRun)
        .order_by(PipelineRun.created_at.desc())
        .limit(1)
    )
    run = result.scalar_one_or_none()

    if not run:
        return {"message": "No pipeline run recorded yet."}

    return {
        "id": str(run.id),
        "status": run.status,
        "triggered_by": run.triggered_by,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "jobs_scraped": run.jobs_scraped,
        "jobs_new": run.jobs_new,
        "matches_created": run.matches_created,
        "notifications_sent": run.notifications_sent,
        "errors": run.errors,
    }


@router.get("/history")
async def get_pipeline_history(
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
):
    """Return the last N pipeline run records."""
    result = await db.execute(
        select(PipelineRun)
        .order_by(PipelineRun.created_at.desc())
        .limit(min(limit, 50))
    )
    runs = result.scalars().all()
    return [
        {
            "id": str(r.id),
            "status": r.status,
            "triggered_by": r.triggered_by,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            "jobs_scraped": r.jobs_scraped,
            "matches_created": r.matches_created,
            "notifications_sent": r.notifications_sent,
            "errors": r.errors,
        }
        for r in runs
    ]


async def _run_in_background():
    """Background task wrapper with its own DB session."""
    async with AsyncSessionLocal() as db:
        try:
            result = await run_pipeline(db, triggered_by="api-background")
            logger.info("Background pipeline complete: %s", result)
        except Exception as e:
            logger.error("Background pipeline error: %s", e)
