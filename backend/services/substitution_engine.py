"""Strict in-stock substitution engine for Indian cooking.

This module resolves missing recipe ingredients by checking active pantry stock
against canonical culinary substitution rules or an AI provider fallback.
"""

from typing import Any

from backend.models.cook_ai import SubstitutionSuggestion
from backend.models.inventory import Item
from backend.services.recipe_matching import _ingredients_match

# Curated substitution table mapping missing ingredients to in-stock alternatives.
INDIAN_CULINARY_SUBSTITUTIONS: dict[str, list[dict[str, Any]]] = {
    "sour cream": [
        {
            "candidates": ["curd", "dahi", "yogurt"],
            "ratio": "1:1 ratio, whisked until smooth",
            "reason": "Whisked curd provides identical lactic acidity and creaminess in gravies.",
        },
        {
            "candidates": ["malai", "fresh cream"],
            "ratio": "1:1 ratio with 1 tsp lemon juice",
            "reason": "Provides full dairy fat richness with balancing citrus acidity.",
        },
    ],
    "heavy cream": [
        {
            "candidates": ["malai", "fresh cream", "cream"],
            "ratio": "1:1 ratio",
            "reason": "Homemade malai replicates restaurant-style gravy richness.",
        },
        {
            "candidates": ["cashew", "kaju"],
            "ratio": "Soaked and ground cashew paste (1:1 ratio)",
            "reason": "Nut paste lends silkiness and body to rich gravies.",
        },
    ],
    "kasuri methi": [
        {
            "candidates": ["fresh methi", "fenugreek leaves", "methi"],
            "ratio": "2x volume of fresh leaves sauteed",
            "reason": "Fresh fenugreek leaves deliver the characteristic herbal aroma.",
        },
        {
            "candidates": ["celery leaves", "coriander"],
            "ratio": "1:1 fresh chopped garnish",
            "reason": "Provides fresh herbal aroma when dried fenugreek is absent.",
        },
    ],
    "lemon juice": [
        {
            "candidates": ["amchur", "dry mango powder", "amchur powder"],
            "ratio": "1/2 tsp amchur per 1 tbsp lemon juice",
            "reason": "Amchur contributes sharp, clean fruit sourness without extra liquid.",
        },
        {
            "candidates": ["tamarind", "imli"],
            "ratio": "1/2 tsp tamarind paste per 1 tbsp lemon juice",
            "reason": "Imli offers balanced sweet-tart acidity.",
        },
    ],
    "tomato puree": [
        {
            "candidates": ["tomato", "tamatar"],
            "ratio": "2 fresh tomatoes pureed per 3 tbsp paste",
            "reason": "Fresh blended tomatoes provide natural sweetness and acidity.",
        },
    ],
    "paneer": [
        {
            "candidates": ["tofu"],
            "ratio": "1:1 ratio cubed and lightly pan-seared",
            "reason": "Firm tofu absorbs spiced gravies and matches paneer bite.",
        },
    ],
    "toor dal": [
        {
            "candidates": ["masoor dal", "red lentil"],
            "ratio": "1:1 ratio",
            "reason": "Masoor dal cooks quickly with a velvety texture matching sambar/dal tadka.",
        },
        {
            "candidates": ["moong dal", "mung dal"],
            "ratio": "1:1 ratio",
            "reason": "Moong dal breaks down into a light, comforting dal consistency.",
        },
    ],
}


def find_substitutes(
    missing_ingredient: str,
    pantry_items: list[Item],
    provider: Any = None,
) -> SubstitutionSuggestion | None:
    """Find in-stock culinary substitute for a missing ingredient.

    Checks curated knowledge base first, then delegates to AI provider.
    Enforces that candidate must be actively available in the user's pantry.

    Args:
        missing_ingredient: Name of absent ingredient.
        pantry_items: List of pantry inventory items.
        provider: Optional AI multimodal or structured LLM provider.

    Returns:
        SubstitutionSuggestion if an in-stock substitute is found, else None.
    """
    # Filter active non-consumed inventory items.
    active = [item for item in pantry_items if not item.consumed]
    norm_missing = missing_ingredient.lower().strip()

    # Step 1: Check curated Indian culinary substitution rules.
    for key, options in INDIAN_CULINARY_SUBSTITUTIONS.items():
        if key in norm_missing or norm_missing in key:
            for option in options:
                candidates: list[str] = option["candidates"]
                # Look for a candidate in the active pantry.
                for item in active:
                    if any(_ingredients_match(cand, item.name) for cand in candidates):
                        return SubstitutionSuggestion(
                            missing_ingredient=missing_ingredient,
                            substitute_item=item.name,
                            ratio_or_amount=option["ratio"],
                            reason=option["reason"],
                            in_stock=True,
                        )

    # Step 2: Use AI provider fallback if configured and rule table misses.
    if provider is not None and active:
        pantry_names = [item.name for item in active]
        prompt = (
            f"You are an expert Indian chef. The recipe requires '{missing_ingredient}', "
            f"which is missing. The user's pantry ONLY contains: {pantry_names}. "
            f"Propose a valid substitution STRICTLY from the user's pantry list. "
            f"If none of these items can substitute '{missing_ingredient}', reply None."
        )

        try:
            # Request structured JSON matching substitution schema.
            raw = provider.generate_structured_content(prompt)
            if raw and isinstance(raw, dict):
                sub_item = raw.get("substitute_item", "")
                # Enforce that proposed substitute is verified in active pantry.
                if any(_ingredients_match(sub_item, p.name) for p in active):
                    return SubstitutionSuggestion(
                        missing_ingredient=missing_ingredient,
                        substitute_item=sub_item,
                        ratio_or_amount=raw.get("ratio_or_amount", "1:1 ratio adjusted to taste"),
                        reason=raw.get("reason", "Culinary substitution from pantry"),
                        in_stock=True,
                    )
        except Exception:
            # Fall back cleanly if provider fails or times out.
            return None

    return None
