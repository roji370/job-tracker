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
    # Two-tier strategy for rows where experience_level IS NULL:
    #   Tier 1 → job title keyword regex (same patterns as Python scraper)
    #   Tier 2 → max years-of-experience found in description+requirements
    #   Default → 'mid'
    op.execute(
        sa.text("""
        UPDATE jobs
        SET experience_level = CASE
            -- Tier 1: title keywords (word-boundary regex)
            WHEN lower(title) ~* '\\mdirector\\m|\\mvp\\m|\\bvice president\\b|\\bhead of\\b|\\mprincipal\\m'
                THEN 'director'
            WHEN lower(title) ~* '\\mlead\\m|\\mstaff\\m|\\marchitect\\m|\\mdistinguished\\m'
                THEN 'lead'
            WHEN lower(title) ~* '\\msenior\\m|\\bsr\\b'
                THEN 'senior'
            WHEN lower(title) ~* '\\mjunior\\m|\\bjr\\b|\\mentry\\m|\\massociate\\m|\\mgraduate\\m|\\mintern\\m|\\bnew grad\\b'
                THEN 'entry'
            -- Tier 2: years-of-experience in description + requirements
            ELSE (
                SELECT CASE
                    WHEN max_yrs >= 12 THEN 'director'
                    WHEN max_yrs >= 8  THEN 'lead'
                    WHEN max_yrs >= 5  THEN 'senior'
                    WHEN max_yrs >= 2  THEN 'mid'
                    WHEN max_yrs >= 0  THEN 'entry'
                    ELSE 'mid'
                END
                FROM (
                    SELECT COALESCE(
                        (SELECT MAX(CAST(m[1] AS INT))
                         FROM regexp_matches(
                           COALESCE(jobs.description,'') || ' ' || COALESCE(jobs.requirements,''),
                           E'(?:at\\\\s+least\\\\s+|minimum\\\\s+|(?:\\\\d+\\\\s*[-\\u2013]\\\\s*)?)([0-9]+)\\\\s*\\\\+?\\\\s*years?',
                           'gi'
                         ) AS m
                        ), -1
                    ) AS max_yrs
                ) AS yrs
            )
        END
        WHERE experience_level IS NULL
        """)
    )



def downgrade() -> None:
    # Cannot reliably reverse a backfill — just NULL out everything that was mid
    # (the original state before any inference was added)
    pass
