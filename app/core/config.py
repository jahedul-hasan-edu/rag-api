"""
Application configuration loaded from environment variables.

Uses pydantic-settings BaseSettings so secrets are never hardcoded.
A single cached Settings instance is shared via get_settings().
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the RAG API."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    environment: Literal["development", "staging", "production"] = Field(
        default="development",
        alias="ENVIRONMENT",
        description="Deployment environment name.",
    )
    log_level: str = Field(
        default="INFO",
        alias="LOG_LEVEL",
        description="Structlog / stdlib log level.",
    )
    app_version: str = Field(
        default="0.1.0",
        alias="APP_VERSION",
        description="Semantic application version exposed by /health.",
    )
    database_url: SecretStr = Field(
        ...,
        alias="DATABASE_URL",
        description="Async SQLAlchemy database URL (postgresql+asyncpg://...).",
    )
    openai_api_key: SecretStr = Field(
        ...,
        alias="OPENAI_API_KEY",
        description="OpenAI API key (used in later phases).",
    )

    @property
    def is_production(self) -> bool:
        """Return True when running in production."""
        return self.environment == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a process-wide cached Settings instance."""
    return Settings()
