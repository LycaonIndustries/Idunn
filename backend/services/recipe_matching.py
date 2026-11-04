"""Recipe matching and ranking engine against pantry inventory.

This module evaluates saved recipes against active pantry stock to compute
ingredient coverage, missing items, and FEFO expiry urgency bonuses.
"""

import re
from datetime import UTC, datetime

from backend.models.cook_ai import PantryMatchResult
from backend.models.inventory import Item
from backend.models.recipe import Recipe

# Grouped synonym clusters for Indian and Western pantry terminology.
INDIAN_SYNONYM_CLUSTERS: list[set[str]] = [
    {"spinach", "palak", "keerai"},
    {"cottage cheese", "paneer"},
    {"garlic", "lahsun", "poondu"},
    {"onion", "pyaz", "vengayam", "kanda"},
    {"potato", "aloo", "batata", "urulaikizhangu"},
    {"tomato", "tamatar", "thakkali"},
    {"coriander", "coriander leaves", "cilantro", "dhania", "kothmir"},
    {"cumin", "cumin seeds", "jeera"},
    {"turmeric", "haldi"},
    {"ginger", "adrak", "inji"},
    {"green chilli", "hari mirch", "chilli", "chillies"},
    {"mustard seeds", "rai", "sarson"},
    {"curd", "dahi", "yogurt"},
    {"butter", "makhan"},
    {"ghee", "clarified butter"},
    {"fenugreek", "methi", "kasuri methi"},
    {"pigeon pea", "toor dal", "tuvar dal", "arhar dal"},
    {"green gram", "moong dal", "mung dal"},
    {"red lentil", "masoor dal"},
    {"chickpeas", "chana", "chole", "kabuli chana"},
    {"peas", "green peas", "matar"},
    {"cauliflower", "gobi", "phool gobi"},
    {"capsicum", "shimla mirch", "bell pepper"},
    {"rice", "chawal", "basmati"},
    {"wheat flour", "atta", "gehu ka atta"},
    {"gram flour", "besan"},
    {"semolina", "sooji", "suji", "rava"},
    {"dal", "lentils", "pulses"},
]


def _clean_token(text: str) -> str:
    """Normalize ingredient text by stripping numbers, units, and symbols.

    Args:
        text: Raw ingredient name string.

    Returns:
        Lower-cased alphanumeric string with clean spacing.
    """
    # Remove digits and common measurement noise.
    cleaned = re.sub(
        r"\b(\d+(\.\d+)?)\s*(g|kg|ml|l|packet|piece|bunch|tbsp|tsp|cup|katori)\b",
        "",
        text,
        flags=re.IGNORECASE,
    )
    # Retain standard letters and spaces.
    cleaned = re.sub(r"[^a-zA-Z\s]", " ", cleaned)
    return " ".join(cleaned.lower().split())


def _ingredients_match(recipe_ingredient: str, pantry_item_name: str) -> bool:
    """Check if recipe ingredient matches pantry item name.

    Matches direct names, substrings, or grouped regional synonyms.

    Args:
        recipe_ingredient: Ingredient string from recipe schema.
        pantry_item_name: Name of active pantry inventory item.

    Returns:
        True if item names are culinary equivalents.
    """
    norm_rec = _clean_token(recipe_ingredient)
    norm_pan = _clean_token(pantry_item_name)

    # Fast path for direct match or substring containment.
    if norm_rec == norm_pan or norm_rec in norm_pan or norm_pan in norm_rec:
        return True

    # Check clustered regional synonym tables.
    for cluster in INDIAN_SYNONYM_CLUSTERS:
        rec_in = any(syn in norm_rec for syn in cluster)
        pan_in = any(syn in norm_pan for syn in cluster)
        if rec_in and pan_in:
            return True

    return False


def calculate_recipe_pantry_match(recipe: Recipe, pantry_items: list[Item]) -> PantryMatchResult:
    """Evaluate a single recipe against active pantry inventory.

    Computes ingredient coverage ratio, lists missing items, and calculates
    FEFO expiry urgency bonus.

    Args:
        recipe: Target recipe model to evaluate.
        pantry_items: Active pantry items available in inventory.

    Returns:
        PantryMatchResult containing match statistics.
    """
    # Exclude consumed items from candidate pantry pool.
    active_items = [item for item in pantry_items if not item.consumed]

    matched_names: list[str] = []
    missing_names: list[str] = []
    expiry_score = 0
    now = datetime.now(UTC)

    recipe_ingredients = recipe.ingredients or []

    # Iterate through all required recipe ingredients.
    for ing in recipe_ingredients:
        if hasattr(ing, "name"):
            ing_name = ing.name
        elif isinstance(ing, dict):
            ing_name = ing.get("name") or ing.get("item", "")
        else:
            ing_name = str(ing)
        matched_item: Item | None = None

        # Search active inventory for a matching item.
        for p_item in active_items:
            if _ingredients_match(ing_name, p_item.name):
                matched_item = p_item
                break

        if matched_item is not None:
            matched_names.append(ing_name)
            # Reward recipe for using items near expiry.
            if matched_item.expiry_date:
                expiry_dt = matched_item.expiry_date
                if expiry_dt.tzinfo is None:
                    expiry_dt = expiry_dt.replace(tzinfo=UTC)
                days_left = (expiry_dt - now).total_seconds() / 86400.0
                if days_left <= 3.0:
                    expiry_score += 20
                elif days_left <= 7.0:
                    expiry_score += 10
        else:
            missing_names.append(ing_name)

    total_count = len(recipe_ingredients)
    coverage = (len(matched_names) / total_count * 100.0) if total_count > 0 else 100.0

    return PantryMatchResult(
        recipe_id=recipe.id,
        recipe_title=recipe.title,
        coverage_percentage=round(coverage, 1),
        matched_ingredients=matched_names,
        missing_ingredients=missing_names,
        expiry_urgency_score=expiry_score,
        can_cook_now=(len(missing_names) == 0),
    )


def rank_recipes_for_pantry(
    recipes: list[Recipe],
    pantry_items: list[Item],
    ready_only: bool = False,
    max_missing: int | None = None,
) -> list[PantryMatchResult]:
    """Rank multiple recipes against pantry items.

    Orders recipes by readiness, expiring perishables utilized, and coverage.

    Args:
        recipes: Candidate recipes to evaluate.
        pantry_items: Active pantry items in stock.
        ready_only: When True, excludes recipes missing any ingredients.
        max_missing: Optional cap on allowable missing ingredients.

    Returns:
        List of match results sorted from highest to lowest suitability.
    """
    results: list[PantryMatchResult] = []

    # Score each candidate recipe.
    for rec in recipes:
        match = calculate_recipe_pantry_match(rec, pantry_items)
        # Apply readiness filters if requested.
        if ready_only and not match.can_cook_now:
            continue
        if max_missing is not None and len(match.missing_ingredients) > max_missing:
            continue
        results.append(match)

    # Prioritize recipes that can be cooked immediately, then expiring items.
    results.sort(
        key=lambda r: (
            1 if r.can_cook_now else 0,
            r.expiry_urgency_score,
            r.coverage_percentage,
        ),
        reverse=True,
    )

    return results
