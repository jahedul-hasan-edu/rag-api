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

    # --- Upload / ingestion (Phase 2) ---
    max_upload_size_bytes: int = Field(
        default=10 * 1024 * 1024,
        alias="MAX_UPLOAD_SIZE_BYTES",
        description="Maximum allowed upload size in bytes (default 10 MiB).",
        gt=0,
    )
    chunk_size_tokens: int = Field(
        default=500,
        alias="CHUNK_SIZE_TOKENS",
        description="Target chunk size in tokens.",
        gt=0,
    )
    chunk_overlap_tokens: int = Field(
        default=100,
        alias="CHUNK_OVERLAP_TOKENS",
        description="Token overlap between consecutive chunks.",
        ge=0,
    )
    embedding_model_name: str = Field(
        default="BAAI/bge-small-en-v1.5",
        alias="EMBEDDING_MODEL_NAME",
        description="Local sentence-transformers model id.",
    )
    embedding_dimension: int = Field(
        default=384,
        alias="EMBEDDING_DIMENSION",
        description="Embedding vector dimensionality (must match model + DB column).",
        gt=0,
    )
    embedding_batch_size: int = Field(
        default=32,
        alias="EMBEDDING_BATCH_SIZE",
        description="Batch size for embedding generation.",
        gt=0,
    )
    load_embedding_model_on_startup: bool = Field(
        default=True,
        alias="LOAD_EMBEDDING_MODEL_ON_STARTUP",
        description="Load the local embedding model during app lifespan startup.",
    )

    # --- Retrieval / LLM (Phase 3) ---
    retrieval_top_k: int = Field(
        default=5,
        alias="RETRIEVAL_TOP_K",
        description="Number of nearest chunks to retrieve for each query.",
        gt=0,
    )
    openai_model: str = Field(
        default="gpt-4o-mini",
        alias="OPENAI_MODEL",
        description="OpenAI chat model used for grounded answers.",
    )
    openai_base_url: str | None = Field(
        default=None,
        alias="OPENAI_BASE_URL",
        description="Optional OpenAI-compatible API base URL.",
    )
    conversation_history_limit: int = Field(
        default=10,
        alias="CONVERSATION_HISTORY_LIMIT",
        description="Max recent messages (user+assistant) included in chat prompts.",
        gt=0,
    )
    llm_temperature: float = Field(
        default=0.0,
        alias="LLM_TEMPERATURE",
        description="Sampling temperature for grounded answers (prefer 0).",
        ge=0.0,
    )

    @property
    def is_production(self) -> bool:
        """Return True when running in production."""
        return self.environment == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a process-wide cached Settings instance."""
    return Settings()
