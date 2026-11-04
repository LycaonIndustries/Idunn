"""Data models for Cook AI and shopping list management.

This module defines models for recipe matching against active pantry stock,
ingredient substitution recommendations, generative pantry-to-plate proposals,
and quick-commerce shopping list generation.
"""

import re
from datetime import UTC, datetime
from urllib.parse import quote_plus

from pydantic import BaseModel, Field


class PantryMatchResult(BaseModel):
    """Result of evaluating a recipe against active pantry items.

    Calculates coverage ratio and highlights missing ingredients.
    """

    recipe_id: str = Field(description="Unique identifier of the recipe.")
    recipe_title: str = Field(description="Display title of the recipe.")
    coverage_percentage: float = Field(
        description="Percentage of ingredients present in the pantry (0 to 100)."
    )
    matched_ingredients: list[str] = Field(
        default_factory=list,
        description="Names of recipe ingredients available in pantry.",
    )
    missing_ingredients: list[str] = Field(
        default_factory=list,
        description="Names of recipe ingredients absent from pantry.",
    )
    expiry_urgency_score: int = Field(
        default=0,
        description="Priority boost based on expiring perishables used.",
    )
    can_cook_now: bool = Field(description="True when all essential ingredients are available.")


class SubstitutionSuggestion(BaseModel):
    """Culinary substitution recommendation for a missing ingredient.

    Draws strictly from verified in-stock pantry items.
    """

    missing_ingredient: str = Field(description="Ingredient absent from pantry.")
    substitute_item: str = Field(
        description="In-stock pantry ingredient recommended as substitute."
    )
    ratio_or_amount: str = Field(description="Replacement ratio or amount (e.g., '1:1 ratio').")
    reason: str = Field(description="Culinary rationale for the substitution.")
    in_stock: bool = Field(
        default=True,
        description="Indicates whether substitute is currently in pantry.",
    )


class PantryToPlateRequest(BaseModel):
    """User preferences for generating a meal from active pantry stock.

    Allows restricting by dietary preference, time limits, and servings.
    """

    dietary_preference: str | None = Field(
        default=None,
        description="Optional dietary constraint such as 'vegetarian' or 'jain'.",
    )
    max_prep_time_minutes: int | None = Field(
        default=None,
        description="Maximum desired preparation and cooking time in minutes.",
    )
    servings: int = Field(
        default=2,
        ge=1,
        description="Desired number of portions to yield.",
    )
    cuisine_hint: str | None = Field(
        default=None,
        description="Optional regional cuisine hint (e.g., 'South Indian').",
    )


class PantryToPlateResponse(BaseModel):
    """Generated recipe produced strictly from in-stock pantry items.

    Conforms to the application recipe schema with attribution to staples.
    """

    title: str = Field(description="Recipe title.")
    description: str = Field(description="Short recipe summary.")
    ingredients: list[dict] = Field(description="List of ingredients with item, amount, and unit.")
    steps: list[str] = Field(description="Sequential cooking steps.")
    prep_time_minutes: int = Field(description="Preparation time in minutes.")
    cook_time_minutes: int = Field(description="Cooking time in minutes.")
    servings: int = Field(default=2, description="Portions produced.")
    used_expiring_items: list[str] = Field(
        default_factory=list,
        description="Expiring pantry items consumed by this recipe.",
    )


class ShoppingListCreate(BaseModel):
    """Payload to add an item to the shopping list.

    Captures missing recipe ingredients or ad-hoc grocery additions.
    """

    name: str = Field(description="Item name to purchase.")
    quantity: float = Field(default=1.0, gt=0, description="Quantity to purchase.")
    unit: str = Field(default="item", description="Unit of measurement.")
    recipe_id: str | None = Field(
        default=None,
        description="Optional source recipe ID that requested this item.",
    )


class ShoppingListItem(BaseModel):
    """Persisted grocery shopping list item with quick-commerce links.

    Provides direct hand-off deep links to Blinkit, Zepto, and Instamart.
    """

    id: str = Field(description="Unique shopping list item identifier.")
    name: str = Field(description="Item name to purchase.")
    quantity: float = Field(default=1.0, gt=0, description="Quantity to purchase.")
    unit: str = Field(default="item", description="Unit of measurement.")
    recipe_id: str | None = Field(
        default=None,
        description="Optional source recipe ID that requested this item.",
    )
    is_purchased: bool = Field(
        default=False,
        description="Marks whether item was purchased.",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when item was added to the list.",
    )

    def get_quick_commerce_url(self, platform: str = "blinkit") -> str:
        """Build deep link for quick-commerce search.

        Strips numeric quantities and punctuation for clean grocery search.

        Args:
            platform: Platform name ('blinkit', 'zepto', or 'instamart').

        Returns:
            Sanitized URL string targeting grocery search query.
        """
        # Clean quantity and unit suffixes to optimize search accuracy.
        clean_name = re.sub(
            r"^\d+(\.\d+)?\s*(g|kg|ml|l|packet|piece|bunch|tbsp|tsp|katori)\s*",
            "",
            self.name,
            flags=re.IGNORECASE,
        ).strip()
        encoded = quote_plus(clean_name if clean_name else self.name)

        target = platform.lower().strip()
        if target == "zepto":
            return f"https://zepto.com/search?q={encoded}"
        if target == "instamart":
            return f"https://www.swiggy.com/instamart/search?query={encoded}"
        return f"https://blinkit.com/s/?q={encoded}"


class ShoppingList(BaseModel):
    """Aggregate shopping list containing items and total count.

    Used by API clients to render grocery shopping view.
    """

    items: list[ShoppingListItem] = Field(
        default_factory=list,
        description="Collection of shopping list items.",
    )
    total_count: int = Field(
        default=0,
        description="Total number of items in shopping list.",
    )
