"""Shopping list API endpoints for Iðunn Kitchen OS."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.db import get_db
from backend.models.shopping import (
    PantryGapResponse,
    ShoppingListBatchCreate,
    ShoppingListItem,
    ShoppingListItemCreate,
    ShoppingListItemUpdate,
    generate_quick_commerce_links,
)
from backend.services.gap_list import generate_pantry_gap_shopping_list

logger = logging.getLogger("backend.api.shopping_list")

router = APIRouter(prefix="/api/v1/shopping-list", tags=["shopping-list"])


@router.get(
    "",
    response_model=list[ShoppingListItem],
    summary="Get all shopping list items",
)
async def get_shopping_list(db=Depends(get_db)) -> list[ShoppingListItem]:
    """Retrieve all shopping list items sorted with active items first.

    Args:
        db: Database session dependency.

    Returns:
        List of ShoppingListItem documents.
    """
    logger.info("Fetching shopping list items")
    # Query database and populate deep links for quick ordering.
    raw_items = await db.shopping_list.find({}).to_list(length=1000)
    items: list[ShoppingListItem] = []
    for doc in raw_items:
        doc["_id"] = str(doc.get("_id", ""))
        doc["quick_links"] = generate_quick_commerce_links(doc.get("name", ""))
        items.append(ShoppingListItem.model_validate(doc))

    # Keep unchecked pending items at top of list.
    return sorted(items, key=lambda x: (x.checked, -x.created_at.timestamp()))


@router.post(
    "/items",
    response_model=ShoppingListItem,
    status_code=status.HTTP_201_CREATED,
    summary="Add a single item to the shopping list",
)
async def add_shopping_item(
    payload: ShoppingListItemCreate,
    db=Depends(get_db),
) -> ShoppingListItem:
    """Insert a single item onto the shopping list.

    Args:
        payload: ShoppingListItemCreate input data.
        db: Database session dependency.

    Returns:
        Created ShoppingListItem document.
    """
    now = datetime.now(UTC)
    item_id = str(uuid4())
    doc = {
        "_id": item_id,
        "name": payload.name.strip(),
        "quantity": payload.quantity,
        "unit": payload.unit.strip(),
        "checked": False,
        "source_recipe_id": payload.source_recipe_id,
        "created_at": now,
        "updated_at": now,
    }

    # Persist item in database collection.
    await db.shopping_list.insert_one(doc)
    doc["quick_links"] = generate_quick_commerce_links(doc["name"])
    return ShoppingListItem.model_validate(doc)


@router.post(
    "/batch",
    response_model=list[ShoppingListItem],
    status_code=status.HTTP_201_CREATED,
    summary="Batch add ingredients to shopping list",
)
async def add_shopping_items_batch(
    payload: ShoppingListBatchCreate,
    db=Depends(get_db),
) -> list[ShoppingListItem]:
    """Insert multiple ingredients onto shopping list simultaneously.

    Args:
        payload: ShoppingListBatchCreate containing items array.
        db: Database session dependency.

    Returns:
        List of created ShoppingListItem documents.
    """
    now = datetime.now(UTC)
    docs = []
    for item in payload.items:
        item_id = str(uuid4())
        docs.append(
            {
                "_id": item_id,
                "name": item.name.strip(),
                "quantity": item.quantity,
                "unit": item.unit.strip(),
                "checked": False,
                "source_recipe_id": item.source_recipe_id,
                "created_at": now,
                "updated_at": now,
            }
        )

    # Insert batch into database if array is non-empty.
    if docs:
        await db.shopping_list.insert_many(docs)

    results: list[ShoppingListItem] = []
    for d in docs:
        d["quick_links"] = generate_quick_commerce_links(d["name"])
        results.append(ShoppingListItem.model_validate(d))
    return results


@router.patch(
    "/items/{item_id}",
    response_model=ShoppingListItem,
    summary="Update or toggle checked status of a shopping list item",
)
async def update_shopping_item(
    item_id: str,
    payload: ShoppingListItemUpdate,
    db=Depends(get_db),
) -> ShoppingListItem:
    """Update fields or toggle checked state of an item.

    Args:
        item_id: Shopping list document ID.
        payload: ShoppingListItemUpdate update fields.
        db: Database session dependency.

    Returns:
        Updated ShoppingListItem document.
    """
    # Fetch existing item to verify document existence.
    existing = await db.shopping_list.find_one({"_id": item_id})
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shopping list item {item_id} not found.",
        )

    updates: dict[str, object] = {"updated_at": datetime.now(UTC)}
    if payload.name is not None:
        updates["name"] = payload.name.strip()
    if payload.quantity is not None:
        updates["quantity"] = payload.quantity
    if payload.unit is not None:
        updates["unit"] = payload.unit.strip()
    if payload.checked is not None:
        updates["checked"] = payload.checked

    # Apply modified properties to database record.
    await db.shopping_list.update_one({"_id": item_id}, {"$set": updates})
    updated = await db.shopping_list.find_one({"_id": item_id})
    updated["_id"] = str(updated.get("_id", ""))
    updated["quick_links"] = generate_quick_commerce_links(updated.get("name", ""))
    return ShoppingListItem.model_validate(updated)


@router.delete(
    "/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an item from shopping list",
)
async def delete_shopping_item(item_id: str, db=Depends(get_db)) -> None:
    """Delete a shopping list item by document ID.

    Args:
        item_id: Shopping list item ID.
        db: Database session dependency.
    """
    # Remove record from database collection.
    result = await db.shopping_list.delete_one({"_id": item_id})
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shopping list item {item_id} not found.",
        )


@router.post(
    "/clear-purchased",
    summary="Remove all checked items from shopping list",
)
async def clear_purchased_items(db=Depends(get_db)) -> dict[str, int]:
    """Delete all items currently marked as checked.

    Args:
        db: Database session dependency.

    Returns:
        Dictionary containing deleted_count integer.
    """
    # Delete all items marked as purchased.
    res = await db.shopping_list.delete_many({"checked": True})
    return {"deleted_count": res.deleted_count}


@router.post(
    "/plan/{plan_id}/gap-analysis",
    response_model=PantryGapResponse,
    summary="Generate pantry gap shopping list from meal plan",
)
async def generate_plan_gap_shopping_list(
    plan_id: str,
    auto_add: bool = Query(default=False, description="Persist missing items into live list"),
    owner_id: str = Query(default="default_user", description="Tenant user identifier"),
    db=Depends(get_db),
) -> PantryGapResponse:
    """Analyze weekly meal plan ingredients and subtract pantry stock.

    Args:
        plan_id: Weekly meal plan document identifier.
        auto_add: Whether to add gap items to live shopping list.
        owner_id: Tenant user identifier.
        db: Database session dependency.

    Returns:
        PantryGapResponse containing required, in-stock, and gap items.
    """
    try:
        return await generate_pantry_gap_shopping_list(
            plan_id=plan_id,
            owner_id=owner_id,
            db=db,
            auto_add_to_list=auto_add,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
