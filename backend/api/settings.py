"""Settings API endpoints for viewing and managing BYOK provider configurations."""

from __future__ import annotations

import contextlib
import os
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ..config import get_settings, settings
from .deps import AuthenticatedUser, get_current_user

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])

ENV_PATH = Path(".env")
ENV_EXAMPLE_PATH = Path(".env.example")


class SettingsStatusResponse(BaseModel):
    """Public settings status with sensitive keys masked."""

    database_backend: str
    supabase_configured: bool
    supabase_url: str | None = None
    supabase_key_masked: str | None = None
    gemini_configured: bool
    gemini_api_key_masked: str | None = None
    gemini_model: str
    anthropic_configured: bool
    anthropic_api_key_masked: str | None = None
    anthropic_model_extract: str
    openai_configured: bool
    openai_api_key_masked: str | None = None
    voyage_configured: bool
    voyage_api_key_masked: str | None = None
    active_llm_provider: str
    env_file_exists: bool
    allow_env_writes: bool = False


class UpdateSettingsRequest(BaseModel):
    """Payload for updating BYOK API keys and models."""

    supabase_url: str | None = Field(default=None, description="Supabase Project URL")
    supabase_key: str | None = Field(default=None, description="Supabase API Key (anon or service)")
    gemini_api_key: str | None = Field(default=None, description="Google Gemini API Key")
    gemini_model: str | None = Field(default=None, description="Gemini model identifier")
    anthropic_api_key: str | None = Field(default=None, description="Anthropic API Key")
    openai_api_key: str | None = Field(default=None, description="OpenAI API Key")
    voyage_api_key: str | None = Field(default=None, description="Voyage AI API Key")


def _mask_key(key: str | None) -> str | None:
    """Mask credentials so sensitive tokens are safe for screen display.

    Args:
        key: Plain-text API key or credential string.

    Returns:
        Masked string showing prefix and suffix, or None if key is absent.
    """
    # Prevent leaking plain text secrets in client API responses.
    if not key or not key.strip():
        return None
    k = key.strip()
    if len(k) <= 8:
        return "****"
    return f"{k[:4]}...{k[-4:]}"


def _get_active_provider() -> str:
    """Determine highest-priority configured LLM provider.

    Returns:
        String identifier of active provider or 'none'.
    """
    # Prioritize Google Gemini because of its generous free tier.
    if settings.gemini_api_key:
        return "gemini"
    if settings.anthropic_api_key:
        return "anthropic"
    if settings.openai_api_key:
        return "openai"
    return "none"


def _write_env_file(updates: dict[str, str]) -> None:
    """Update or create local .env file while preserving comments and structure.

    Args:
        updates: Dictionary of environment variable key-value pairs to persist.

    Returns:
        None.
    """
    # Read existing file to preserve user comments and unmanaged settings.
    lines: list[str] = []
    if ENV_PATH.is_file():
        lines = ENV_PATH.read_text(encoding="utf-8").splitlines()
    elif ENV_EXAMPLE_PATH.is_file():
        lines = ENV_EXAMPLE_PATH.read_text(encoding="utf-8").splitlines()

    updated_keys = set()
    new_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key, _ = stripped.split("=", 1)
            key = key.strip()
            if key in updates:
                new_lines.append(f"{key}={updates[key]}")
                updated_keys.add(key)
                continue
        new_lines.append(line)

    # Append any new configuration keys not already present in .env.
    for key, val in updates.items():
        if key not in updated_keys:
            new_lines.append(f"{key}={val}")

    ENV_PATH.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


