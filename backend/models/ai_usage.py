"""AI usage tracking and token ledger models for Iðunn."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from pydantic import BaseModel, Field

# Pricing per million tokens across common generative models in USD.
PRICING_PER_MILLION_TOKENS: dict[str, dict[str, float]] = {
    "gemini-2.5-flash": {"input": 0.075, "output": 0.30},
    "gemini-2.0-flash": {"input": 0.10, "output": 0.40},
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
    "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.00},
    "claude-sonnet-4-5": {"input": 3.00, "output": 15.00},
    "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "default": {"input": 0.10, "output": 0.40},
}


def calculate_token_cost(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> float:
    """Calculate estimated USD cost based on prompt and completion token counts.

    Args:
        model: Identifier name of generative model.
        prompt_tokens: Number of prompt/input tokens.
        completion_tokens: Number of completion/output tokens.

    Returns:
        Estimated USD cost rounded to 6 decimal places.
    """
    # Select pricing profile matching model name or fall back to default baseline rate.
    rates = PRICING_PER_MILLION_TOKENS.get(model, PRICING_PER_MILLION_TOKENS["default"])
    input_cost = (prompt_tokens / 1_000_000.0) * rates["input"]
    output_cost = (completion_tokens / 1_000_000.0) * rates["output"]
    return round(input_cost + output_cost, 6)


class AIUsageLog(BaseModel):
    """Ledger document recording token counts and costs for a generative AI request."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str | None = None
    endpoint: str
    provider: str
    model: str
    prompt_tokens: int = Field(default=0, ge=0)
    completion_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)
    estimated_cost_usd: float = Field(default=0.0, ge=0.0)
    duration_ms: float = Field(default=0.0, ge=0.0)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AIUsageSummary(BaseModel):
    """Aggregated usage metrics exposed to user and administrator dashboards."""

    total_requests: int
    total_prompt_tokens: int
    total_completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float
    monthly_budget_usd: float = 10.0
    budget_used_percentage: float = 0.0
    by_model: dict[str, int] = Field(default_factory=dict)
