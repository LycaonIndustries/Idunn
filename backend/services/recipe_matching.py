"""Algorithmic recipe matching and FEFO ranking service for Iðunn Kitchen OS.

Evaluates recipe ingredient requirements against active pantry stock deterministically.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime

from backend.models.cook_ai import PantryMatchResult
from backend.models.inventory import Item
from backend.models.recipe import Recipe

# Synonym map normalizing regional Hindi and English culinary names.
REGIONAL_SYNONYMS: dict[str, set[str]] = {
    "coriander": {"coriander", "coriander leaves", "dhania", "cilantro", "fresh coriander"},
    "cumin": {"cumin", "cumin seeds", "jeera", "zeera"},
    "turmeric": {"turmeric", "turmeric powder", "haldi"},
    "mustard seeds": {"mustard seeds", "rai", "sarson"},
    "fenugreek": {"fenugreek", "methi", "kasuri methi"},
    "curd": {"curd", "dahi", "yogurt", "plain yogurt"},
    "ginger": {"ginger", "adrak", "fresh ginger"},
    "garlic": {"garlic", "lehsun", "fresh garlic"},
    "green chilli": {"green chilli", "green chili", "hari mirch"},
    "red chilli powder": {"red chilli powder", "red chili powder", "lal mirch"},
    "asafoetida": {"asafoetida", "hing", "heeng"},
    "cardamom": {"cardamom", "elaichi", "green cardamom"},
    "clove": {"clove", "laung", "lavang"},
    "cinnamon": {"cinnamon", "dalchini"},
    "paneer": {"paneer", "cottage cheese", "indian cottage cheese"},
    "potato": {"potato", "potatoes", "aloo", "alu"},
    "onion": {"onion", "onions", "pyaz", "pyaaz"},
    "tomato": {"tomato", "tomatoes", "tamatar"},
    "toor dal": {"toor dal", "arhar dal", "pigeon pea", "tuvar dal"},
    "chana dal": {"chana dal", "bengal gram"},
    "moong dal": {"moong dal", "mung dal", "split green gram"},
}


def normalize_ingredient_name(name: str) -> str:
    """Normalize ingredient name for robust substring and synonym matching.

    Args:
        name: Raw ingredient string.

    Returns:
        Clean lowercased string with punctuation removed.
    """
    # Clean whitespace and non-alphanumeric noise to support fuzzy equality.
    cleaned = re.sub(r"[^\w\s]", " ", name.lower())
    return " ".join(cleaned.split())


def matches_inventory_item(recipe_ingredient: str, pantry_names: set[str]) -> bool:
    """Check whether recipe ingredient matches any active pantry item.

    Supports exact matching, substring overlap, and regional synonym expansion.

    Args:
        recipe_ingredient: Ingredient string from recipe schema.
        pantry_names: Set of normalized inventory item names in stock.

    Returns:
        True if item is available in pantry stock, otherwise False.
    """
    norm_rec = normalize_ingredient_name(recipe_ingredient)

    # Check direct name equality or word containment.
    for p_name in pantry_names:
        if norm_rec == p_name or norm_rec in p_name or p_name in norm_rec:
            return True

    # Search synonym dictionary for regional aliases.
    for synonyms in REGIONAL_SYNONYMS.values():
        if any(syn in norm_rec for syn in synonyms) and any(
            syn in p_name or p_name in syn for syn in synonyms for p_name in pantry_names
        ):
            return True

    return False


def calculate_fefo_urgency(matched_items: list[Item], now: datetime | None = None) -> float:
    """Calculate expiry urgency score for ingredients expiring within 72 hours.

    Args:
        matched_items: Active inventory items matching recipe requirements.
        now: Optional current datetime for deterministic unit testing.

    Returns:
        Float score representing urgency priority bonus.
    """
    if now is None:
        now = datetime.now(UTC)

    total_urgency = 0.0

    # Prioritize dishes consuming perishables close to spoilage.
    for item in matched_items:
        if item.expiry_date:
            expiry = item.expiry_date
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=UTC)

            hours_remaining = (expiry - now).total_seconds() / 3600.0
            if 0 <= hours_remaining <= 72.0:
                total_urgency += (72.0 - hours_remaining) / 10.0

    return round(total_urgency, 2)


class RecipeMatchingService:
    """Evaluates and ranks saved recipes against user inventory."""

    @staticmethod
    def match_recipe(
        recipe: Recipe,
        inventory: list[Item],
        now: datetime | None = None,
    ) -> PantryMatchResult:
        """Evaluate a single recipe against active pantry inventory.

        Args:
            recipe: Recipe document to inspect.
            inventory: Full list of current inventory items.
            now: Optional timestamp for expiry calculation.

        Returns:
            Computed PantryMatchResult instance.
        """
        # Exclude depleted items so only available stock is considered.
        active_items = [item for item in inventory if not item.consumed and item.quantity > 0]
        pantry_names = {normalize_ingredient_name(item.name) for item in active_items}

        matched_names: list[str] = []
        missing_names: list[str] = []
        matched_item_models: list[Item] = []

        # Compare required recipe ingredients against normalized pantry names.
        for ingredient in recipe.ingredients:
            if matches_inventory_item(ingredient.name, pantry_names):
                matched_names.append(ingredient.name)
                # Find matching Item model for expiry evaluation.
                norm_name = normalize_ingredient_name(ingredient.name)
                for item in active_items:
                    if norm_name in normalize_ingredient_name(item.name):
                        matched_item_models.append(item)
                        break
            else:
                missing_names.append(ingredient.name)

        total_req = len(recipe.ingredients)
        coverage = (len(matched_names) / total_req * 100.0) if total_req > 0 else 0.0
        urgency = calculate_fefo_urgency(matched_item_models, now=now)
        recipe_id = str(recipe.id or getattr(recipe, "_id", ""))

        return PantryMatchResult(
            recipe_id=recipe_id,
            recipe_title=recipe.title,
            coverage_percentage=round(coverage, 1),
            matched_ingredients=matched_names,
            missing_ingredients=missing_names,
            expiry_urgency_score=urgency,
            can_cook_now=(len(missing_names) == 0 and total_req > 0),
        )

    @classmethod
    def rank_recipes(
        cls,
        recipes: list[Recipe],
        inventory: list[Item],
        ready_only: bool = False,
        now: datetime | None = None,
    ) -> list[PantryMatchResult]:
        """Rank collection of recipes by pantry coverage and expiry priority.

        Args:
            recipes: Collection of recipes in vault.
            inventory: Active inventory items.
            ready_only: When true, filters out recipes with missing ingredients.
            now: Optional timestamp for deterministic evaluation.

        Returns:
            Ranked list of PantryMatchResult objects.
        """
        results: list[PantryMatchResult] = []

        # Evaluate pantry readiness for each stored recipe.
        for recipe in recipes:
            result = cls.match_recipe(recipe, inventory, now=now)
            if ready_only and not result.can_cook_now:
                continue
            results.append(result)

        # Sort recipes descending by coverage first, then FEFO urgency score.
        results.sort(
            key=lambda r: (r.coverage_percentage, r.expiry_urgency_score),
            reverse=True,
        )
        return results