@router.get("", response_model=SettingsStatusResponse)
async def get_settings_status(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> SettingsStatusResponse:
    """Return status of database and all BYOK providers with masked keys.

    Args:
        user: Authenticated caller identity.

    Returns:
        SettingsStatusResponse containing configuration flags and masked keys.
    """
    # Provide system diagnostics without revealing raw secrets.
    return SettingsStatusResponse(
        database_backend=settings.database_backend,
        supabase_configured=bool(settings.supabase_url and settings.supabase_key),
        supabase_url=settings.supabase_url,
        supabase_key_masked=_mask_key(settings.supabase_key),
        gemini_configured=bool(settings.gemini_api_key),
        gemini_api_key_masked=_mask_key(settings.gemini_api_key),
        gemini_model=settings.gemini_model,
        anthropic_configured=bool(settings.anthropic_api_key),
        anthropic_api_key_masked=_mask_key(settings.anthropic_api_key),
        anthropic_model_extract=settings.anthropic_model_extract,
        openai_configured=bool(settings.openai_api_key),
        openai_api_key_masked=_mask_key(settings.openai_api_key),
        voyage_configured=bool(settings.voyage_api_key),
        voyage_api_key_masked=_mask_key(settings.voyage_api_key),
        active_llm_provider=_get_active_provider(),
        env_file_exists=ENV_PATH.is_file(),
        allow_env_writes=settings.allow_env_writes,
    )


@router.post("", response_model=SettingsStatusResponse)
async def update_settings(
    req: UpdateSettingsRequest,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> SettingsStatusResponse:
    """Update settings at runtime and optionally persist them to local .env file.

    Args:
        req: Update request containing updated keys and model identifiers.
        user: Authenticated caller identity.

    Returns:
        Updated SettingsStatusResponse.
    """
    env_updates: dict[str, str] = {}

    # Mutate runtime configuration and prepare environment updates.
    if req.supabase_url is not None:
        val = req.supabase_url.strip()
        settings.supabase_url = val or None
        os.environ["SUPABASE_URL"] = val
        env_updates["SUPABASE_URL"] = val

    if req.supabase_key is not None:
        val = req.supabase_key.strip()
        settings.supabase_key = val or None
        os.environ["SUPABASE_KEY"] = val
        env_updates["SUPABASE_KEY"] = val
        from ..db.supabase_client import SupabaseClientManager

        # Reset client pool to force re-authentication with updated credentials.
        SupabaseClientManager.reset()

    if req.gemini_api_key is not None:
        val = req.gemini_api_key.strip()
        settings.gemini_api_key = val or None
        os.environ["GEMINI_API_KEY"] = val
        env_updates["GEMINI_API_KEY"] = val

    if req.gemini_model is not None and req.gemini_model.strip():
        model_val = req.gemini_model.strip()
        settings.gemini_model = model_val
        os.environ["GEMINI_MODEL"] = model_val
        env_updates["GEMINI_MODEL"] = model_val

    if req.anthropic_api_key is not None:
        val = req.anthropic_api_key.strip()
        settings.anthropic_api_key = val or None
        os.environ["ANTHROPIC_API_KEY"] = val
        env_updates["ANTHROPIC_API_KEY"] = val

    if req.openai_api_key is not None:
        val = req.openai_api_key.strip()
        settings.openai_api_key = val or None
        os.environ["OPENAI_API_KEY"] = val
        env_updates["OPENAI_API_KEY"] = val

    if req.voyage_api_key is not None:
        val = req.voyage_api_key.strip()
        settings.voyage_api_key = val or None
        os.environ["VOYAGE_API_KEY"] = val
        env_updates["VOYAGE_API_KEY"] = val

    # Guard disk modification to prevent arbitrary remote file corruption.
    if env_updates and settings.allow_env_writes:
        # Suppress file IO exceptions so disk issues do not break memory updates.
        with contextlib.suppress(Exception):
            _write_env_file(env_updates)

    # Invalidate settings lru_cache so fresh reads reload updated values.
    get_settings.cache_clear()
    return await get_settings_status(user)


@router.get("/ai-usage")
async def get_ai_usage_stats(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
):
    """Retrieve aggregated token consumption metrics and estimated USD costs for the current month.

    Args:
        user: Authenticated caller identity.

    Returns:
        AIUsageSummary containing monthly token totals and budget utilization.
    """
    from ..services.ai_usage_tracker import get_monthly_ai_usage_summary

    return await get_monthly_ai_usage_summary()
