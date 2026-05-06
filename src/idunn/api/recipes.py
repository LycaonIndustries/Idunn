"""Recipe API routes for Iðunn.

Provides CRUD endpoints for recipes with multi-source ingest support
(JSON-LD, blog scraping, YouTube transcripts).
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..config import settings
from ..db import COLLECTION_RECIPES, get_db
from ..models.recipe import (
    Recipe,
    RecipeCreate,
    RecipeUpdate,
    Region,
    CuisineType,
)

router = APIRouter(prefix="/api/v1/recipes", tags=["recipes"])


@router.post("", response_model=Recipe, status_code=status.HTTP_201_CREATED)
async def create_recipe(
    recipe: RecipeCreate, db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Create a new recipe."""
    collection = db[COLLECTION_RECIPES]

    now = recipe.created_at
    recipe_dict = recipe.model_dump()
    recipe_dict["created_at"] = now
    recipe_dict["updated_at"] = now

    result = await collection.insert_one(recipe_dict)

    created = await collection.find_one({"_id": result.inserted_id})
    if not created:
        raise HTTPException(status_code=500, detail="Failed to create recipe")

    created["_id"] = str(created["_id"])
    return Recipe(**created)


@router.get("", response_model=list[Recipe])
async def list_recipes(
    query: Optional[str] = Query(None, description="Search in title/description"),
    region: Optional[Region] = Query(None, description="Filter by region"),
    cuisine_type: Optional[CuisineType] = Query(None, description="Filter by cuisine type"),
    tags: Optional[str] = Query(None, description="Comma-separated tags"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """List recipes with optional filters."""
    collection = db[COLLECTION_RECIPES]

    filter_query: dict = {}

    if query:
        # Text search on title and description
        filter_query["$or"] = [
            {"title": {"$regex": query, "$options": "i"}},
            {"description": {"$regex": query, "$options": "i"}},
        ]

    if region:
        filter_query["region"] = region.value

    if cuisine_type:
        filter_query["cuisine_type"] = cuisine_type.value

    if tags:
        tag_list = [t.strip() for t in tags.split(",")]
        filter_query["tags"] = {"$all": tag_list}

    cursor = collection.find(filter_query).skip(skip).limit(limit)
    recipes = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        recipes.append(Recipe(**doc))

    return recipes


@router.get("/{recipe_id}", response_model=Recipe)
async def get_recipe(recipe_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Get a specific recipe by ID."""
    from bson import ObjectId

    collection = db[COLLECTION_RECIPES]

    try:
        obj_id = ObjectId(recipe_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid recipe ID")

    doc = await collection.find_one({"_id": obj_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Recipe not found")

    doc["_id"] = str(doc["_id"])
    return Recipe(**doc)


@router.patch("/{recipe_id}", response_model=Recipe)
async def update_recipe(
    recipe_id: str,
    update: RecipeUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Update a recipe (partial update)."""
    from bson import ObjectId

    collection = db[COLLECTION_RECIPES]

    try:
        obj_id = ObjectId(recipe_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid recipe ID")

    update_dict = {k: v for k, v in update.model_dump(exclude_none=True).items()}
    if not update_dict:
        raise HTTPException(status_code=400, detail="No fields to update")

    update_dict["updated_at"] = RecipeCreate.__fields__["created_at"].default_factory()

    result = await collection.find_one_and_update(
        {"_id": obj_id},
        {"$set": update_dict},
        return_document=True,
    )

    if not result:
        raise HTTPException(status_code=404, detail="Recipe not found")

    result["_id"] = str(result["_id"])
    return Recipe(**result)


@router.delete("/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_recipe(recipe_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Delete a recipe (hard delete)."""
    from bson import ObjectId

    collection = db[COLLECTION_RECIPES]

    try:
        obj_id = ObjectId(recipe_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid recipe ID")

    result = await collection.delete_one({"_id": obj_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Recipe not found")


@router.post("/ingest", status_code=status.HTTP_202_ACCEPTED)
async def ingest_recipe(
    url: str = Query(..., description="Recipe URL to ingest"),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Ingest a recipe from a URL (JSON-LD, blog, or YouTube).

    Uses RecipeIngestService for multi-source ingestion.
    Returns immediately with task acceptance; processing is async.
    """
    from ..services.recipe_ingest import RecipeIngestService, IngestSource

    # Determine source type (simple heuristic)
    if "youtube.com" in url or "youtu.be" in url:
        source_type = IngestSource.YOUTUBE
    else:
        source_type = IngestSource.JSON_LD  # Try JSON-LD first

    # Create ingest service
    service = RecipeIngestService(db)

    # Ingest recipe
    result = await service.ingest_from_url(url)

    if result.success:
        return {
            "message": "Recipe ingested successfully",
            "recipe_id": result.recipe_id,
            "confidence": result.confidence,
            "warnings": result.warnings,
        }
    else:
        raise HTTPException(
            status_code=422,
            detail={
                "message": result.message,
                "warnings": result.warnings,
            },
        )
