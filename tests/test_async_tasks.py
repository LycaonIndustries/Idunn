"""Tests for ARQ background tasks, worker settings, and jobs API router."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from arq.jobs import JobStatus
from starlette.testclient import TestClient

from backend.api.deps import AuthenticatedUser, get_current_user
from backend.api.jobs import enqueue_background_task
from backend.main import app
from backend.workers.tasks import (
    WorkerSettings,
    process_receipt_ocr_task,
    process_youtube_audio_task,
    shutdown,
    startup,
)


@pytest.mark.asyncio
async def test_worker_lifecycle_and_tasks() -> None:
    """Verify worker startup, shutdown, and task execution payloads."""
    ctx: dict = {}

    # Startup hook initializes worker context.
    await startup(ctx)
    assert ctx.get("worker_ready") is True

    # Receipt OCR task execution.
    receipt_res = await process_receipt_ocr_task(ctx, "/tmp/receipt.jpg", "user_123")
    assert receipt_res["status"] == "completed"
    assert receipt_res["file_path"] == "/tmp/receipt.jpg"
    assert receipt_res["user_id"] == "user_123"

    # YouTube audio transcription task execution.
    yt_res = await process_youtube_audio_task(ctx, "https://youtube.com/watch?v=123", "user_123")
    assert yt_res["status"] == "completed"
    assert yt_res["video_url"] == "https://youtube.com/watch?v=123"

    # Shutdown hook cleanly closes context.
    await shutdown(ctx)
    assert ctx.get("worker_ready") is False


def test_worker_settings_configuration() -> None:
    """Verify ARQ worker settings configure timeouts, concurrency, and task functions."""
    assert len(WorkerSettings.functions) == 2
    assert WorkerSettings.max_jobs == 5
    assert WorkerSettings.job_timeout == 300
    assert WorkerSettings.on_startup == startup
    assert WorkerSettings.on_shutdown == shutdown


@pytest.mark.asyncio
async def test_enqueue_background_task_unreachable_redis() -> None:
    """Verify enqueueing gracefully returns None when Redis is offline."""
    # When redis connection fails, task enqueueing must not raise unhandled exception.
    with patch("backend.api.jobs.get_redis_pool", return_value=None):
        job_id = await enqueue_background_task("process_receipt_ocr_task", "/tmp/img.png", "u1")
        assert job_id is None


def test_get_job_status_not_found(api_client: TestClient) -> None:
    """Verify job polling returns not_found status for missing or offline job IDs."""
    caller = AuthenticatedUser(id="job_tester", email="tester@example.com")
    app.dependency_overrides[get_current_user] = lambda: caller

    with patch("backend.api.jobs.get_redis_pool", return_value=None):
        res = api_client.get("/api/v1/jobs/nonexistent_job_12345")
        assert res.status_code == 200
        data = res.json()
        assert data["job_id"] == "nonexistent_job_12345"
        assert data["status"] == "not_found"


def test_get_job_status_mocked_complete(api_client: TestClient) -> None:
    """Verify job polling returns complete status and execution payload when job finishes."""
    caller = AuthenticatedUser(id="job_tester", email="tester@example.com")
    app.dependency_overrides[get_current_user] = lambda: caller

    # Mock Arq Redis pool and Job instance to simulate finished job.
    mock_job = AsyncMock()
    mock_job.status = AsyncMock(return_value=JobStatus.complete)
    mock_job.result = AsyncMock(return_value={"items_found": 3})
    mock_job.info = AsyncMock(return_value=None)

    mock_pool = AsyncMock()
    mock_pool.close = AsyncMock()

    with (
        patch("backend.api.jobs.get_redis_pool", return_value=mock_pool),
        patch("backend.api.jobs.Job", return_value=mock_job),
    ):
        res = api_client.get("/api/v1/jobs/finished_job_999")
        assert res.status_code == 200
        data = res.json()
        assert data["job_id"] == "finished_job_999"
        assert data["status"] == "complete"
        assert data["result"] == {"items_found": 3}
