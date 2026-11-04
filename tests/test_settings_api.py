"""Tests for the Settings & BYOK API endpoint."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.config import settings
from backend.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_get_settings_status(client):
    """GET /api/v1/settings returns configured status and masked keys."""
    resp = client.get("/api/v1/settings")
    assert resp.status_code == 200
    data = resp.json()
    assert "gemini_configured" in data
    assert "anthropic_configured" in data
    assert "active_llm_provider" in data
    assert "env_file_exists" in data


def test_update_settings_byok(client, monkeypatch, tmp_path):
    """POST /api/v1/settings updates settings at runtime and returns new status."""
    # Temporarily point ENV_PATH to a temporary file
    test_env = tmp_path / ".env"
    monkeypatch.setattr("backend.api.settings.ENV_PATH", test_env)

    resp = client.post(
        "/api/v1/settings",
        json={
            "gemini_api_key": "AIzaSyTestKey1234567890",
            "gemini_model": "gemini-2.5-flash",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["gemini_configured"] is True
    assert data["gemini_api_key_masked"] == "AIza...7890"
    assert data["gemini_model"] == "gemini-2.5-flash"
    assert data["active_llm_provider"] == "gemini"

    # Verify runtime settings were updated
    assert settings.gemini_api_key == "AIzaSyTestKey1234567890"
    assert settings.gemini_model == "gemini-2.5-flash"

    # Reset
    settings.gemini_api_key = None
