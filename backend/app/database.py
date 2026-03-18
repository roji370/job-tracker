from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.ENVIRONMENT == "development",
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """
    Apply all pending Alembic migrations, then ensure any remaining tables exist.

    Running `alembic upgrade head` programmatically at startup means every
    Render deploy automatically migrates the database — no manual steps needed.
    Falls back to create_all so local dev without an alembic_version table also works.
    """
    import logging
    from alembic.config import Config
    from alembic import command

    logger = logging.getLogger(__name__)

    try:
        # Resolve the alembic.ini path relative to this file
        import pathlib
        alembic_cfg_path = pathlib.Path(__file__).parent.parent / "alembic.ini"
        alembic_cfg = Config(str(alembic_cfg_path))
        # Always use the live DATABASE_URL — not whatever is in alembic.ini
        alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
        command.upgrade(alembic_cfg, "head")
        logger.info("✅ Alembic migrations applied (upgrade head).")
    except Exception as e:
        # Fall back to create_all so dev environments without migrations still work
        logger.warning("⚠️  Alembic upgrade failed (%s) — falling back to create_all.", e)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
