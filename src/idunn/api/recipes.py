"""Recipe CRUD, source imports, and the ingredient review queue."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Annotated

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import ValidationError
from pymongo import ReturnDocument

from ..db import COLLECTION_INGREDIENTS, COLLECTION_RECIPES, get_db
from ..models.recipe import (
    CuisineType,
    IngredientMatch,
    Recipe,
    RecipeCreate,
    RecipeReview,
    RecipeTextInput,
    RecipeUpdate,
    Region,
)
from ..services.recipe_ingest import IngestResult, RecipeIngestService, confirmed_ids

router = APIRouter(prefix="/api/v1/recipes", tags=["recipes"])
Database = Annotated[AsyncIOMotorDatabase, Depends(get_db)]


def get_ingest_service(db: Database) -> RecipeIngestService:
    return RecipeIngestService(db)


IngestService = Annotated[RecipeIngestService, Depends(get_ingest_service)]


def object_id(value: str) -> ObjectId:
    if not ObjectId.is_valid(value):
        raise HTTPException(status_code=400, detail="Invalid ID")
    return ObjectId(value)


def recipe_response(doc: dict) -> Recipe:
    return Recipe.model_validate({**doc, "_id": str(doc["_id"])})


def revision_filter(doc: dict, revision: int) -> dict:
    query = {"_id": doc["_id"]}
    if revision == 0:
        query["$or"] = [{"revision": 0}, {"revision": {"$exists": False}}]
    else:
        query["revision"] = revision
    return query


@router.post("", response_model=Recipe, status_code=201)
async def create_recipe(recipe: RecipeCreate, db: Database):
    now = datetime.now(UTC)
    matches = [IngredientMatch(ingredient_index=i) for i in range(len(recipe.ingredients))]
    doc = Recipe(
        _id=str(ObjectId()), **recipe.model_dump(), created_at=now, updated_at=now,
        ingest_source="manual", ingredient_matches=matches, needs_review=bool(matches),
    )
    data = doc.model_dump(exclude={"id"})
    data["_id"] = ObjectId(doc.id)
    await db[COLLECTION_RECIPES].insert_one(data)
    return doc


@router.get("", response_model=list[Recipe])
async def list_recipes(
    db: Database,
    query: str | None = Query(None, max_length=200),
    region: Region | None = None,
    cuisine_type: CuisineType | None = None,
    tags: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
):
    filters = {}
    if query:
        filters["$or"] = [
            {field: {"$regex": re.escape(query), "$options": "i"}}
            for field in ("title", "description")
        ]
    if region:
        filters["region"] = region.value
    if cuisine_type:
        filters["cuisine_type"] = cuisine_type.value
    if tags:
        filters["tags"] = {"$all": [tag.strip() for tag in tags.split(",") if tag.strip()]}
    cursor = db[COLLECTION_RECIPES].find(filters).sort("_id", 1).skip(skip).limit(limit)
    return [recipe_response(doc) async for doc in cursor]


# Static routes precede /{recipe_id}, so "review" is never parsed as an ObjectId.
@router.get("/review", response_model=list[Recipe])
async def review_queue(
    db: Database, skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200)
):
    cursor = (
        db[COLLECTION_RECIPES].find({"needs_review": True}).sort("_id", 1).skip(skip).limit(limit)
    )
    return [recipe_response(doc) async for doc in cursor]


@router.post("/ingest", response_model=IngestResult, status_code=201)
async def ingest_recipe(
    service: IngestService, url: str = Query(..., min_length=1, max_length=500)
):
    """Import one URL. Success means it has been stored, not merely queued."""
    return await service.ingest_from_url(url)


@router.post("/ingest/text", response_model=IngestResult, status_code=201)
async def ingest_recipe_text(payload: RecipeTextInput, service: IngestService):
    return await service.ingest_from_text(payload.text, payload.source_name)


@router.get("/{recipe_id}", response_model=Recipe)
async def get_recipe(recipe_id: str, db: Database):
    doc = await db[COLLECTION_RECIPES].find_one({"_id": object_id(recipe_id)})
    if doc is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return recipe_response(doc)


@router.patch("/{recipe_id}", response_model=Recipe)
async def update_recipe(recipe_id: str, update: RecipeUpdate, db: Database):
    collection = db[COLLECTION_RECIPES]
    doc = await collection.find_one({"_id": object_id(recipe_id)})
    if doc is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    changes = update.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=400, detail="No fields to update")
    current = recipe_response(doc)
    merged = current.model_dump(by_alias=True) | changes
    try:
        checked = Recipe.model_validate(merged)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail="Updated recipe fields are invalid") from exc
    changes = {key: checked.model_dump()[key] for key in changes}
    if "ingredients" in changes:
        matches = [IngredientMatch(ingredient_index=i) for i in range(len(checked.ingredients))]
        changes.update(
            ingredient_matches=[match.model_dump() for match in matches],
            normalized_ingredients=[],
            needs_review=bool(matches) or not current.extraction_reviewed,
        )
    if {"title", "description", "ingredients", "steps"} & changes.keys():
        changes.update(embedding=None, embedding_model=None)
    changes["updated_at"] = datetime.now(UTC)
    updated = await collection.find_one_and_update(
        revision_filter(doc, current.revision),
        {"$set": changes, "$inc": {"revision": 1}},
        return_document=ReturnDocument.AFTER,
    )
    if updated is None:
        raise HTTPException(status_code=409, detail="Recipe changed; reload and retry")
    return recipe_response(updated)


@router.post("/{recipe_id}/review", response_model=Recipe)
async def review_recipe(recipe_id: str, review: RecipeReview, db: Database):
    collection = db[COLLECTION_RECIPES]
    doc = await collection.find_one({"_id": object_id(recipe_id)})
    if doc is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    current = recipe_response(doc)
    if current.revision != review.revision:
        raise HTTPException(
            status_code=409, detail="Recipe changed; reload before reviewing"
        )
    matches = {i: IngredientMatch(ingredient_index=i) for i in range(len(current.ingredients))}
    matches.update({match.ingredient_index: match for match in current.ingredient_matches})
    indices = [decision.ingredient_index for decision in review.decisions]
    if len(set(indices)) != len(indices) or any(i >= len(current.ingredients) for i in indices):
        raise HTTPException(
            status_code=422, detail="Review contains duplicate or invalid row numbers"
        )
    for decision in review.decisions:
        if decision.ingredient_id:
            ingredient = await db[COLLECTION_INGREDIENTS].find_one({
                "_id": object_id(decision.ingredient_id),
            })
            if ingredient is None:
                raise HTTPException(status_code=422, detail="Chosen ingredient does not exist")
        matches[decision.ingredient_index] = IngredientMatch(
            ingredient_index=decision.ingredient_index, ingredient_id=decision.ingredient_id,
            status="ignored" if decision.ignore else "confirmed", method="manual", score=1,
        )
    ordered = [matches[i] for i in range(len(current.ingredients))]
    extraction_reviewed = current.extraction_reviewed or review.approve_extraction
    updated = await collection.find_one_and_update(
        revision_filter(doc, review.revision),
        {"$set": {
            "ingredient_matches": [match.model_dump() for match in ordered],
            "normalized_ingredients": confirmed_ids(ordered),
            "extraction_reviewed": extraction_reviewed,
            "needs_review": not extraction_reviewed or any(m.status == "pending" for m in ordered),
            "updated_at": datetime.now(UTC),
        }, "$inc": {"revision": 1}},
        return_document=ReturnDocument.AFTER,
    )
    if updated is None:
        raise HTTPException(status_code=409, detail="Recipe changed; reload before reviewing")
    return recipe_response(updated)


@router.delete("/{recipe_id}", status_code=204)
async def delete_recipe(recipe_id: str, db: Database):
    result = await db[COLLECTION_RECIPES].delete_one({"_id": object_id(recipe_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return Response(status_code=204)
