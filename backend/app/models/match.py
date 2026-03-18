import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Float, Text, DateTime, ForeignKey, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.database import Base


class JobMatch(Base):
    __tablename__ = "job_matches"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    resume_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
    )
    match_score: Mapped[float] = mapped_column(Float, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=True)
    # Stores per-dimension breakdown: {role, skills, experience, location, tech_stack}
    # NULL for legacy rows (pre-migration) that haven't been re-matched yet.
    score_breakdown: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, default=None)
    is_notified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_saved: Mapped[bool] = mapped_column(Boolean, default=False)
    is_applied: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    resume: Mapped["Resume"] = relationship("Resume", back_populates="matches")
    job: Mapped["Job"] = relationship("Job", back_populates="matches")

    # Fix #9: indexes on the columns that appear in WHERE clauses constantly
    __table_args__ = (
        Index("ix_job_matches_resume_id", "resume_id"),
        Index("ix_job_matches_match_score", "match_score"),
        Index("ix_job_matches_is_notified", "is_notified"),
        Index("ix_job_matches_is_saved", "is_saved"),
        Index("ix_job_matches_is_applied", "is_applied"),
    )

    def __repr__(self) -> str:
        return f"<JobMatch score={self.match_score:.1f}%>"
