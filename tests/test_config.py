"""Tests for application settings and configuration resilience."""

import os
from unittest.mock import patch

from idunn.config import Settings


def test_settings_loads_with_extra_env_vars() -> None:
    """Arbitrary extra environment variables must be ignored without raising ValidationError."""
    with patch.dict(os.environ, {"EXTRA_UNKNOWN_VAR": "some_value", "ANOTHER_RANDOM_ENV": "123"}):
        settings = Settings()
        assert settings.app_name == "Iðunn"


def test_settings_gemini_and_openai_byok_fields() -> None:
    """Settings supports Gemini and OpenAI BYOK keys."""
    with patch.dict(
        os.environ,
        {
            "GEMINI_API_KEY": "test-gemini-key",
            "GEMINI_MODEL": "gemini-2.5-flash",
            "OPENAI_API_KEY": "test-openai-key",
        },
    ):
        settings = Settings()
        assert settings.gemini_api_key == "test-gemini-key"
        assert settings.gemini_model == "gemini-2.5-flash"
        assert settings.openai_api_key == "test-openai-key"
