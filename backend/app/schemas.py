"""
Pydantic request/response schemas for the Job Tracker API.
Using these ensures:
  - Consistent, documented API contracts in Swagger UI
  - Output field filtering (no accidental data leakage)
  - Type validation on input
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, ConfigDict, field_validator


# ── Shared config ─────────────────────────────────────────────────────────────
class _OrmBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────────────────────────────────────────────
# Job schemas
# ─────────────────────────────────────────────────────────────────────────────

class JobOut(_OrmBase):
    id: uuid.UUID
    title: str
    company: str
    location: Optional[str] = None
    description: Optional[str] = None
    requirements: Optional[str] = None
    url: Optional[str] = None
    source: str
    employment_type: Optional[str] = None
    posted_date: Optional[str] = None
    experience_level: Optional[str] = None
    is_active: bool
    # Fix #8: surfaced so the UI can display a "synthetic" badge
    is_synthetic: bool = False
    is_top_company: bool = False
    created_at: datetime


class JobDeactivateOut(_OrmBase):
    message: str
    id: uuid.UUID


# ─────────────────────────────────────────────────────────────────────────────
# Resume schemas
# ─────────────────────────────────────────────────────────────────────────────

class ResumeOut(_OrmBase):
    id: uuid.UUID
    original_filename: str
    skills: list[str] = []
    is_active: bool
    created_at: datetime


class ResumeDetailOut(ResumeOut):
    extracted_text: Optional[str] = None


class ResumeUploadOut(_OrmBase):
    id: uuid.UUID
    original_filename: str
    skills: list[str] = []
    text_preview: str
    created_at: datetime


class ResumeActivateOut(_OrmBase):
    message: str
    id: uuid.UUID


# ─────────────────────────────────────────────────────────────────────────────
# Match schemas
# ─────────────────────────────────────────────────────────────────────────────

class JobInMatchOut(BaseModel):
    """Embedded job summary inside a match response."""
    id: Optional[uuid.UUID] = None
    title: str = ""
    company: str = ""
    location: str = ""
    description: str = ""
    requirements: str = ""
    url: str = ""
    source: str = ""
    employment_type: str = ""
    posted_date: str = ""
    experience_level: Optional[str] = None
    is_synthetic: bool = False
    is_top_company: bool = False


class MatchOut(_OrmBase):
    id: uuid.UUID
    match_score: float
    explanation: Optional[Any] = None   # str (legacy) or list[str] (new matcher)
    score_breakdown: Optional[dict] = None
    is_saved: bool
    is_applied: bool
    is_notified: bool
    created_at: datetime
    job: Optional[JobInMatchOut] = None

    @field_validator("explanation", mode="before")
    @classmethod
    def _coerce_explanation(cls, v: Any) -> Any:
        """Accept both the legacy single-string and the new list-of-strings format."""
        return v  # pass through as-is; frontend handles both


class MatchToggleOut(_OrmBase):
    id: uuid.UUID
    is_saved: Optional[bool] = None
    is_applied: Optional[bool] = None


class MatchStatsOut(BaseModel):
    total_matches: int
    high_score_matches: int
    saved_jobs: int
    applied_jobs: int


# ─────────────────────────────────────────────────────────────────────────────
# Notification schemas
# ─────────────────────────────────────────────────────────────────────────────

class NotificationLogOut(_OrmBase):
    id: uuid.UUID
    channel: str
    recipient: str
    subject: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    created_at: datetime


# ─────────────────────────────────────────────────────────────────────────────
# Company schemas
# ─────────────────────────────────────────────────────────────────────────────

class CompanyOut(BaseModel):
    name: str
    ats: str
    slug: str


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline schemas
# ─────────────────────────────────────────────────────────────────────────────

class PipelineRunRequest(BaseModel):
    """Optional request body for pipeline trigger endpoints."""
    companies: Optional[list[str]] = Field(
        default=None,
        description=(
            "List of company slugs to scrape (e.g. ['stripe', 'github']). "
            "Omit or pass null to scrape all configured companies."
        ),
    )


class PipelineRunOut(BaseModel):
    id: Optional[uuid.UUID] = None
    status: str
    triggered_by: str = "scheduler"
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    jobs_scraped: int = 0
    jobs_new: int = 0
    matches_created: int = 0
    notifications_sent: int = 0
    errors: list[str] = []
