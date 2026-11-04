"""Generative Pantry-to-Plate chef service.

Produces bespoke Indian recipes designed strictly around verified in-stock
inventory items and household staples.
"""

from datetime import UTC, datetime
from typing import Any

from backend.models.cook_ai import PantryToPlateRequest, PantryToPlateResponse
from backend.models.inventory import Item


def generate_pantry_meal(
    pantry_items: list[Item],
    request: PantryToPlateRequest,
    provider: Any,
) -> PantryToPlateResponse:
    """Generate a structured meal recipe strictly using available pantry stock.

    Prioritizes expiring perishables to reduce food waste. Prohibits hallucinated
    ingredients, permitting only listed pantry items plus baseline staples
    (water, salt, cooking oil, black pepper).

    Args:
        pantry_items: Collection of pantry items in stock.
        request: Meal generation parameters and dietary constraints.
        provider: AI provider implementing structured content generation.

    Returns:
        PantryToPlateResponse containing the generated recipe proposal.

    Raises:
        ValueError: If active pantry inventory is completely empty.
    """
    # Exclude consumed items from recipe candidate inventory.
    active = [item for item in pantry_items if not item.consumed]
    if not active:
        raise ValueError("Pantry has no active items to cook with")

    now = datetime.now(UTC)
    expiring_soon: list[str] = []
    all_names: list[str] = []

    # Detect ingredients expiring within 3 days for priority usage.
    for item in active:
        all_names.append(f"{item.name} ({item.quantity} {item.unit})")
        if item.expiry_date:
            expiry_dt = item.expiry_date
            if expiry_dt.tzinfo is None:
                expiry_dt = expiry_dt.replace(tzinfo=UTC)
            if (expiry_dt - now).total_seconds() <= 3.0 * 86400.0:
                expiring_soon.append(item.name)

    expiring_str = ", ".join(expiring_soon) if expiring_soon else "None"
    items_str = ", ".join(all_names)

    # Build prompt enforcing strict inventory constraint.
    prompt = (
        "You are an expert Indian chef designing a home meal from available kitchen stock.\n\n"
        "CRITICAL CONSTRAINT: You must ONLY use ingredients from the active pantry list below, "
        "plus basic household staples (water, salt, cooking oil, black pepper).\n"
        "Do NOT introduce any unlisted ingredients.\n\n"
        f"Active Pantry Items: {items_str}\n"
        f"Expiring Soon (prioritize using these first): {expiring_str}\n\n"
        f"Dietary Constraint: {request.dietary_preference or 'None'}\n"
        f"Desired Servings: {request.servings}\n"
        f"Max Prep Time: {request.max_prep_time_minutes or 'Flexible'} minutes\n"
        f"Regional Cuisine Hint: {request.cuisine_hint or 'Indian Home Cooking'}\n\n"
        "Generate a structured JSON response with title, description, ingredients, "
        "steps, prep_time_minutes, cook_time_minutes, servings, and used_expiring_items."
    )

    # Invoke structured generation from configured AI provider.
    raw_response = provider.generate_structured_content(prompt)
    if not raw_response or not isinstance(raw_response, dict):
        raise ValueError("AI provider failed to generate a valid recipe proposal")

    return PantryToPlateResponse(
        title=raw_response.get("title", "Pantry Surprise"),
        description=raw_response.get("description", "Created from active pantry stock"),
        ingredients=raw_response.get("ingredients", []),
        steps=raw_response.get("steps", []),
        prep_time_minutes=int(raw_response.get("prep_time_minutes", 15)),
        cook_time_minutes=int(raw_response.get("cook_time_minutes", 20)),
        servings=int(raw_response.get("servings", request.servings)),
        used_expiring_items=raw_response.get("used_expiring_items", expiring_soon),
    )
