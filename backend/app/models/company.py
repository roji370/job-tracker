"""
Company DB model — Part 3 of the company-boost feature.

Table: companies
  id         SERIAL PRIMARY KEY
  name       TEXT UNIQUE NOT NULL           -- normalized canonical name
  tier       INT DEFAULT 3                  -- 1=static top, 2=seen in DB, 3=unknown
  last_seen  TIMESTAMP WITH TIME ZONE       -- updated on every pipeline run that sees this company
  created_at TIMESTAMP WITH TIME ZONE
"""
from datetime import datetime, timezone
from sqlalchemy import Integer, Text, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    # tier: 1 = static top company, 2 = seen in DB, 3 = unknown/default
    tier: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("ix_companies_name", "name"),
        Index("ix_companies_tier", "tier"),
    )

    def __repr__(self) -> str:
        return f"<Company {self.name!r} tier={self.tier}>"
