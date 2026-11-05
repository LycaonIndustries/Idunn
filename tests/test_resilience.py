"""Unit and integration tests for exponential backoff retries and resilience policies."""

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from pymongo.errors import AutoReconnect, NetworkTimeout, ServerSelectionTimeoutError

from backend.db.resilience import (
    with_db_retry,
    with_provider_retry,
)
from backend.db.supabase_client import SupabaseCollection


@pytest.mark.asyncio
async def test_with_db_retry_succeeds_on_second_attempt() -> None:
    """Verify that transient AutoReconnect error retries and succeeds on attempt 2."""
    call_count = 0

    @with_db_retry(max_attempts=3, initial_delay=0.01, max_delay=0.05)
    async def flaky_db_operation() -> str:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise AutoReconnect("Connection reset by peer")
        return "success"

    result = await flaky_db_operation()
    assert result == "success"
    assert call_count == 2


@pytest.mark.asyncio
async def test_with_db_retry_reraises_after_exhausting_attempts() -> None:
    """Verify that persistent transient error reraises after max attempts are exhausted."""
    call_count = 0

    @with_db_retry(max_attempts=3, initial_delay=0.01, max_delay=0.05)
    async def always_failing_db_call() -> None:
        nonlocal call_count
        call_count += 1
        raise NetworkTimeout("Database socket timed out")

    with pytest.raises(NetworkTimeout):
        await always_failing_db_call()
    assert call_count == 3


@pytest.mark.asyncio
async def test_with_db_retry_does_not_retry_non_transient_error() -> None:
    """Verify that permanent errors like ValueError or KeyError are not retried."""
    call_count = 0

    @with_db_retry(max_attempts=3, initial_delay=0.01, max_delay=0.05)
    async def bad_syntax_call() -> None:
        nonlocal call_count
        call_count += 1
        raise ValueError("Invalid query parameter format")

    with pytest.raises(ValueError):
        await bad_syntax_call()
    assert call_count == 1


@pytest.mark.asyncio
async def test_with_provider_retry_recovers_from_transient_http_timeout() -> None:
    """Verify provider retry recovers from transient httpx.ReadTimeout."""
    call_count = 0

    @with_provider_retry(max_attempts=3, initial_delay=0.01, max_delay=0.05)
    async def flaky_ai_call() -> dict[str, str]:
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise httpx.ReadTimeout("Gemini gateway read timeout")
        return {"response": "recipe json"}

    result = await flaky_ai_call()
    assert result == {"response": "recipe json"}
    assert call_count == 3


@pytest.mark.asyncio
async def test_supabase_collection_falls_back_to_memory_after_retry_failure() -> None:
    """Ensure Supabase collection gracefully falls back to memory if cloud insert fails."""
    fake_client = MagicMock()
    mock_memory = MagicMock()
    mock_insert_res = MagicMock()
    mock_insert_res.inserted_id = "mem_fallback_123"
    mock_memory.insert_one = AsyncMock(return_value=mock_insert_res)

    adapter = SupabaseCollection("recipes", fake_client, mock_memory)

    # Mock _execute_remote_insert to always raise transient network timeout
    adapter._execute_remote_insert = AsyncMock(
        side_effect=ServerSelectionTimeoutError("Supabase paused")
    )

    doc = {"title": "Masala Dosa", "servings": 2}
    result = await adapter.insert_one(doc)

    assert result.inserted_id == "mem_fallback_123"
    mock_memory.insert_one.assert_called_once()
