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

    IMPORTANT: alembic's env.py uses asyncio.run() internally, which raises
    RuntimeError if called from inside a running event loop (which FastAPI's
    lifespan always is). We therefore run the migration in a separate thread
    via run_in_executor so it gets its own clean event loop.
    """
    import logging
    import asyncio
    from concurrent.futures import ThreadPoolExecutor
    from alembic.config import Config
    from alembic import command

    logger = logging.getLogger(__name__)

    def _run_upgrade():
        """Runs in a dedicated thread — safe to call asyncio.run() here."""
        import pathlib
        alembic_cfg_path = pathlib.Path(__file__).parent.parent / "alembic.ini"
        alembic_cfg = Config(str(alembic_cfg_path))
        # Force the live DATABASE_URL — ignore whatever is in alembic.ini
        alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
        command.upgrade(alembic_cfg, "head")

    try:
        loop = asyncio.get_running_loop()
        with ThreadPoolExecutor(max_workers=1) as pool:
            await loop.run_in_executor(pool, _run_upgrade)
        logger.info("✅ Alembic migrations applied (upgrade head).")
    except Exception as e:
        # Fall back to create_all so dev environments without a DB still work
        logger.warning("⚠️  Alembic upgrade failed (%s) — falling back to create_all.", e)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
