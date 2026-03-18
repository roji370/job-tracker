"""Add score_breakdown JSONB column to job_matches table

Revision ID: 0003
Revises: 0002
Create Date: 2026-03-18

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "job_matches",
        sa.Column(
            "score_breakdown",
            JSONB,
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("job_matches", "score_breakdown")
