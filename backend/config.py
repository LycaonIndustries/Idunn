"""Configuration for Iðunn.

Loads from environment variables with sensible defaults.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_name: str = "Iðunn"
    app_version: str = "0.1.0"
    debug: bool = False
    log_level: str = "INFO"

    # Database
    database_backend: str = "supabase"  # "supabase" or "mongodb"
    supabase_url: str | None = None
    supabase_key: str | None = None

    # MongoDB (legacy / optional)
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_db_name: str = "idunn"

    # Redis (for Arq jobs)
    redis_url: str = "redis://localhost:6379"

    # Object store (MinIO/R2)
    object_store_endpoint: str | None = None
    object_store_access_key: str | None = None
    object_store_secret_key: str | None = None
    object_store_bucket: str = "idunn"

    # LLM (Anthropic)
    anthropic_api_key: str | None = None
    anthropic_model_extract: str = "claude-haiku-4-5-20251001"
    anthropic_model_rank: str = "claude-sonnet-4-5"

    # LLM (BYOK Providers)
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    openai_api_key: str | None = None

    # Embeddings
    voyage_api_key: str | None = None
    embedding_model: str = "voyage-3-large"
    embedding_dimensions: int = Field(1024, ge=1)
    ingredient_vector_index: str = "ingredient_embeddings"
    ingredient_match_threshold: float = Field(0.9, ge=0, le=1)
    ingredient_match_margin: float = Field(0.05, ge=0, le=1)

    # Recipe sources
    source_timeout_seconds: float = Field(30, gt=0)
    source_max_bytes: int = Field(2_000_000, ge=1)
    source_max_text_chars: int = Field(60_000, ge=1)
    extraction_confidence_threshold: float = Field(0.85, ge=0, le=1)
    video_max_seconds: int = Field(1800, ge=1)
    video_max_bytes: int = Field(100_000_000, ge=1)
    video_timeout_seconds: float = Field(900, gt=0)
    whisper_model: str = "large-v3"
    whisper_local_files_only: bool = True

    # Reranker
    cohere_api_key: str | None = None
    reranker_model: str = "rerank-3"

    # OCR
    paddle_ocr_enabled: bool = True

    # CORS
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
