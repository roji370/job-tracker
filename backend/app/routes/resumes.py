"""
Resume routes: upload, list, activate, delete.
Fix #10: async file I/O using aiofiles.
Fix #11: parse_resume offloaded to thread pool via run_in_executor.
Fix #17: Pydantic response_model on all endpoints.
Fix #29: Resume file always cleaned up on any error (including DB commit failures).
"""
import asyncio
import json
import uuid
import logging
from pathlib import Path
from typing import List

import aiofiles
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.resume import Resume
from app.utils.resume_parser import parse_resume
from app.schemas import ResumeOut, ResumeDetailOut, ResumeUploadOut, ResumeActivateOut

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/resumes", tags=["resumes"])
limiter = Limiter(key_func=get_remote_address)

UPLOAD_DIR = Path("/app/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


@router.post("/upload", status_code=status.HTTP_201_CREATED, response_model=ResumeUploadOut)
@limiter.limit("10/minute")  # Fix #7: tighter limit for expensive upload endpoint
async def upload_resume(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload and parse a resume file (PDF, DOCX, TXT)."""
    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{suffix}'. Allowed: {sorted(ALLOWED_EXTENSIONS)}",
        )

    file_id = uuid.uuid4()
    saved_name = f"{file_id}{suffix}"
    file_path = UPLOAD_DIR / saved_name

    # Fix #29: Track whether the file was written so cleanup is always correct
    file_written = False

    try:
        # Read into memory first (lets us check size before writing)
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail="File too large (max 10 MB)")

        # Fix #10: Use aiofiles for non-blocking disk write
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)
        file_written = True

        # Fix #11: Offload synchronous parse_resume() to thread pool
        loop = asyncio.get_event_loop()
        parsed = await loop.run_in_executor(None, parse_resume, str(file_path))

        # Mark all others inactive
        await db.execute(Resume.__table__.update().values(is_active=False))

        resume = Resume(
            id=file_id,
            filename=saved_name,
            original_filename=file.filename,
            extracted_text=parsed["text"],
            # Fix #16: skills is now a JSONB list — no json.dumps needed
            skills=parsed["skills"],
            is_active=True,
        )
        db.add(resume)
        await db.commit()
        await db.refresh(resume)

        return {
            "id": str(resume.id),
            "original_filename": resume.original_filename,
            "skills": resume.skills,
            "text_preview": (parsed["text"] or "")[:400],
            "created_at": resume.created_at.isoformat(),
        }

    except HTTPException:
        # Fix #29: Clean up on all errors, including DB commit failures
        if file_written and file_path.exists():
            file_path.unlink(missing_ok=True)
        raise
    except Exception as e:
        logger.error("Resume upload failed: %s", e)
        if file_written and file_path.exists():
            file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Failed to process resume: {str(e)}")


@router.get("/", response_model=List[ResumeOut])
async def list_resumes(db: AsyncSession = Depends(get_db)):
    """List all uploaded resumes."""
    result = await db.execute(select(Resume).order_by(Resume.created_at.desc()))
    resumes = result.scalars().all()
    return resumes


@router.get("/{resume_id}", response_model=ResumeDetailOut)
async def get_resume(resume_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Get a single resume by ID."""
    result = await db.execute(select(Resume).where(Resume.id == resume_id))
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    return resume


@router.patch("/{resume_id}/activate", response_model=ResumeActivateOut)
async def activate_resume(resume_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Set a resume as the active one for matching."""
    result = await db.execute(select(Resume).where(Resume.id == resume_id))
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    await db.execute(Resume.__table__.update().values(is_active=False))
    resume.is_active = True
    await db.commit()
    return ResumeActivateOut(message="Resume activated", id=resume.id)


@router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resume(resume_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Delete a resume and its file."""
    result = await db.execute(select(Resume).where(Resume.id == resume_id))
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    file_path = UPLOAD_DIR / resume.filename
    await db.delete(resume)
    await db.commit()

    # Delete file after DB commit succeeds
    if file_path.exists():
        file_path.unlink(missing_ok=True)
