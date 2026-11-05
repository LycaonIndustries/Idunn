"""Persistent storage service for application settings and BYOK credentials."""

from __future__ import annotations

import contextlib
import json
import os
from pathlib import Path

from ..config import get_settings, settings

SETTINGS_PATH = Path("data/settings.json")
KEY_MAP = {
    "SUPABASE_URL": "supabase_url",
    "SUPABASE_KEY": "supabase_key",
    "GEMINI_API_KEY": "gemini_api_key",
    "GEMINI_MODEL": "gemini_model",
    "ANTHROPIC_API_KEY": "anthropic_api_key",
    "OPENAI_API_KEY": "openai_api_key",
    "VOYAGE_API_KEY": "voyage_api_key",
}


def _read_data_file() -> dict[str, str]:
    """Read saved settings from persistent volume file."""
    if not SETTINGS_PATH.is_file():
        return {}
    with contextlib.suppress(Exception):
        data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        return {k: str(v) for k, v in data.items() if isinstance(k, str) and v is not None}
    return {}


def _write_data_file(updates: dict[str, str]) -> None:
    """Write updated settings to persistent data directory."""
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    existing = _read_data_file()
    existing.update(updates)
    SETTINGS_PATH.write_text(json.dumps(existing, indent=2), encoding="utf-8")


async def save_persisted_settings(updates: dict[str, str]) -> None:
    """Persist settings updates to disk volume and database collection."""
    if not updates:
        return
    with contextlib.suppress(Exception):
        _write_data_file(updates)
    with contextlib.suppress(Exception):
        from ..db import DatabaseRouter

        db = DatabaseRouter()
        await db["settings"].find_one_and_update(
            {"_id": "app_settings"}, {"$set": updates}, upsert=True
        )


async def load_persisted_settings() -> None:
    """Load persisted settings on startup and apply to runtime environment."""
    loaded = _read_data_file()
    with contextlib.suppress(Exception):
        from ..db import DatabaseRouter

        doc = await DatabaseRouter()["settings"].find_one({"_id": "app_settings"})
        if doc:
            loaded.update(
                {k: v for k, v in doc.items() if k not in ("_id", "id") and isinstance(v, str)}
            )

    for env_key, val in loaded.items():
        if val:
            os.environ[env_key] = val
            attr = KEY_MAP.get(env_key)
            if attr and hasattr(settings, attr):
                setattr(settings, attr, val)
    get_settings.cache_clear()
