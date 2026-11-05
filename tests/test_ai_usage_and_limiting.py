"""Tests for rate limiting on AI endpoints and LLM token usage tracking ledger."""

import pytest

from backend.api.limiter import limiter
from backend.db import COLLECTION_AI_USAGE
from backend.models.ai_usage import calculate_token_cost
from backend.services.ai_usage_tracker import (
    get_monthly_ai_usage_summary,
    record_ai_usage,
)


def test_calculate_token_cost() -> None:
    """Verify token cost calculation across Gemini and Claude pricing models."""
    # Gemini 2.5 Flash: input $0.075/M, output $0.30/M
    cost_gemini = calculate_token_cost(
        model="gemini-2.5-flash",
        prompt_tokens=1_000_000,
        completion_tokens=1_000_000,
    )
    assert cost_gemini == 0.375

    # Claude 3.5 Sonnet: input $3.00/M, output $15.00/M
    cost_claude = calculate_token_cost(
        model="claude-3-5-sonnet-20241022",
        prompt_tokens=100_000,
        completion_tokens=10_000,
    )
    assert cost_claude == round(0.30 + 0.15, 6)


@pytest.mark.asyncio
async def test_record_and_aggregate_ai_usage(db) -> None:
    """Verify recording token ledger entries and querying monthly aggregated metrics."""
    await db[COLLECTION_AI_USAGE].delete_many({})

    # Record two usage events
    await record_ai_usage(
        endpoint="/api/v1/recipes/extract",
        provider="gemini",
        model="gemini-2.5-flash",
        prompt_tokens=5000,
        completion_tokens=500,
        duration_ms=1200.0,
        user_id="usr_test_1",
    )
    await record_ai_usage(
        endpoint="/api/v1/cook-ai/pantry-to-plate",
        provider="anthropic",
        model="claude-sonnet-4-5",
        prompt_tokens=3000,
        completion_tokens=800,
        duration_ms=2100.0,
        user_id="usr_test_1",
    )

    summary = await get_monthly_ai_usage_summary(monthly_budget_usd=10.0)
    assert summary.total_requests == 2
    assert summary.total_prompt_tokens == 8000
    assert summary.total_completion_tokens == 1300
    assert summary.total_tokens == 9300
    assert summary.estimated_cost_usd > 0.0
    assert summary.by_model["gemini-2.5-flash"] == 1
    assert summary.by_model["claude-sonnet-4-5"] == 1


def test_api_get_ai_usage_stats(api_client) -> None:
    """Verify GET /api/v1/settings/ai-usage returns aggregate usage schema."""
    response = api_client.get("/api/v1/settings/ai-usage")
    assert response.status_code == 200
    data = response.json()
    assert "total_requests" in data
    assert "total_tokens" in data
    assert "estimated_cost_usd" in data
    assert "monthly_budget_usd" in data
    assert "by_model" in data


def test_rate_limiter_blocks_excessive_calls(api_client) -> None:
    """Verify that rapid requests beyond threshold receive 429 Too Many Requests."""
    endpoint = "/api/v1/cook-ai/pantry-to-plate"
    payload = {"servings": 2}

    try:
        # Endpoint limit is 10/minute; sending 12 requests should trip 429.
        responses = [api_client.post(endpoint, json=payload) for _ in range(12)]
        status_codes = [r.status_code for r in responses]

        # At least the later requests must be rate limited to 429
        assert 429 in status_codes
    finally:
        limiter.reset()
