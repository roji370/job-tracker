"""
Company database ops and boost logic.
Part 4 & 5 of the company-boost feature.
"""
import logging
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import select

from app.models.company import Company
from app.utils.company_normalizer import normalize_company, is_top_company

logger = logging.getLogger(__name__)


async def updateCompanyDatabase(db: AsyncSession, jobs: list[dict[str, Any]]) -> None:
    """
    Extract company names from a batch of jobs, normalize them,
    and UPSERT into the companies table.

    Uses PostgreSQL ON CONFLICT DO UPDATE to set last_seen = NOW().
    """
    if not jobs:
        return

    # Extract unique normalized company names from the batch
    companies_batch = {normalize_company(j.get("company")) for j in jobs if j.get("company")}
    
    if not companies_batch:
        return

    # Prepare values for upsert
    values = [{"name": c, "tier": 1 if is_top_company(c) else 2} for c in companies_batch]

    stmt = insert(Company).values(values)
    
    # On conflict, update last_seen and explicitly set the tier to the new computed tier
    # (in case a company wasn't in top companies but is added later, or vice-versa).
    stmt = stmt.on_conflict_do_update(
        index_elements=["name"],
        set_={
            "tier": stmt.excluded.tier,
            "last_seen": stmt.excluded.last_seen,
        }
    )

    try:
        await db.execute(stmt)
        await db.commit()
        logger.info("Updated company DB with %d companies", len(companies_batch))
    except Exception as e:
        logger.error("Failed to update companies DB: %s", e)
        await db.rollback()


async def get_db_tier(db: AsyncSession, company_name: str) -> int:
    """
    Fetch the tier of a company from the DB.
    Returns 3 (default unknown) if it doesn't exist.
    """
    name = normalize_company(company_name)
    result = await db.execute(select(Company.tier).where(Company.name == name))
    row = result.scalar_one_or_none()
    return row if row is not None else 3


def applyCompanyBoost(score: float, is_top: bool, db_tier: int) -> float:
    """
    Apply company boost logic.
    - If in static dataset (is_top=True) -> +10
    - Else if exists in DB (tier <= 2) -> +5
    - Cap at 100
    """
    boost = 0
    if is_top:
        boost = 10
    elif db_tier <= 2:
        boost = 5

    return min(100.0, score + boost)
