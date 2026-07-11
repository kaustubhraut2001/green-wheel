"""
Application configuration using Pydantic Settings.
All secrets must be set via environment variables — never hardcoded.
"""
from functools import lru_cache
from typing import List, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── App ──────────────────────────────────────────────────
    APP_NAME: str = "Multi-Currency Wallet Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"

    # ── Database ─────────────────────────────────────────────
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_POOL_TIMEOUT: int = 30

    # ── Redis ────────────────────────────────────────────────
    REDIS_URL: str = "redis://redis:6379/0"
    REDIS_CACHE_TTL: int = 300          # 5 minutes default
    EXCHANGE_RATE_CACHE_TTL: int = 3600  # 1 hour

    # ── Celery ───────────────────────────────────────────────
    CELERY_BROKER_URL: str = "redis://redis:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/2"

    # ── JWT ──────────────────────────────────────────────────
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── CORS ─────────────────────────────────────────────────
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # ── Rate Limiting ─────────────────────────────────────────
    RATE_LIMIT_LOGIN: str = "5/minute"
    RATE_LIMIT_SIGNUP: str = "3/minute"
    RATE_LIMIT_DEFAULT: str = "60/minute"

    # ── Exchange Rate Provider ────────────────────────────────
    EXCHANGE_RATE_PROVIDER: str = "open_exchange"  # fixer | currency_layer | open_exchange
    OPEN_EXCHANGE_APP_ID: Optional[str] = None
    FIXER_API_KEY: Optional[str] = None
    CURRENCY_LAYER_API_KEY: Optional[str] = None

    # ── Circuit Breaker ───────────────────────────────────────
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 5
    CIRCUIT_BREAKER_RECOVERY_TIMEOUT: int = 60  # seconds

    # ── File Storage ──────────────────────────────────────────
    UPLOAD_DIR: str = "/tmp/uploads"
    MAX_UPLOAD_SIZE_MB: int = 5

    # ── Pagination ────────────────────────────────────────────
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        allowed = {"development", "staging", "production", "test"}
        if v not in allowed:
            raise ValueError(f"ENVIRONMENT must be one of {allowed}")
        return v


@lru_cache()
def get_settings() -> Settings:
    """
    Singleton settings instance.
    lru_cache ensures we only parse environment once — avoids repeated I/O.
    """
    return Settings()


settings = get_settings()
