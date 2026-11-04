"""Ingredient API routes for Iðunn.

Provides CRUD endpoints for the canonical ingredient master.
Supports synonym management and IFCT linkage.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..config import settings
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
    """Get the ingredients collection."""
    return get_db()[COLLECTION_INGREDIENTS]


@router.post("", response_model=Ingredient, status_code=status.HTTP_201_CREATED)
async def create_ingredient(
    ingredient: IngredientCreate, db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Create a new canonical ingredient."""
    collection = db[COLLECTION_INGREDIENTS]

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
    category: Optional[str] = Query(None, description="Filter by category"),
    region: Optional[Region] = Query(None, description="Filter by region"),
    query: Optional[str] = Query(None, description="Search by name/synonym"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """List ingredients with optional filters."""
    collection = db[COLLECTION_INGREDIENTS]

    filter_query: dict = {}
    if category:
        filter_query["category"] = category
    if region:
        filter_query["regions"] = region.value
    if query:
        # Search in name and synonyms
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
    ingredient_id: str, db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Get a specific ingredient by ID."""
    from bson import ObjectId

    collection = db[COLLECTION_INGREDIENTS]

    try:
        obj_id = ObjectId(ingredient_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ingredient ID")

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
):
    """Update an ingredient (partial update)."""
    from bson import ObjectId

    collection = db[COLLECTION_INGREDIENTS]

    try:
        obj_id = ObjectId(ingredient_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ingredient ID")

    update_dict = {k: v for k, v in update.model_dump(exclude_none=True).items()}
    if not update_dict:
        raise HTTPException(status_code=400, detail="No fields to update")

    update_dict["updated_at"] = str(int(__import__("time").time()))

    changes = {"$set": update_dict}
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
):
    """Add a synonym to an ingredient."""
    from bson import ObjectId

    collection = db[COLLECTION_INGREDIENTS]

    try:
        obj_id = ObjectId(ingredient_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ingredient ID")

    # Check if synonym already exists
    doc = await collection.find_one(
        {"_id": obj_id, "synonyms.name": synonym.name}
    )
    if doc:
        raise HTTPException(status_code=400, detail="Synonym already exists")

    now = str(int(__import__("time").time()))
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
    ingredient_id: str, db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Delete an ingredient (hard delete)."""
    from bson import ObjectId

    collection = db[COLLECTION_INGREDIENTS]

    try:
        obj_id = ObjectId(ingredient_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ingredient ID")

    result = await collection.delete_one({"_id": obj_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Ingredient not found")
