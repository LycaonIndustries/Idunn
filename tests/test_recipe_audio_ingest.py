"""Tests for the direct audio/voice note recipe ingestion endpoint."""

from unittest.mock import AsyncMock

from backend.services.recipe_ingest import IngestResult


def test_ingest_audio_success(api_client, service, monkeypatch):
    """Uploading a valid audio file returns 201 Created."""
    mock_result = IngestResult(
        success=True,
        recipe_id="507f1f77bcf86cd799439012",
        confidence=0.93,
        needs_review=False,
    )
    monkeypatch.setattr(
        service,
        "ingest_from_audio",
        AsyncMock(return_value=mock_result),
    )

    # Fake audio bytes
    audio_bytes = b"ID3\x04\x00\x00\x00\x00\x00#" + b"\x00" * 100
    files = {"file": ("voice_recipe.mp3", audio_bytes, "audio/mpeg")}
    data = {"source_name": "Family Voice Note"}

    response = api_client.post("/api/v1/recipes/ingest/audio", files=files, data=data)
    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert body["recipe_id"] == "507f1f77bcf86cd799439012"


def test_ingest_audio_rejects_non_audio_mime(api_client):
    """Uploading a non-audio file returns 400 Bad Request."""
    files = {"file": ("document.pdf", b"%PDF-1.4...", "application/pdf")}
    response = api_client.post("/api/v1/recipes/ingest/audio", files=files)
    assert response.status_code == 400
    assert "audio" in response.json()["detail"].lower()


def test_ingest_audio_rejects_empty_file(api_client):
    """Uploading an empty audio file returns 400 Bad Request."""
    files = {"file": ("empty.mp3", b"", "audio/mpeg")}
    response = api_client.post("/api/v1/recipes/ingest/audio", files=files)
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()
