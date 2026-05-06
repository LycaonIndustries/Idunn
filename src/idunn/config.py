"""Configuration for Iðunn.

Loads from environment variables with sensible defaults.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # App
    app_name: str = "Iðunn"
    app_version: str = "0.1.0"
    debug: bool = False

    # MongoDB
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_db_name: str = "idunn"

    # Redis (for Arq jobs)
    redis_url: str = "redis://localhost:6379"

    # Object store (MinIO/R2)
    object_store_endpoint: Optional[str] = None
    object_store_access_key: Optional[str] = None
    object_store_secret_key: Optional[str] = None
    object_store_bucket: str = "idunn"

    # LLM (Anthropic)
    anthropic_api_key: Optional[str] = None
    anthropic_model_extract: str = "claude-3-5-haiku-latest"
    anthropic_model_rank: str = "claude-sonnet-4-5"

    # Embeddings
    voyage_api_key: Optional[str] = None
    embedding_model: str = "voyage-3-large"

    # Reranker
    cohere_api_key: Optional[str] = None
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
