"""API endpoints for Cook AI and Shopping List features.

Provides routes for recipe ranking against active pantry stock, in-stock
substitution assistance, generative pantry-to-plate meal proposals,
and shopping list management.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from backend.config import settings
from backend.db import COLLECTION_ITEMS, COLLECTION_RECIPES, get_db
from backend.models.cook_ai import (
    PantryMatchResult,
    PantryToPlateRequest,
    PantryToPlateResponse,
    ShoppingList,
    ShoppingListCreate,
    ShoppingListItem,
    SubstitutionSuggestion,
)
from backend.models.inventory import Item
from backend.models.recipe import Recipe
from backend.services.pantry_to_plate import generate_pantry_meal
from backend.services.recipe_matching import rank_recipes_for_pantry
from backend.services.shopping_list import ShoppingListService
from backend.services.substitution_engine import find_substitutes

router = APIRouter(tags=["cook_ai"])


def get_ai_provider() -> Any:
    """Resolve active AI provider for structured culinary generation.

    Returns None if no API keys are configured, preventing live network calls.

    Returns:
        Structured provider instance or None.
    """
    # Safeguard against accidental network calls during testing or unconfigured runs.
    if settings.gemini_api_key:
        from backend.services.recipe_providers import GeminiRecipeExtractor

        return GeminiRecipeExtractor(settings.gemini_api_key)
    return None


class MissingIngredientRequest(BaseModel):
    """Payload to query in-stock culinary substitutions."""

    missing_ingredient: str = Field(
        ..., min_length=1, description="Missing recipe ingredient name."
    )


class PatchPurchasedRequest(BaseModel):
    """Payload to update purchased state of a shopping list item."""

    is_purchased: bool = Field(..., description="Target purchase state.")


def _doc_to_item(doc: dict) -> Item:
    """Format MongoDB document into validated Item model.

    Args:
        doc: Raw MongoDB inventory document.

    Returns:
        Validated Item instance.
    """
    doc["_id"] = str(doc.get("_id") or doc.get("id"))
    return Item.model_validate(doc)


def _doc_to_recipe(doc: dict) -> Recipe:
    """Format MongoDB document into validated Recipe model.

    Args:
        doc: Raw MongoDB recipe document.

    Returns:
        Validated Recipe instance.
    """
    doc["_id"] = str(doc.get("_id") or doc.get("id"))
    return Recipe.model_validate(doc)


@router.post("/api/v1/cook-ai/what-can-i-cook", response_model=list[PantryMatchResult])
async def what_can_i_cook(
    ready_only: bool = Query(False, description="Filter only 100% ready recipes"),
    max_missing: int | None = Query(None, description="Max missing ingredients allowable"),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> list[PantryMatchResult]:
    """Rank recipes by active pantry coverage, expiring items, and readiness.

    Args:
        ready_only: When true, only returns recipes that can be cooked immediately.
        max_missing: Optional cap on allowable missing ingredients.
        db: Injected database handle.

    Returns:
        List of PantryMatchResult sorted from most ready to least ready.
    """
    # Fetch active non-consumed pantry items.
    item_docs = await db[COLLECTION_ITEMS].find({"consumed": False}).to_list(1000)
    pantry_items = [_doc_to_item(doc) for doc in item_docs]

    # Fetch stored recipe library.
    recipe_docs = await db[COLLECTION_RECIPES].find().to_list(1000)
    recipes = [_doc_to_recipe(doc) for doc in recipe_docs]

    return rank_recipes_for_pantry(
        recipes=recipes,
        pantry_items=pantry_items,
        ready_only=ready_only,
        max_missing=max_missing,
    )


@router.post(
    "/api/v1/cook-ai/substitutions",
    response_model=SubstitutionSuggestion | None,
)
async def get_substitutions(
    request: MissingIngredientRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    provider: Any = Depends(get_ai_provider),
) -> SubstitutionSuggestion | None:
    """Find in-stock culinary substitution for an absent recipe ingredient.

    Args:
        request: MissingIngredientRequest containing missing ingredient name.
        db: Injected database handle.
        provider: Injected AI provider handle.

    Returns:
        SubstitutionSuggestion if an in-stock substitute is verified, else None.
    """
    # Load available pantry items.
    item_docs = await db[COLLECTION_ITEMS].find({"consumed": False}).to_list(1000)
    pantry_items = [_doc_to_item(doc) for doc in item_docs]

    return find_substitutes(
        missing_ingredient=request.missing_ingredient,
        pantry_items=pantry_items,
        provider=provider,
    )


@router.post(
    "/api/v1/cook-ai/pantry-to-plate",
    response_model=PantryToPlateResponse,
)
async def cook_pantry_to_plate(
    request: PantryToPlateRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    provider: Any = Depends(get_ai_provider),
) -> PantryToPlateResponse:
    """Generate a custom recipe strictly from currently available kitchen stock.

    Args:
        request: PantryToPlateRequest specifying dietary filters and servings.
        db: Injected database handle.
        provider: Injected AI provider handle.

    Returns:
        Generated PantryToPlateResponse conforming to recipe schema.

    Raises:
        HTTPException: If provider is missing or pantry is empty.
    """
    if provider is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI Provider is not configured. Add Gemini API key in settings.",
        )

    item_docs = await db[COLLECTION_ITEMS].find({"consumed": False}).to_list(1000)
    pantry_items = [_doc_to_item(doc) for doc in item_docs]

    try:
        return generate_pantry_meal(
            pantry_items=pantry_items,
            request=request,
            provider=provider,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# --- Shopping List Endpoints ---


@router.get("/api/v1/shopping-list", response_model=ShoppingList)
async def get_shopping_list(
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> ShoppingList:
    """Retrieve full shopping list with active and purchased grocery items.

    Args:
        db: Injected database handle.

    Returns:
        ShoppingList containing item collection and count.
    """
    service = ShoppingListService(db)
    return await service.get_all_items()


@router.post(
    "/api/v1/shopping-list",
    response_model=ShoppingListItem,
    status_code=status.HTTP_201_CREATED,
)
async def add_shopping_list_item(
    payload: ShoppingListCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> ShoppingListItem:
    """Add a single item to the shopping list.

    Args:
        payload: ShoppingListCreate payload.
        db: Injected database handle.

    Returns:
        Created ShoppingListItem.
    """
    service = ShoppingListService(db)
    return await service.add_item(payload)


@router.post(
    "/api/v1/shopping-list/batch",
    response_model=list[ShoppingListItem],
    status_code=status.HTTP_201_CREATED,
)
async def add_shopping_list_batch(
    payloads: list[ShoppingListCreate],
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> list[ShoppingListItem]:
    """Add a batch of items to the shopping list.

    Args:
        payloads: List of ShoppingListCreate payloads.
        db: Injected database handle.

    Returns:
        List of created ShoppingListItem instances.
    """
    service = ShoppingListService(db)
    return await service.add_batch(payloads)


@router.patch("/api/v1/shopping-list/{item_id}", response_model=ShoppingListItem)
async def update_shopping_list_item(
    item_id: str,
    payload: PatchPurchasedRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> ShoppingListItem:
    """Toggle purchased status of a shopping list item.

    Args:
        item_id: Target item identifier.
        payload: PatchPurchasedRequest payload.
        db: Injected database handle.

    Returns:
        Updated ShoppingListItem.

    Raises:
        HTTPException: If item not found.
    """
    service = ShoppingListService(db)
    updated = await service.update_purchased(item_id, payload.is_purchased)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shopping list item '{item_id}' not found",
        )
    return updated


@router.delete("/api/v1/shopping-list/{item_id}")
async def delete_shopping_list_item(
    item_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict[str, str]:
    """Delete an item from the shopping list.

    Args:
        item_id: Target item identifier.
        db: Injected database handle.

    Returns:
        Confirmation dictionary.

    Raises:
        HTTPException: If item not found.
    """
    service = ShoppingListService(db)
    deleted = await service.delete_item(item_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shopping list item '{item_id}' not found",
        )
    return {"status": "deleted"}


@router.post("/api/v1/shopping-list/clear-purchased")
async def clear_purchased_shopping_items(
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict[str, int]:
    """Remove all marked-as-purchased items from the shopping list.

    Args:
        db: Injected database handle.

    Returns:
        Count of cleared items.
    """
    service = ShoppingListService(db)
    count = await service.clear_purchased()
    return {"cleared_count": count}
