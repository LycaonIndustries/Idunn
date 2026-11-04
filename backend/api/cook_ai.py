"""Cook AI API endpoints for Iðunn Kitchen OS.

Exposes algorithmic pantry recipe matching and vault queries.
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from backend.db import get_db
from backend.models.cook_ai import PantryMatchResult
from backend.models.inventory import Item
from backend.models.recipe import Recipe
from backend.services.recipe_matching import RecipeMatchingService

logger = logging.getLogger("backend.api.cook_ai")

router = APIRouter(prefix="/api/v1/cook-ai", tags=["cook-ai"])


@router.get(
    "/what-can-i-cook",
    response_model=list[PantryMatchResult],
    summary="Rank saved vault recipes by pantry coverage",
)
async def what_can_i_cook(
    ready_only: Annotated[
        bool,
        Query(description="When True, returns only recipes with 100% ingredients in stock."),
    ] = False,
    db=Depends(get_db),
) -> list[PantryMatchResult]:
    """Retrieve saved recipes ranked by pantry availability and FEFO urgency.

    Args:
        ready_only: Filter flag restricting results to 100% satisfied recipes.
        db: Database session dependency.

    Returns:
        List of PantryMatchResult items ordered descending by readiness.
    """
    logger.info("Evaluating what-can-i-cook query (ready_only=%s)", ready_only)

    # Fetch stored recipes from database.
    raw_recipes = await db.recipes.find({}).to_list(length=1000)
    recipes: list[Recipe] = []
    for doc in raw_recipes:
        doc["_id"] = str(doc.get("_id", ""))
        recipes.append(Recipe.model_validate(doc))

    # Fetch active unconsumed pantry inventory.
    raw_inventory = await db.inventory.find({"consumed": False}).to_list(length=1000)
    inventory: list[Item] = []
    for doc in raw_inventory:
        doc["_id"] = str(doc.get("_id", ""))
        inventory.append(Item.model_validate(doc))

    # Rank recipes deterministically without LLM calls.
    return RecipeMatchingService.rank_recipes(recipes, inventory, ready_only=ready_only)
