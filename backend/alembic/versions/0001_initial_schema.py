"""Initial schema

Revision ID: 0001
Revises:
Create Date: 2026-03-17

Creates all tables for the job tracker application.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── resumes ──────────────────────────────────────────────────────────────
    op.create_table(
        "resumes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("extracted_text", sa.Text, nullable=True),
        sa.Column("skills", postgresql.JSONB, nullable=True),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_resumes_is_active", "resumes", ["is_active"])

    # ── jobs ─────────────────────────────────────────────────────────────────
    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("company", sa.String(255), nullable=False),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("requirements", sa.Text, nullable=True),
        sa.Column("url", sa.String(1000), nullable=True),
        sa.Column("source", sa.String(100), default="amazon"),
        sa.Column("job_id_external", sa.String(255), nullable=True, unique=True),
        sa.Column("employment_type", sa.String(100), nullable=True),
        sa.Column("posted_date", sa.String(100), nullable=True),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("is_synthetic", sa.Boolean, default=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_jobs_is_active", "jobs", ["is_active"])
    op.create_index("ix_jobs_job_id_external", "jobs", ["job_id_external"])
    op.create_index("ix_jobs_source", "jobs", ["source"])

    # ── job_matches ──────────────────────────────────────────────────────────
    op.create_table(
        "job_matches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "resume_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("resumes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("match_score", sa.Float, nullable=False),
        sa.Column("explanation", sa.Text, nullable=True),
        sa.Column("is_notified", sa.Boolean, default=False),
        sa.Column("is_saved", sa.Boolean, default=False),
        sa.Column("is_applied", sa.Boolean, default=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_job_matches_resume_id", "job_matches", ["resume_id"])
    op.create_index("ix_job_matches_match_score", "job_matches", ["match_score"])
    op.create_index("ix_job_matches_is_notified", "job_matches", ["is_notified"])
    op.create_index("ix_job_matches_is_saved", "job_matches", ["is_saved"])
    op.create_index("ix_job_matches_is_applied", "job_matches", ["is_applied"])

    # ── notification_logs ────────────────────────────────────────────────────
    op.create_table(
        "notification_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("channel", sa.String(50), nullable=False),
        sa.Column("recipient", sa.String(255), nullable=False),
        sa.Column("subject", sa.String(500), nullable=True),
        sa.Column("body", sa.Text, nullable=True),
        sa.Column("status", sa.String(50), default="pending"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_notification_logs_status", "notification_logs", ["status"])
    op.create_index("ix_notification_logs_channel", "notification_logs", ["channel"])

    # ── pipeline_runs ────────────────────────────────────────────────────────
    op.create_table(
        "pipeline_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(50), default="running"),
        sa.Column("jobs_scraped", sa.Integer, default=0),
        sa.Column("jobs_new", sa.Integer, default=0),
        sa.Column("matches_created", sa.Integer, default=0),
        sa.Column("notifications_sent", sa.Integer, default=0),
        sa.Column("errors", postgresql.JSONB, nullable=True),
        sa.Column("triggered_by", sa.String(50), default="scheduler"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_pipeline_runs_status", "pipeline_runs", ["status"])
    op.create_index("ix_pipeline_runs_created_at", "pipeline_runs", ["created_at"])


def downgrade() -> None:
    op.drop_table("pipeline_runs")
    op.drop_table("notification_logs")
    op.drop_table("job_matches")
    op.drop_table("jobs")
    op.drop_table("resumes")
