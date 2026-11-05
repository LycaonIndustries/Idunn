"""Service for logging LLM token burn and querying aggregate cost metrics."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from ..db import COLLECTION_AI_USAGE, MongoClient
from ..models.ai_usage import AIUsageLog, AIUsageSummary, calculate_token_cost

logger = logging.getLogger(__name__)


async def record_ai_usage(
    endpoint: str,
    provider: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    duration_ms: float = 0.0,
    user_id: str | None = None,
) -> AIUsageLog:
    """Record LLM token usage log to database collection.

    Args:
        endpoint: API path invoking the model.
        provider: AI provider name.
        model: Model identifier string.
        prompt_tokens: Input token count.
        completion_tokens: Output token count.
        duration_ms: Execution duration in milliseconds.
        user_id: Optional caller identifier.

    Returns:
        Persisted AIUsageLog instance.
    """
    total = prompt_tokens + completion_tokens
    cost = calculate_token_cost(model, prompt_tokens, completion_tokens)
    log_entry = AIUsageLog(
        user_id=user_id,
        endpoint=endpoint,
        provider=provider,
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total,
        estimated_cost_usd=cost,
        duration_ms=duration_ms,
    )

    try:
        # Save usage record to active database collection.
        db = MongoClient.get_db()
        await db[COLLECTION_AI_USAGE].insert_one(log_entry.model_dump())
    except Exception as exc:
        # Log warning on persistence failure to avoid blocking user request execution.
        logger.warning("Failed to record AI usage ledger entry: %s", exc)

    return log_entry


async def get_monthly_ai_usage_summary(
    monthly_budget_usd: float = 10.0,
) -> AIUsageSummary:
    """Aggregate token usage and cost metrics for the current calendar month.

    Args:
        monthly_budget_usd: Budget ceiling in USD for percentage tracking.

    Returns:
        Populated AIUsageSummary instance.
    """
    now = datetime.now(UTC)
    start_of_month = datetime(now.year, now.month, 1, tzinfo=UTC)

    total_requests = 0
    total_prompt = 0
    total_completion = 0
    total_cost = 0.0
    by_model: dict[str, int] = {}

    try:
        db = MongoClient.get_db()
        cursor = db[COLLECTION_AI_USAGE].find({"timestamp": {"$gte": start_of_month}})
        records = await cursor.to_list(length=10000)

        for rec in records:
            total_requests += 1
            total_prompt += int(rec.get("prompt_tokens", 0))
            total_completion += int(rec.get("completion_tokens", 0))
            total_cost += float(rec.get("estimated_cost_usd", 0.0))
            mod = str(rec.get("model", "unknown"))
            by_model[mod] = by_model.get(mod, 0) + 1
    except Exception as exc:
        logger.warning("Failed to aggregate AI usage summary from database: %s", exc)

    total_tokens = total_prompt + total_completion
    budget_pct = (
        0.0 if monthly_budget_usd <= 0 else round((total_cost / monthly_budget_usd) * 100.0, 2)
    )

    return AIUsageSummary(
        total_requests=total_requests,
        total_prompt_tokens=total_prompt,
        total_completion_tokens=total_completion,
        total_tokens=total_tokens,
        estimated_cost_usd=round(total_cost, 4),
        monthly_budget_usd=monthly_budget_usd,
        budget_used_percentage=budget_pct,
        by_model=by_model,
    )
