"""Cook AI API endpoints for Iðunn Kitchen OS.

Exposes pantry recipe matching, substitutions, and generative pantry-to-plate chef.
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.config import settings
from backend.db import get_db
from backend.models.cook_ai import (
    PantryMatchResult,
    PantryToPlateRecipe,
    PantryToPlateRequest,
    SubstitutionQueryRequest,
    SubstitutionSuggestion,
)
from backend.models.inventory import Item
from backend.models.recipe import Recipe
from backend.services.pantry_to_plate import PantryToPlateService
from backend.services.recipe_matching import RecipeMatchingService
from backend.services.substitution_engine import SubstitutionEngine

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


@router.post(
    "/substitutions",
    response_model=list[SubstitutionSuggestion],
    summary="Get culinary substitution suggestions for an ingredient",
)
async def get_substitutions(
    request: SubstitutionQueryRequest,
    db=Depends(get_db),
) -> list[SubstitutionSuggestion]:
    """Retrieve functional substitutions prioritizing ingredients in pantry inventory.

    Args:
        request: SubstitutionQueryRequest containing the ingredient name.
        db: Database session dependency.

    Returns:
        List of SubstitutionSuggestion sorted with in-stock pantry items first.
    """
    logger.info("Evaluating substitution query for ingredient: %s", request.ingredient)

    # Fetch active unconsumed inventory to identify pantry-ready replacements.
    raw_inventory = await db.inventory.find({"consumed": False}).to_list(length=1000)
    inventory: list[Item] = []
    for doc in raw_inventory:
        doc["_id"] = str(doc.get("_id", ""))
        inventory.append(Item.model_validate(doc))

    # Execute deterministic substitution match against pantry stock.
    return SubstitutionEngine.find_pantry_substitutions(request.ingredient, inventory)


@router.post(
    "/pantry-to-plate",
    response_model=PantryToPlateRecipe,
    summary="Generate custom recipe on-the-fly from active pantry inventory",
)
async def generate_pantry_recipe(
    request: PantryToPlateRequest,
    db=Depends(get_db),
) -> PantryToPlateRecipe:
    """Explicit user-triggered action to synthesize an inventive recipe from current pantry.

    Args:
        request: PantryToPlateRequest parameters.
        db: Database session dependency.

    Returns:
        PantryToPlateRecipe containing customized recipe.
    """
    logger.info("Generating pantry-to-plate recipe for %s servings", request.servings)

    # Fetch active unconsumed inventory items.
    query: dict[str, object] = {"consumed": False}
    if request.selected_item_ids:
        query["_id"] = {"$in": request.selected_item_ids}

    raw_inventory = await db.inventory.find(query).to_list(length=1000)
    inventory: list[Item] = []
    for doc in raw_inventory:
        doc["_id"] = str(doc.get("_id", ""))
        inventory.append(Item.model_validate(doc))

    # Guard against synthesizing with zero pantry ingredients.
    if not inventory:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No ingredients available in pantry to generate a recipe.",
        )

    service = PantryToPlateService(settings)
    return await service.generate_recipe(request, inventory)
