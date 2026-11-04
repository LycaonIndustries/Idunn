"""Settings API endpoints for viewing and managing BYOK provider configurations."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..config import get_settings, settings

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])

ENV_PATH = Path(".env")
ENV_EXAMPLE_PATH = Path(".env.example")


class SettingsStatusResponse(BaseModel):
    """Public settings status with sensitive keys masked."""

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


class UpdateSettingsRequest(BaseModel):
    """Payload for updating BYOK API keys and models."""

    gemini_api_key: str | None = Field(default=None, description="Google Gemini API Key")
    gemini_model: str | None = Field(default=None, description="Gemini model identifier")
    anthropic_api_key: str | None = Field(default=None, description="Anthropic API Key")
    openai_api_key: str | None = Field(default=None, description="OpenAI API Key")
    voyage_api_key: str | None = Field(default=None, description="Voyage AI API Key")


def _mask_key(key: str | None) -> str | None:
    if not key or not key.strip():
        return None
    k = key.strip()
    if len(k) <= 8:
        return "****"
    return f"{k[:4]}...{k[-4:]}"


def _get_active_provider() -> str:
    if settings.gemini_api_key:
        return "gemini"
    if settings.anthropic_api_key:
        return "anthropic"
    if settings.openai_api_key:
        return "openai"
    return "none"


def _write_env_file(updates: dict[str, str]) -> None:
    """Updates or creates .env file preserving existing comments/entries."""
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

    # Append any remaining keys not present in original file
    for key, val in updates.items():
        if key not in updated_keys:
            new_lines.append(f"{key}={val}")

    ENV_PATH.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


@router.get("", response_model=SettingsStatusResponse)
async def get_settings_status() -> SettingsStatusResponse:
    """Return status of all BYOK providers with masked keys."""
    return SettingsStatusResponse(
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
    )


@router.post("", response_model=SettingsStatusResponse)
async def update_settings(req: UpdateSettingsRequest) -> SettingsStatusResponse:
    """Update BYOK settings at runtime and persist them to .env."""
    env_updates: dict[str, str] = {}

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

    if env_updates:
        try:
            _write_env_file(env_updates)
        except Exception:
            # Runtime settings are already updated; file write failure shouldn't crash request
            pass

    get_settings.cache_clear()
    return await get_settings_status()
