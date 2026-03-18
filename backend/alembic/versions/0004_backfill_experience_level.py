"""Backfill experience_level for existing jobs that have NULL

Revision ID: 0004
Revises: 0003
Create Date: 2026-03-18

Uses SQL CASE/ILIKE expressions that mirror the Python _infer_experience_level()
logic so existing rows get a value that the filter endpoint can use immediately
without needing the pipeline to re-run.

Priority order (first match wins):
  director  → director, vp, vice president, head of, principal
  lead      → lead, staff, architect, distinguished
  senior    → senior, sr., sr
  entry     → junior, jr., entry, associate, graduate, intern, new grad
  mid       → everything else (default)
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Only backfill rows where experience_level is currently NULL
    op.execute(
        sa.text("""
        UPDATE jobs
        SET experience_level = CASE
            WHEN lower(title) ~* '\\mdirector\\m|\\mvp\\m|\\bvice president\\b|\\bhead of\\b|\\mprincipal\\m'
                THEN 'director'
            WHEN lower(title) ~* '\\mlead\\m|\\mstaff\\m|\\marchitect\\m|\\mdistinguished\\m'
                THEN 'lead'
            WHEN lower(title) ~* '\\msenior\\m|\\bsr\\b'
                THEN 'senior'
            WHEN lower(title) ~* '\\mjunior\\m|\\bjr\\b|\\mentry\\m|\\massociate\\m|\\mgraduate\\m|\\mintern\\m|\\bnew grad\\b'
                THEN 'entry'
            ELSE 'mid'
        END
        WHERE experience_level IS NULL
        """)
    )


def downgrade() -> None:
    # Cannot reliably reverse a backfill — just NULL out everything that was mid
    # (the original state before any inference was added)
    pass
