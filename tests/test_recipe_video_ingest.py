"""Tests for silent video reel frame extraction and recipe ingestion."""

from unittest.mock import AsyncMock

import pytest

from backend.services.recipe_ingest import IngestResult


def test_ingest_video_success(api_client, service, monkeypatch):
    """Uploading a valid video file returns 201 Created."""
    mock_result = IngestResult(
        success=True,
        recipe_id="507f1f77bcf86cd799439013",
        confidence=0.91,
        needs_review=False,
    )
    monkeypatch.setattr(
        service,
        "ingest_from_video",
        AsyncMock(return_value=mock_result),
    )

    # Fake mp4 header
    video_bytes = b"\x00\x00\x00 ftypisom" + b"\x00" * 200
    files = {"file": ("cooking_reel.mp4", video_bytes, "video/mp4")}
    data = {"source_name": "Instagram Reel"}

    response = api_client.post("/api/v1/recipes/ingest/video", files=files, data=data)
    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert body["recipe_id"] == "507f1f77bcf86cd799439013"


def test_ingest_video_rejects_non_video_mime(api_client):
    """Uploading a non-video file returns 400 Bad Request."""
    files = {"file": ("text.txt", b"not a video", "text/plain")}
    response = api_client.post("/api/v1/recipes/ingest/video", files=files)
    assert response.status_code == 400
    assert "video" in response.json()["detail"].lower()


def test_ingest_video_rejects_empty_file(api_client):
    """Uploading an empty video file returns 400 Bad Request."""
    files = {"file": ("empty.mp4", b"", "video/mp4")}
    response = api_client.post("/api/v1/recipes/ingest/video", files=files)
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_sample_video_keyframes_empty_bytes_raises():
    """Attempting to extract frames from invalid/empty bytes raises ExtractionError."""
    from backend.services.ingest_errors import ExtractionError
    from backend.services.video_frames import sample_video_keyframes

    with pytest.raises(ExtractionError):
        await sample_video_keyframes(b"corrupt video stream")
