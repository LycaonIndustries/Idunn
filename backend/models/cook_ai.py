"""Pantry match data models for Iðunn Kitchen OS.

Encapsulates recipe inventory coverage evaluations, FEFO scores, and substitution suggestions.
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


class SubstitutionSuggestion(BaseModel):
    """Algorithmic culinary substitution suggestion.

    Maps a missing ingredient to functionally equivalent pantry or culinary alternatives.
    """

    target_ingredient: str = Field(description="Ingredient requiring replacement.")
    substitute_name: str = Field(description="Recommended functional replacement ingredient.")
    category: str = Field(description="Culinary category (e.g. acid, fat, dairy, thickener).")
    ratio: str = Field(description="Recommended replacement ratio (e.g. 1:1, 1:0.5).")
    in_pantry: bool = Field(default=False, description="True if substitute is in active pantry.")
    notes: str = Field(default="", description="Culinary application instructions or trade-offs.")


class SubstitutionQueryRequest(BaseModel):
    """Request payload to query culinary substitutions for an ingredient."""

    ingredient: str = Field(min_length=1, description="Ingredient name to find substitutes for.")
