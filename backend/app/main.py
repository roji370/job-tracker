"""
FastAPI application entry point.
"""
import logging
import logging.config
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.config import get_settings
from app.database import init_db
from app.scheduler import start_scheduler, stop_scheduler
from app.routes import resumes, jobs, matches, notifications, pipeline
from app.middleware.auth import require_api_key
from fastapi import Depends

# ── Logging setup ─────────────────────────────────────────────────────────────
settings = get_settings()

LOG_LEVEL = logging.DEBUG if settings.ENVIRONMENT == "development" else logging.INFO

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            "datefmt": "%Y-%m-%dT%H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "stream": "ext://sys.stdout",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": LOG_LEVEL,
    },
    # Quiet noisy libraries in production
    "loggers": {
        "sqlalchemy.engine": {"level": "WARNING" if settings.ENVIRONMENT == "production" else "DEBUG"},
        "apscheduler": {"level": "INFO"},
        "playwright": {"level": "WARNING"},
    },
}
logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)

# ── Rate limiter (Fix #7) ─────────────────────────────────────────────────────
# Uses client IP by default. Override limit per-route on expensive endpoints.
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    logger.info("🚀 Starting Job Tracker API  [env=%s]", settings.ENVIRONMENT)

    # Create DB tables (dev) / apply migrations (idempotent in prod via Alembic)
    await init_db()
    logger.info("✅ Database initialized.")

    # Ensure uploads dir exists
    Path("/app/uploads").mkdir(parents=True, exist_ok=True)

    # Start background scheduler
    start_scheduler()

    yield

    stop_scheduler()
    logger.info("👋 Job Tracker API shut down.")


app = FastAPI(
    title="Job Tracker API",
    description=(
        "AI-powered job tracking system: scrapes Amazon Jobs, matches with your resume "
        "using sentence-transformers, and sends WhatsApp + Email notifications.\n\n"
        "**Authentication:** All endpoints (except `/api/health`) require the "
        "`X-API-Key` header when `API_KEY` is configured."
    ),
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# ── Rate limiter middleware ───────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS ──────────────────────────────────────────────────────────────────────
origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers (Fix #1: all routes require API key authentication) ───────────────
auth_dep = [Depends(require_api_key)]

app.include_router(resumes.router, prefix="/api", dependencies=auth_dep)
app.include_router(jobs.router, prefix="/api", dependencies=auth_dep)
app.include_router(matches.router, prefix="/api", dependencies=auth_dep)
app.include_router(notifications.router, prefix="/api", dependencies=auth_dep)
app.include_router(pipeline.router, prefix="/api", dependencies=auth_dep)


# ── Public endpoints (no auth required) ──────────────────────────────────────
@app.get("/api/health", tags=["health"])
async def health():
    """Health check endpoint — publicly accessible, no auth required."""
    return {"status": "ok", "version": "1.0.0", "environment": settings.ENVIRONMENT}
