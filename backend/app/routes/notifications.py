"""
Notification routes: view logs, trigger manually.
Fix #17: Pydantic response_model on all endpoints.
Fix #18: Use settings.MATCH_THRESHOLD instead of hardcoded 70.0.
"""
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import get_settings
from app.database import get_db
from app.models.notification import NotificationLog
from app.models.match import JobMatch
from app.models.resume import Resume
from app.schemas import NotificationLogOut
from app.utils.notifier import (
    send_whatsapp,
    send_email,
    build_job_notification_message,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/notifications", tags=["notifications"])
settings = get_settings()


@router.get("/logs", response_model=List[NotificationLogOut])
async def get_notification_logs(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """Get recent notification history."""
    result = await db.execute(
        select(NotificationLog)
        .order_by(NotificationLog.created_at.desc())
        .limit(limit)
    )
    logs = result.scalars().all()
    return [
        {
            "id": str(log.id),
            "channel": log.channel,
            "recipient": log.recipient,
            "subject": log.subject,
            "status": log.status,
            "error_message": log.error_message,
            "created_at": log.created_at.isoformat(),
        }
        for log in logs
    ]


@router.post("/trigger")
async def trigger_notifications_manually(db: AsyncSession = Depends(get_db)):
    """
    Manually trigger notifications for all high-score matches
    that haven't been notified yet.
    Uses MATCH_THRESHOLD from settings (Fix #18).
    """
    from sqlalchemy.orm import selectinload

    # Get active resume
    resume_result = await db.execute(
        select(Resume).where(Resume.is_active == True).order_by(Resume.created_at.desc())
    )
    resume = resume_result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=400, detail="No active resume found")

    # Fix #18: Use settings.MATCH_THRESHOLD (was hardcoded 70.0)
    threshold = settings.MATCH_THRESHOLD

    # Get unnotified high-score matches
    result = await db.execute(
        select(JobMatch)
        .options(selectinload(JobMatch.job))
        .where(
            JobMatch.resume_id == resume.id,
            JobMatch.match_score >= threshold,
            JobMatch.is_notified == False,
        )
        .order_by(JobMatch.match_score.desc())
        .limit(10)
    )
    matches = result.scalars().all()

    if not matches:
        return {
            "message": f"No unnotified matches above {threshold}% found",
            "sent": 0,
        }

    payload = [
        {
            "title": m.job.title if m.job else "Unknown",
            "company": m.job.company if m.job else "Unknown",
            "location": m.job.location if m.job else "",
            "url": m.job.url if m.job else "",
            "match_score": m.match_score,
        }
        for m in matches
    ]

    wa_text, email_html = build_job_notification_message(payload)

    # WhatsApp
    wa_result = send_whatsapp(wa_text)
    log_wa = NotificationLog(
        channel="whatsapp",
        body=wa_text,
        recipient=settings.WHATSAPP_TO,
        status=wa_result.get("status", "error"),
        error_message=wa_result.get("reason"),
    )
    db.add(log_wa)

    # Email
    subject = f"🎯 {len(matches)} Job Matches Found!"
    email_result = send_email(subject=subject, body_html=email_html)
    log_email = NotificationLog(
        channel="email",
        subject=subject,
        body=email_html,
        recipient=settings.EMAIL_TO or settings.EMAIL_USER,
        status=email_result.get("status", "error"),
        error_message=email_result.get("reason"),
    )
    db.add(log_email)

    # Mark as notified
    for m in matches:
        m.is_notified = True

    await db.commit()

    return {
        "message": "Notifications triggered",
        "matches_notified": len(matches),
        "threshold_used": threshold,
        "whatsapp": wa_result,
        "email": email_result,
    }
