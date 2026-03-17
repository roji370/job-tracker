"""
Application settings, loaded from environment variables via pydantic-settings.
All values have safe defaults for local development, but production deployments
MUST override the variables annotated with [REQUIRED IN PRODUCTION].
"""
import logging
from typing import Literal
from functools import lru_cache

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://jobtracker:jobtracker@localhost:5432/jobtracker"

    # ── API Authentication [REQUIRED IN PRODUCTION] ──────────────────────────
    # Set to any random 32-64 character string.
    # Clients must send:  X-API-Key: <value>
    # Leave empty to disable auth in local dev (loud warning will be logged).
    API_KEY: str = ""

    # ── Twilio / WhatsApp ─────────────────────────────────────────────────────
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    WHATSAPP_FROM: str = "whatsapp:+14155238886"
    WHATSAPP_TO: str = "whatsapp:+1234567890"

    # ── Email (SMTP) ──────────────────────────────────────────────────────────
    EMAIL_HOST: str = "smtp.gmail.com"
    EMAIL_PORT: int = 587
    EMAIL_USER: str = ""
    EMAIL_PASS: str = ""
    EMAIL_TO: str = ""

    # ── App ───────────────────────────────────────────────────────────────────
    # Fix #3 + #28: Literal type + production validator below
    SECRET_KEY: str = "changeme-super-secret-key"  # [REQUIRED IN PRODUCTION]
    ENVIRONMENT: Literal["development", "production"] = "development"
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # ── Scheduler ─────────────────────────────────────────────────────────────
    SCHEDULER_INTERVAL_HOURS: int = 6

    # ── Matching ──────────────────────────────────────────────────────────────
    MATCH_THRESHOLD: float = 70.0

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    # Fix #3: Reject dangerous defaults in production
    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if self.ENVIRONMENT == "production":
            errors = []

            if self.SECRET_KEY in ("changeme-super-secret-key", "", "replace_with_64_char_random_string"):
                errors.append(
                    "SECRET_KEY must be set to a unique random string in production. "
                    "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
                )

            if not self.API_KEY:
                errors.append(
                    "API_KEY must be set in production. All API clients need this key. "
                    "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
                )

            # Fix #12: Reject localhost origins in production
            origins = [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]
            localhost_origins = [o for o in origins if "localhost" in o or "127.0.0.1" in o]
            if localhost_origins:
                errors.append(
                    f"ALLOWED_ORIGINS contains localhost entries in production: {localhost_origins}. "
                    "Set ALLOWED_ORIGINS to your actual domain(s)."
                )

            if errors:
                raise ValueError(
                    "Unsafe configuration detected for ENVIRONMENT=production:\n"
                    + "\n".join(f"  • {e}" for e in errors)
                )

        return self


@lru_cache()
def get_settings() -> Settings:
    return Settings()
