"""Pantry match data models for Iðunn Kitchen OS.

Coverage evaluations, substitutions, and generative pantry-to-plate recipes.
"""

from __future__ import annotations

from typing import Any

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


class PantryToPlateRequest(BaseModel):
    """User-triggered request to synthesize an on-the-fly recipe from current pantry items."""

    selected_item_ids: list[str] = Field(
        default_factory=list,
        description="Optional list of specific inventory item IDs to prioritize.",
    )
    meal_type: str = Field(default="dinner", description="Meal category (e.g. dinner, quick meal).")
    servings: int = Field(default=2, ge=1, le=12, description="Target number of portions.")
    dietary_preference: str | None = Field(default=None, description="e.g. veg, non_veg.")


class PantryToPlateRecipe(BaseModel):
    """AI-synthesized custom recipe tailored strictly to available pantry ingredients."""

    title: str = Field(description="Generated recipe name.")
    description: str = Field(default="", description="Summary of flavors and dish concept.")
    prep_time_minutes: int = Field(default=10, description="Preparation duration.")
    cook_time_minutes: int = Field(default=20, description="Active cooking duration.")
    servings: int = Field(default=2, description="Number of servings.")
    cuisine_type: str = Field(default="veg", description="Cuisine or dietary style.")
    ingredients: list[dict[str, Any]] = Field(
        default_factory=list,
        description="List of ingredients used from pantry inventory.",
    )
    steps: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Ordered cooking steps.",
    )
    assumed_staples: list[str] = Field(
        default_factory=lambda: ["salt", "water", "cooking oil", "black pepper"],
        description="Assumed basic household pantry staples used.",
    )
