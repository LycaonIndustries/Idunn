"""Ingredient API routes for Iðunn.

Provides CRUD endpoints for the canonical ingredient master.
Supports synonym management and IFCT linkage.
"""

from __future__ import annotations

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..db import COLLECTION_INGREDIENTS, get_db
from ..models.ingredient import (
    Ingredient,
    IngredientCreate,
    IngredientUpdate,
    Region,
    Synonym,
)

router = APIRouter(prefix="/api/v1/ingredients", tags=["ingredients"])


def get_ingredients_collection():
    """Retrieve the ingredients collection handle from database.

    Returns:
        Collection adapter for ingredients.
    """
    return get_db()[COLLECTION_INGREDIENTS]


@router.post("", response_model=Ingredient, status_code=status.HTTP_201_CREATED)
async def create_ingredient(
    ingredient: IngredientCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Ingredient:
    """Create a new canonical ingredient in the master database.

    Args:
        ingredient: Ingredient creation payload.
        db: Database session injected via dependency.

    Returns:
        Created Ingredient entity with assigned identifier.

    Raises:
        HTTPException: If created record cannot be retrieved.
    """
    collection = db[COLLECTION_INGREDIENTS]

    # Timestamp creation to support audit tracking.
    now = str(int(__import__("time").time()))
    ingredient_dict = ingredient.model_dump()
    ingredient_dict["created_at"] = now
    ingredient_dict["updated_at"] = now

    result = await collection.insert_one(ingredient_dict)

    created = await collection.find_one({"_id": result.inserted_id})
    if not created:
        raise HTTPException(status_code=500, detail="Failed to create ingredient")

    created["_id"] = str(created["_id"])
    return Ingredient(**created)


@router.get("", response_model=list[Ingredient])
async def list_ingredients(
    category: str | None = Query(None, description="Filter by category"),
    region: Region | None = Query(None, description="Filter by region"),
    query: str | None = Query(None, description="Search by name/synonym"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> list[Ingredient]:
    """List canonical ingredients matching optional search and filter criteria.

    Args:
        category: Filter by broad category.
        region: Filter by Indian regional culinary tradition.
        query: Substring search matching either primary name or synonyms.
        skip: Offset for pagination.
        limit: Maximum results count.
        db: Injected database handle.

    Returns:
        List of matching Ingredient records.
    """
    collection = db[COLLECTION_INGREDIENTS]

    # Build MongoDB query criteria dictionary.
    filter_query: dict = {}
    if category:
        filter_query["category"] = category
    if region:
        filter_query["regions"] = region.value
    if query:
        # Search both primary name and nested synonyms array using case-insensitive regex.
        filter_query["$or"] = [
            {"name": {"$regex": query, "$options": "i"}},
            {"synonyms.name": {"$regex": query, "$options": "i"}},
        ]

    cursor = collection.find(filter_query).skip(skip).limit(limit)
    ingredients = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        ingredients.append(Ingredient(**doc))

    return ingredients


@router.get("/{ingredient_id}", response_model=Ingredient)
async def get_ingredient(
    ingredient_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Ingredient:
    """Get a specific ingredient by its unique database identifier.

    Args:
        ingredient_id: Unique record ID string.
        db: Injected database handle.

    Returns:
        Found Ingredient record.

    Raises:
        HTTPException: If identifier format is invalid or record does not exist.
    """
    collection = db[COLLECTION_INGREDIENTS]

    # Convert string ID into MongoDB ObjectId.
    try:
        obj_id = ObjectId(ingredient_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ingredient ID") from None

    doc = await collection.find_one({"_id": obj_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Ingredient not found")

    doc["_id"] = str(doc["_id"])
    return Ingredient(**doc)


@router.patch("/{ingredient_id}", response_model=Ingredient)
async def update_ingredient(
    ingredient_id: str,
    update: IngredientUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Ingredient:
    """Perform partial update on an existing ingredient.

    Args:
        ingredient_id: Target ingredient ID string.
        update: Fields to update.
        db: Injected database handle.

    Returns:
        Updated Ingredient document.

    Raises:
        HTTPException: If ID is invalid, payload is empty, or record not found.
    """
    collection = db[COLLECTION_INGREDIENTS]

    try:
        obj_id = ObjectId(ingredient_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ingredient ID") from None

    # Exclude unset fields so omitted attributes remain intact.
    update_dict = {k: v for k, v in update.model_dump(exclude_none=True).items()}
    if not update_dict:
        raise HTTPException(status_code=400, detail="No fields to update")

    update_dict["updated_at"] = str(int(__import__("time").time()))

    changes: dict = {"$set": update_dict}
    # Unset vector embeddings when names or synonyms change to invalidate stale vectors.
    if {"name", "synonyms"} & update_dict.keys():
        changes["$unset"] = {"embedding": "", "embedding_model": "", "embedding_text": ""}

    result = await collection.find_one_and_update(
        {"_id": obj_id},
        changes,
        return_document=True,
    )

    if not result:
        raise HTTPException(status_code=404, detail="Ingredient not found")

    result["_id"] = str(result["_id"])
    return Ingredient(**result)


@router.post("/{ingredient_id}/synonyms", response_model=Ingredient)
async def add_synonym(
    ingredient_id: str,
    synonym: Synonym,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Ingredient:
    """Add a new synonym or vernacular name to an ingredient.

    Args:
        ingredient_id: Target ingredient ID string.
        synonym: Synonym data with name, language, and regional classification.
        db: Injected database handle.

    Returns:
        Updated Ingredient document with newly attached synonym.

    Raises:
        HTTPException: If ID is invalid, synonym already exists, or record missing.
    """
    collection = db[COLLECTION_INGREDIENTS]

    try:
        obj_id = ObjectId(ingredient_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ingredient ID") from None

    # Verify synonym name is not duplicated to keep index clean.
    doc = await collection.find_one({"_id": obj_id, "synonyms.name": synonym.name})
    if doc:
        raise HTTPException(status_code=400, detail="Synonym already exists")

    now = str(int(__import__("time").time()))
    # Push synonym to array and clear embedding to trigger vector regeneration.
    result = await collection.find_one_and_update(
        {"_id": obj_id},
        {
            "$push": {"synonyms": synonym.model_dump()},
            "$set": {"updated_at": now},
            "$unset": {"embedding": "", "embedding_model": "", "embedding_text": ""},
        },
        return_document=True,
    )

    if not result:
        raise HTTPException(status_code=404, detail="Ingredient not found")

    result["_id"] = str(result["_id"])
    return Ingredient(**result)


@router.delete("/{ingredient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ingredient(
    ingredient_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> None:
    """Hard-delete an ingredient from canonical master database.

    Args:
        ingredient_id: Unique record ID string to delete.
        db: Injected database handle.

    Returns:
        None.

    Raises:
        HTTPException: If ID format is invalid or ingredient does not exist.
    """
    collection = db[COLLECTION_INGREDIENTS]

    try:
        obj_id = ObjectId(ingredient_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ingredient ID") from None

    result = await collection.delete_one({"_id": obj_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Ingredient not found")
