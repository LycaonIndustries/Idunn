"""Tests for the image/screenshot recipe ingestion endpoint."""

from unittest.mock import AsyncMock

import pytest

from idunn.models.recipe import RecipeCreate
from idunn.services.recipe_ingest import IngestResult
from idunn.services.recipe_providers import ExtractedRecipe


@pytest.fixture
def mock_extracted_image_recipe():
    recipe = RecipeCreate(
        title="Dosa",
        ingredients=[{"name": "dosa batter", "quantity": 1, "unit": "cup"}],
        steps=[{"step_number": 1, "instruction": "Spread batter on hot tawa."}],
        region="south_india",
        description="Crispy South Indian dosa",
    )
    return ExtractedRecipe(recipe=recipe, confidence=0.95)


def test_ingest_image_success(api_client, service, monkeypatch):
    """Uploading a valid recipe screenshot returns 201 Created."""
    mock_result = IngestResult(
        success=True,
        recipe_id="507f1f77bcf86cd799439011",
        confidence=0.95,
        needs_review=False,
    )
    monkeypatch.setattr(
        service,
        "ingest_from_image",
        AsyncMock(return_value=mock_result),
    )

    # Fake PNG content
    image_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"\x00" * 50
    files = {"file": ("cookbook_photo.png", image_bytes, "image/png")}
    data = {"source_name": "Cookbook Scan"}

    response = api_client.post("/api/v1/recipes/ingest/image", files=files, data=data)
    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert body["recipe_id"] == "507f1f77bcf86cd799439011"


def test_ingest_image_rejects_non_image_mime(api_client):
    """Uploading a non-image file type returns 400 Bad Request."""
    files = {"file": ("notes.txt", b"just some text", "text/plain")}
    response = api_client.post("/api/v1/recipes/ingest/image", files=files)
    assert response.status_code == 400
    assert "image" in response.json()["detail"].lower()


def test_ingest_image_rejects_empty_file(api_client):
    """Uploading an empty image returns 400 Bad Request."""
    files = {"file": ("empty.png", b"", "image/png")}
    response = api_client.post("/api/v1/recipes/ingest/image", files=files)
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()
