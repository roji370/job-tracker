"""
Pipeline service: orchestrates scrape → match → store → notify.
Called by APScheduler and API routes.
Fix #6: Persists run state to PipelineRun DB table.
Fix #8: Sets is_synthetic=True on jobs with AI-generated descriptions.
"""
import logging
import asyncio
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.job import Job
from app.models.match import JobMatch
from app.models.resume import Resume
from app.models.notification import NotificationLog
from app.models.pipeline_run import PipelineRun
from app.utils.scraper import scrape_amazon_jobs
from app.utils.matcher import match_job
from app.utils.resume_parser import build_cv_data, extract_skills
from app.utils.notifier import send_whatsapp, send_email, build_job_notification_message
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def run_pipeline(
    db: AsyncSession,
    triggered_by: str = "scheduler",
    company_slugs: list[str] | None = None,
) -> dict:
    """
    Full pipeline:
    1. Scrape jobs from configured companies (or a subset if company_slugs provided)
    2. Load active resume
    3. Run AI matching
    4. Store new jobs + matches in DB
    5. Send notifications for high-scoring new matches

    Args:
        company_slugs: If provided, only scrape these company slugs.
                       Pass None to scrape all companies.

    Returns a summary dict and persists a PipelineRun record.
    """
    now = datetime.now(timezone.utc)

    # Fix #6: Create a PipelineRun record immediately so status=running is visible
    run = PipelineRun(
        started_at=now,
        status="running",
        triggered_by=triggered_by,
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    errors: list[str] = []

    # Step 1: Scrape jobs
    raw_jobs = []
    try:
        raw_jobs = await scrape_amazon_jobs(company_slugs=company_slugs)
        run.jobs_scraped = len(raw_jobs)
        logger.info("Scraped %d jobs", len(raw_jobs))
    except Exception as e:
        logger.error("Scraping failed: %s", e)
        errors.append(f"Scraping: {e}")

    # Step 2: Load active resume
    resume = await _get_active_resume(db)
    if not resume:
        logger.warning("No active resume — skipping matching step.")
        errors.append("No active resume found")
        run.status = "completed"
        run.finished_at = datetime.now(timezone.utc)
        run.errors = errors
        await db.commit()
        return _run_summary(run)

    # Build structured CV data once — used for all job comparisons this run
    cv_data = build_cv_data(resume)
    logger.info(
        "CV data: roles=%s skills=%d exp_years=%s location=%s",
        cv_data["roles"],
        len(cv_data["skills"]),
        cv_data["experience_years"],
        cv_data["location"],
    )

    # Step 3+4: Match and store
    new_matches: list[dict] = []
    jobs_new = 0

    for job_data in raw_jobs:
        try:
            job, is_new = await _upsert_job(db, job_data)
            if is_new:
                jobs_new += 1

            # Skip if already matched against this resume
            existing = await db.execute(
                select(JobMatch).where(
                    JobMatch.resume_id == resume.id,
                    JobMatch.job_id == job.id,
                )
            )
            if existing.scalar_one_or_none():
                continue

            # Build a clean dict for the weighted matcher (avoid shadowing the
            # for-loop variable job_data which holds the raw scraper payload).
            # Extract skills_required from the requirements text so
            # calculate_skills_score() has an explicit list to compare against.
            requirements_text = job.requirements or ""
            description_text  = job.description  or ""
            skills_required   = extract_skills(requirements_text + " " + description_text)

            match_input = {
                "title":            job.title,
                "skills_required":  skills_required,
                "experience_level": job.experience_level,
                "location":         job.location,
                "description":      description_text,
            }

            # Run weighted matching in a thread pool (CPU-bound but very fast)
            loop   = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None, match_job, cv_data, match_input
            )

            score           = result["final_score"]
            breakdown       = result["breakdown"]
            explanation_list = result["explanation"]
            # Store explanation as a newline-joined string for Text column compat
            explanation_str = "\n".join(explanation_list)

            match = JobMatch(
                resume_id=resume.id,
                job_id=job.id,
                match_score=score,
                explanation=explanation_str,
                score_breakdown=breakdown,
            )
            db.add(match)
            run.matches_created += 1

            if score >= settings.MATCH_THRESHOLD:
                new_matches.append({
                    "title":       job.title,
                    "company":     job.company,
                    "location":    job.location,
                    "url":         job.url,
                    "match_score": score,
                    "explanation": explanation_str,
                })

        except Exception as e:
            logger.error("Error processing job '%s': %s", job_data.get("title"), e)
            errors.append(str(e))

    run.jobs_new = jobs_new
    await db.commit()

    # Step 5: Notify
    if new_matches:
        sent = await _send_notifications(db, new_matches)
        run.notifications_sent = sent

    # Finalize run record
    run.status = "completed" if not errors else "completed_with_errors"
    run.finished_at = datetime.now(timezone.utc)
    run.errors = errors
    await db.commit()

    summary = _run_summary(run)
    logger.info("Pipeline finished: %s", summary)
    return summary


def _run_summary(run: PipelineRun) -> dict:
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


async def _get_active_resume(db: AsyncSession) -> Resume | None:
    result = await db.execute(
        select(Resume).where(Resume.is_active == True).order_by(Resume.created_at.desc())
    )
    return result.scalar_one_or_none()


async def _upsert_job(db: AsyncSession, job_data: dict) -> tuple[Job, bool]:
    """Insert or return existing job by external ID. Returns (job, is_new)."""
    if job_data.get("job_id_external"):
        result = await db.execute(
            select(Job).where(Job.job_id_external == job_data["job_id_external"])
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing, False

    # Fix #8: Mark job as synthetic if description was AI-generated
    job = Job(
        title=job_data.get("title", ""),
        company=job_data.get("company", "Amazon"),
        location=job_data.get("location"),
        description=job_data.get("description"),
        requirements=job_data.get("requirements"),
        url=job_data.get("url"),
        source=job_data.get("source", "amazon"),
        job_id_external=job_data.get("job_id_external"),
        employment_type=job_data.get("employment_type"),
        posted_date=job_data.get("posted_date"),
        experience_level=job_data.get("experience_level"),
        is_synthetic=job_data.get("is_synthetic", False),
    )
    db.add(job)
    await db.flush()  # Get the ID
    return job, True


async def _send_notifications(db: AsyncSession, matches: list[dict]) -> int:
    """Send WhatsApp + Email notifications and log them."""
    sent = 0
    try:
        wa_text, email_html = build_job_notification_message(matches)

        wa_result = send_whatsapp(wa_text)
        log_wa = NotificationLog(
            channel="whatsapp",
            recipient=settings.WHATSAPP_TO,
            body=wa_text,
            status=wa_result.get("status", "error"),
            error_message=wa_result.get("reason"),
        )
        db.add(log_wa)
        if wa_result.get("status") == "sent":
            sent += 1

        subject = f"🎯 {len(matches)} New Job Matches Found!"
        email_result = send_email(subject=subject, body_html=email_html)
        log_email = NotificationLog(
            channel="email",
            recipient=settings.EMAIL_TO or settings.EMAIL_USER,
            subject=subject,
            body=email_html,
            status=email_result.get("status", "error"),
            error_message=email_result.get("reason"),
        )
        db.add(log_email)
        if email_result.get("status") == "sent":
            sent += 1

        await db.commit()
    except Exception as e:
        logger.error("Notification error: %s", e)

    return sent
