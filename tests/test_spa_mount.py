"""Tests for SPA static mount and API coexistence.

Verifies that:
- GET / returns HTML (index.html) when web_dist is present
- GET /api/v1/recipes still returns JSON (not HTML)
- GET /health returns JSON health status
- GET /docs returns Swagger UI
- OpenAPI spec is accessible

Uses the same TestClient + dependency override pattern as the rest of the suite
to avoid connecting to any real MongoDB instance.
"""

from __future__ import annotations

import pytest
from mongomock_motor import AsyncMongoMockClient

from idunn.api.recipes import get_ingest_service
from idunn.db import get_db
from idunn.main import app, WEB_DIST
from idunn.services.recipe_ingest import RecipeIngestService


@pytest.fixture
def spa_client():
    """TestClient with mock DB, no lifespan — same pattern as conftest.api_client."""
    from fastapi.testclient import TestClient
    from idunn.config import Settings

    db = AsyncMongoMockClient()["idunn_test"]
    config = Settings(
        _env_file=None,
        anthropic_api_key=None,
        gemini_api_key=None,
        openai_api_key=None,
        voyage_api_key=None,
        embedding_dimensions=3,
    )
    service = RecipeIngestService(db, config)

    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_ingest_service] = lambda: service

    client = TestClient(app)
    try:
        yield client
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)


def test_root_returns_html_or_json(spa_client):
    """GET / serves index.html (SPA) when web_dist is built, otherwise JSON fallback."""
    resp = spa_client.get("/")
    assert resp.status_code == 200
    ct = resp.headers.get("content-type", "")
    if WEB_DIST.is_dir():
        assert "text/html" in ct
        assert "Iðunn" in resp.text or "root" in resp.text
    else:
        assert "application/json" in ct


def test_api_routes_still_json(spa_client):
    """API routes must return JSON, not HTML, even with SPA mounted."""
    resp = spa_client.get("/api/v1/recipes")
    assert resp.status_code == 200
    assert "application/json" in resp.headers.get("content-type", "")


def test_health_returns_json(spa_client):
    """Health endpoint must always return JSON."""
    resp = spa_client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "app" in data


def test_openapi_json_accessible(spa_client):
    """OpenAPI spec must remain accessible."""
    resp = spa_client.get("/openapi.json")
    assert resp.status_code == 200
    data = resp.json()
    assert "openapi" in data
    assert "paths" in data


def test_swagger_docs_accessible(spa_client):
    """Swagger /docs page must not be captured by SPA catch-all."""
    resp = spa_client.get("/docs")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")
    assert "swagger" in resp.text.lower() or "openapi" in resp.text.lower()
