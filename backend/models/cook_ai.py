"""Pantry match data models for Iðunn Kitchen OS.

Encapsulates recipe inventory coverage evaluations and FEFO expiry scores.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class PantryMatchResult(BaseModel):
    """Evaluation result comparing recipe ingredients against active pantry stock.

    Identifies which ingredients are present, missing, and computes readiness.
    """

    recipe_id: str = Field(description="Recipe document identifier.")
    recipe_title: str = Field(description="Display title of the recipe.")
    coverage_percentage: float = Field(
        ge=0.0,
        le=100.0,
        description="Percentage of required ingredients currently present in pantry.",
    )
    matched_ingredients: list[str] = Field(
        default_factory=list,
        description="List of recipe ingredients found in pantry inventory.",
    )
    missing_ingredients: list[str] = Field(
        default_factory=list,
        description="List of recipe ingredients missing from pantry inventory.",
    )
    expiry_urgency_score: float = Field(
        default=0.0,
        ge=0.0,
        description="Priority boost derived from perishables expiring within 72 hours.",
    )
    can_cook_now: bool = Field(
        default=False,
        description="True when 100% of required ingredients are in stock.",
    )
