import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.database import Base


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    company: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    requirements: Mapped[str] = mapped_column(Text, nullable=True)
    url: Mapped[str] = mapped_column(String(1000), nullable=True)
    source: Mapped[str] = mapped_column(String(100), default="amazon")
    job_id_external: Mapped[str] = mapped_column(String(255), nullable=True, unique=True)
    employment_type: Mapped[str] = mapped_column(String(100), nullable=True)
    posted_date: Mapped[str] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # Fix #8: flag jobs whose descriptions were AI-generated (scraper fallback)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    matches: Mapped[list["JobMatch"]] = relationship(
        "JobMatch", back_populates="job", cascade="all, delete-orphan"
    )

    # Fix #9: DB indexes on high-frequency filter columns
    __table_args__ = (
        Index("ix_jobs_is_active", "is_active"),
        Index("ix_jobs_job_id_external", "job_id_external"),
        Index("ix_jobs_source", "source"),
    )

    def __repr__(self) -> str:
        return f"<Job {self.title} @ {self.company}>"
