"""Shopping list models for Iðunn Kitchen OS."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from urllib.parse import quote

from pydantic import BaseModel, Field


class AisleCategory(StrEnum):
    """Supermarket and grocery store aisle categories."""

    PRODUCE = "Produce"
    DAIRY = "Dairy"
    SPICES = "Spices"
    GRAINS = "Grains"
    STAPLES = "Staples"
    OTHER = "Other"


def generate_quick_commerce_links(item_name: str) -> dict[str, str]:
    """Generate search URLs for Indian quick-commerce providers.

    Args:
        item_name: Product or ingredient name to search.

    Returns:
        Dictionary mapping provider key to search URL string.
    """
    encoded = quote(item_name.strip())
    return {
        "blinkit": f"https://blinkit.com/s/?q={encoded}",
        "zepto": f"https://www.zeptonow.com/search?q={encoded}",
        "instamart": f"https://www.swiggy.com/instamart/search?custom_back=true&query={encoded}",
    }


class ShoppingListItemCreate(BaseModel):
    """Payload to create a single item on the shopping list."""

    name: str = Field(min_length=1, max_length=120, description="Display name of ingredient.")
    quantity: float = Field(default=1.0, gt=0, description="Required amount.")
    unit: str = Field(default="piece", max_length=20, description="Measurement unit.")
    source_recipe_id: str | None = Field(default=None, description="Optional recipe document ID.")


class ShoppingListBatchCreate(BaseModel):
    """Payload to add multiple missing ingredients simultaneously."""

    items: list[ShoppingListItemCreate] = Field(min_length=1, description="List of items to add.")


class ShoppingListItemUpdate(BaseModel):
    """Payload to modify item properties or toggle checked state."""

    name: str | None = Field(default=None, min_length=1, max_length=120)
    quantity: float | None = Field(default=None, gt=0)
    unit: str | None = Field(default=None, max_length=20)
    checked: bool | None = Field(default=None)


class ShoppingListItem(BaseModel):
    """Shopping list item document schema with pre-computed deep links."""

    id: str = Field(alias="_id", description="Document identifier.")
    name: str = Field(description="Display name.")
    quantity: float = Field(default=1.0, description="Quantity.")
    unit: str = Field(default="piece", description="Unit.")
    checked: bool = Field(default=False, description="Purchased status.")
    source_recipe_id: str | None = Field(default=None, description="Associated recipe.")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    quick_links: dict[str, str] = Field(
        default_factory=dict,
        description="Search deep links to Blinkit, Zepto, and Instamart.",
    )


class AggregatedShoppingItem(BaseModel):
    """Aggregated ingredient requirement with pantry deduction and aisle mapping."""

    name: str = Field(description="Normalized ingredient name")
    required_quantity: float = Field(description="Total amount required across meals")
    in_stock_quantity: float = Field(default=0.0, description="Available pantry stock")
    gap_quantity: float = Field(description="Missing amount needed to purchase")
    unit: str = Field(description="Measurement unit")
    aisle: AisleCategory = Field(default=AisleCategory.OTHER, description="Store aisle")
    recipes: list[str] = Field(default_factory=list, description="Source recipe titles")
    quick_links: dict[str, str] = Field(default_factory=dict, description="Quick commerce links")


class PantryGapResponse(BaseModel):
    """Response bundle returning pantry gap analysis for a meal plan."""

    plan_id: str = Field(description="Target weekly meal plan identifier")
    week_start_date: str = Field(description="Monday start date (YYYY-MM-DD)")
    gap_items: list[AggregatedShoppingItem] = Field(description="Ingredients with stock gaps")
    total_gap_count: int = Field(description="Count of missing ingredients")
    added_to_shopping_list: bool = Field(default=False, description="Added to live shopping list")
