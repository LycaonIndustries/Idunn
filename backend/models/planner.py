"""Weekly meal planning and scheduled recipe slot data models."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field


class MealType(StrEnum):
    """Categorical classification of daily meal slots."""

    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    SNACK = "snack"
    DINNER = "dinner"


class MealSlot(BaseModel):
    """Single planned recipe assignment inside a daily meal schedule."""

    slot_id: str = Field(default_factory=lambda: str(uuid4()))
    meal_type: MealType = Field(..., description="Meal timing category")
    recipe_id: str | None = Field(default=None, description="Vault recipe ID")
    custom_title: str | None = Field(default=None, description="Manual title")
    servings: float = Field(default=2.0, gt=0, description="Scaled servings")
    notes: str | None = Field(default=None, description="Prep notes")
    completed: bool = Field(default=False, description="Whether meal was cooked")


class DayPlan(BaseModel):
    """Single calendar day schedule containing structured meal slots."""

    date: str = Field(..., description="ISO calendar date (YYYY-MM-DD)")
    day_of_week: str = Field(..., description="Day name (e.g. monday)")
    slots: list[MealSlot] = Field(default_factory=list, description="Planned meals")


class WeeklyMealPlan(BaseModel):
    """Seven-day meal schedule covering Monday through Sunday."""

    id: str = Field(default_factory=lambda: str(uuid4()), alias="_id")
    owner_id: str = Field(default="default_user", description="Tenant isolation")
    week_start_date: str = Field(..., description="ISO Monday start (YYYY-MM-DD)")
    days: list[DayPlan] = Field(default_factory=list, description="Days array")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = {"populate_by_name": True}


class MealPlanCreateRequest(BaseModel):
    """Input payload to create or initialize a weekly schedule."""

    week_start_date: str = Field(..., description="ISO Monday start (YYYY-MM-DD)")
    days: list[DayPlan] = Field(default_factory=list, description="Initial days")


class MealPlanUpdateRequest(BaseModel):
    """Input payload to update an existing weekly schedule."""

    days: list[DayPlan] = Field(..., description="Full updated days array")


class MealSlotUpdateRequest(BaseModel):
    """Input payload to mutate or assign a single meal slot."""

    date: str = Field(..., description="Target ISO date (YYYY-MM-DD)")
    meal_type: MealType = Field(..., description="Target meal type")
    recipe_id: str | None = Field(default=None, description="Vault recipe ID")
    custom_title: str | None = Field(default=None, description="Custom title")
    servings: float = Field(default=2.0, gt=0, description="Serving count")
    notes: str | None = Field(default=None, description="Notes")
    completed: bool = Field(default=False, description="Completed flag")
