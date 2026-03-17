"""
API Key authentication dependency.

Usage:
  - Set API_KEY in your .env file (at least 32 random characters).
  - Clients must pass the header:  X-API-Key: <value>
  - If API_KEY is empty (default dev mode), authentication is SKIPPED and a
    warning is logged. This lets you bring up the stack locally without
    configuration, but production must always set a strong key.
"""
import logging
import secrets

from fastapi import Depends, HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(api_key: str | None = Security(API_KEY_HEADER)) -> None:
    """
    FastAPI dependency that enforces API-key authentication.

    Inject as:
        router = APIRouter(dependencies=[Depends(require_api_key)])
    or per-route:
        @router.get("/", dependencies=[Depends(require_api_key)])
    """
    configured_key = settings.API_KEY

    # Dev mode: no key configured → skip auth (with a loud warning)
    if not configured_key:
        logger.warning(
            "⚠️  API_KEY is not set — authentication is DISABLED. "
            "Set API_KEY in your .env for production."
        )
        return

    # Reject missing or wrong key (constant-time comparison to prevent timing attacks)
    if not api_key or not secrets.compare_digest(api_key, configured_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key. Pass 'X-API-Key' header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
