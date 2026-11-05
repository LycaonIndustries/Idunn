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
    assert "allow_env_writes" in data


def test_update_settings_byok_with_env_writes_allowed(client, monkeypatch, tmp_path):
    """POST /api/v1/settings writes to .env only when allow_env_writes is true."""
    test_env = tmp_path / ".env"
    monkeypatch.setattr("backend.api.settings.ENV_PATH", test_env)
    monkeypatch.setattr(settings, "allow_env_writes", True)

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
    assert data["allow_env_writes"] is True

    # Verify file was written when enabled
    assert test_env.exists()
    assert "GEMINI_API_KEY=AIzaSyTestKey1234567890" in test_env.read_text(encoding="utf-8")

    # Reset
    settings.gemini_api_key = None


def test_update_settings_byok_disallows_env_writes_by_default(client, monkeypatch, tmp_path):
    """POST /api/v1/settings updates runtime memory but guards .env from writes by default."""
    test_env = tmp_path / ".env"
    monkeypatch.setattr("backend.api.settings.ENV_PATH", test_env)
    monkeypatch.setattr(settings, "allow_env_writes", False)

    resp = client.post(
        "/api/v1/settings",
        json={
            "openai_api_key": "sk-testOpenAIKey9999",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["openai_configured"] is True
    assert data["openai_api_key_masked"] == "sk-t...9999"
    assert data["allow_env_writes"] is False

    # Verify .env was not written on disk
    assert not test_env.exists()

    # Reset
    settings.openai_api_key = None


def test_settings_requires_authentication_when_auth_enabled(client, monkeypatch):
    """Unauthenticated calls to settings endpoints return 401 when auth_enabled is true."""
    monkeypatch.setattr(settings, "auth_enabled", True)

    # Test GET without credentials
    resp_get = client.get("/api/v1/settings")
    assert resp_get.status_code == 401
    assert "credentials were not provided" in resp_get.json()["detail"]

    # Test POST without credentials
    resp_post = client.post("/api/v1/settings", json={"gemini_model": "gemini-2.5-flash"})
    assert resp_post.status_code == 401
    assert "credentials were not provided" in resp_post.json()["detail"]


def test_settings_succeeds_with_valid_bearer_token(client):
    """Authenticated caller with valid Clerk JWT accesses settings endpoints successfully."""
    from backend.api.deps import AuthenticatedUser, get_current_user

    async def fake_user():
        return AuthenticatedUser(
            id="user_clerk_123",
            email="admin@kitchen.os",
            first_name="Admin",
            last_name="User",
        )

    app.dependency_overrides[get_current_user] = fake_user
    try:
        resp = client.get("/api/v1/settings")
        assert resp.status_code == 200
        assert resp.json()["database_backend"] == settings.database_backend
    finally:
        app.dependency_overrides.pop(get_current_user, None)
