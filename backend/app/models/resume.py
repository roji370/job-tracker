import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.database import Base


class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    extracted_text: Mapped[str] = mapped_column(Text, nullable=True)
    # Fix #16: use native PostgreSQL JSONB instead of JSON-in-Text
    skills: Mapped[list] = mapped_column(JSONB, nullable=True, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    matches: Mapped[list["JobMatch"]] = relationship(
        "JobMatch", back_populates="resume", cascade="all, delete-orphan"
    )

    # Fix #9: index on is_active (queried on every pipeline run)
    __table_args__ = (
        Index("ix_resumes_is_active", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<Resume {self.original_filename}>"
