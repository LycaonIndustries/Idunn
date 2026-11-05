"""Recipe CRUD, source imports, and the ingredient review queue."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Annotated, Any

from bson import ObjectId
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
)
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
    RecipeUrlInput,
    Region,
)
from ..services.cooking_deduction import CookingDeductionService, DeductionReport
from ..services.ifct_nutrition import calculate_recipe_nutrition
from ..services.recipe_ingest import IngestResult, RecipeIngestService, confirmed_ids
from .deps import AuthenticatedUser, get_current_user
from .limiter import limiter

router = APIRouter(prefix="/api/v1/recipes", tags=["recipes"])
Database = Annotated[AsyncIOMotorDatabase, Depends(get_db)]
CurrentUser = Annotated[AuthenticatedUser, Depends(get_current_user)]


def owner_filter(user_id: str) -> dict:
    """Build tenant query filter supporting legacy untagged documents in dev mode.

    Args:
        user_id: Unique caller identifier.

    Returns:
        Mongo query dictionary scoped to tenant.
    """
    if user_id == "dev_user_local":
        return {"$or": [{"owner_id": user_id}, {"owner_id": {"$exists": False}}]}
    return {"owner_id": user_id}


def get_ingest_service(db: Database) -> RecipeIngestService:
    """Instantiate the recipe ingestion service with the active database handle.

    Args:
        db: Database session injected via dependency.

    Returns:
        Configured RecipeIngestService instance.
    """
    return RecipeIngestService(db)


IngestService = Annotated[RecipeIngestService, Depends(get_ingest_service)]


def object_id(value: str) -> Any:
    """Validate and convert record identifier.

    Args:
        value: String representation of record ID.

    Returns:
        ObjectId if valid 24-character hex, otherwise sanitized string.

    Raises:
        HTTPException: If identifier is empty.
    """
    clean = str(value).strip() if value is not None else ""
    if not clean:
        raise HTTPException(status_code=400, detail="Invalid ID")
    if ObjectId.is_valid(clean):
        return ObjectId(clean)
    return clean


def recipe_response(doc: dict) -> Recipe:
    """Convert raw database dictionary document into a validated Recipe model.

    Args:
        doc: Raw document dictionary from database.

    Returns:
        Validated Recipe model instance.
    """
    # Transform database identifier into string format expected by clients.
    rec_dict = dict(doc)
    rec_id = str(rec_dict.get("_id") or rec_dict.get("id") or "")
    rec_dict["_id"] = rec_id
    return Recipe.model_validate(rec_dict)


def revision_filter(doc: dict, revision: int) -> dict:
    """Build optimistic concurrency filter query to prevent lost updates.

    Args:
        doc: Target database document dictionary.
        revision: Expected revision integer.

    Returns:
        Query dictionary targeting document identifier and revision state.
    """
    # Match revision 0 or missing revision field for legacy documents.
    query: dict = {"_id": doc["_id"]}
    if revision == 0:
        query["$or"] = [{"revision": 0}, {"revision": {"$exists": False}}]
    else:
        query["revision"] = revision
    return query


@router.post("", response_model=Recipe, status_code=201)
async def create_recipe(
    recipe: RecipeCreate,
    db: Database,
    user: CurrentUser,
) -> Recipe:
    """Create a new manual recipe entry.

    Args:
        recipe: Recipe creation payload.
        db: Injected database handle.
        user: Authenticated caller identity.

    Returns:
        Created Recipe record.
    """
    # Initialize pending matches for all ingredients so review queue can flag them.
    now = datetime.now(UTC)
    matches = [IngredientMatch(ingredient_index=i) for i in range(len(recipe.ingredients))]

    # Estimate nutritional profile automatically using IFCT standards when not supplied.
    nutrition = recipe.nutrition
    if nutrition is None:
        computed = calculate_recipe_nutrition(recipe)
        if computed.is_ifct_verified:
            nutrition = computed

    doc = Recipe(
        _id=str(ObjectId()),
        **recipe.model_dump(exclude={"owner_id", "nutrition"}),
        nutrition=nutrition,
        owner_id=user.id,
        created_at=now,
        updated_at=now,
        ingest_source="manual",
        ingredient_matches=matches,
        needs_review=bool(matches),
    )
    data = doc.model_dump(exclude={"id"})
    data["_id"] = ObjectId(doc.id)
    data["owner_id"] = user.id
    await db[COLLECTION_RECIPES].insert_one(data)
    return doc


@router.get("", response_model=list[Recipe])
async def list_recipes(
    db: Database,
    user: CurrentUser,
    query: str | None = Query(None, max_length=200),
    region: Region | None = None,
    cuisine_type: CuisineType | None = None,
    tags: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
) -> list[Recipe]:
    """List recipes with optional keyword, cuisine, and tag filters.

    Args:
        db: Injected database handle.
        user: Authenticated caller identity.
        query: Optional search keyword matching title or description.
        region: Optional Indian culinary region.
        cuisine_type: Optional dietary category.
        tags: Comma-separated list of tags required on the recipe.
        skip: Pagination offset.
        limit: Maximum results count.

    Returns:
        List of matching Recipe records.
    """
    # Isolate queries to caller tenant records to prevent data leakage.
    filters: dict = {**owner_filter(user.id)}
    # Apply regex search with escaped input to prevent regex injection attacks.
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
    db: Database,
    user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> list[Recipe]:
    """Retrieve recipes that require human review of ingredient mappings.

    Args:
        db: Injected database handle.
        user: Authenticated caller identity.
        skip: Pagination offset.
        limit: Maximum results count.

    Returns:
        List of recipes flagged with needs_review=True.
    """
    # Fetch unconfirmed recipe extractions for active tenant review queue.
    cursor = (
        db[COLLECTION_RECIPES]
        .find({"needs_review": True, **owner_filter(user.id)})
        .sort("_id", 1)
        .skip(skip)
        .limit(limit)
    )
    return [recipe_response(doc) async for doc in cursor]


@router.post("/ingest", response_model=IngestResult, status_code=201)
@limiter.limit("15/minute;100/day")
async def ingest_recipe(
    request: Request,
    service: IngestService,
    user: CurrentUser,
    url: str | None = Query(None, min_length=1, max_length=500),
    body: RecipeUrlInput | None = None,
) -> IngestResult:
    """Import and parse a recipe from a web URL.

    Args:
        request: Incoming HTTP request for rate limiting.
        service: Ingestion service dependency.
        user: Authenticated caller identity.
        url: URL provided via query parameter.
        body: URL provided via JSON body payload.

    Returns:
        IngestResult containing extracted recipe details and confidence scores.

    Raises:
        HTTPException: If no URL is provided in either query or body.
    """
    target_url = url or (body.url if body else None)
    if not target_url:
        raise HTTPException(
            status_code=422,
            detail="A 'url' parameter (query string or JSON body) is required.",
        )
    result = await service.ingest_from_url(target_url)
    # Bind imported recipe to calling tenant to enforce object-level isolation.
    await service.db[COLLECTION_RECIPES].update_one(
        {"_id": ObjectId(result.recipe_id)},
        {"$set": {"owner_id": user.id}},
    )
    return result


@router.post("/ingest/text", response_model=IngestResult, status_code=201)
@limiter.limit("15/minute;100/day")
async def ingest_recipe_text(
    request: Request,
    payload: RecipeTextInput,
    service: IngestService,
    user: CurrentUser,
) -> IngestResult:
    """Import and extract structured recipe from pasted text.

    Args:
        request: Incoming HTTP request for rate limiting.
        payload: Input text and attribution name.
        service: Ingestion service dependency.
        user: Authenticated caller identity.

    Returns:
        IngestResult with parsed recipe.
    """
    result = await service.ingest_from_text(payload.text, payload.source_name)
    # Stamp owner identity on text-extracted recipe document.
    await service.db[COLLECTION_RECIPES].update_one(
        {"_id": ObjectId(result.recipe_id)},
        {"$set": {"owner_id": user.id}},
    )
    return result


@router.post("/ingest/image", response_model=IngestResult, status_code=201)
async def ingest_recipe_image(
    service: IngestService,
    user: CurrentUser,
    file: UploadFile = File(...),
    source_name: str = Form("Image Upload"),
) -> IngestResult:
    """Extract and import a recipe from an uploaded cookbook photo or screenshot.

    Args:
        service: Ingestion service dependency.
        user: Authenticated caller identity.
        file: Uploaded image file stream.
        source_name: Attribution name for recipe source.

    Returns:
        IngestResult with extracted recipe.

    Raises:
        HTTPException: If file is not an image, is empty, or exceeds 10 MB limit.
    """
    # Enforce MIME type to prevent processing non-image files.
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="File must be an image (JPEG, PNG, or WebP).",
        )
    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=400,
            detail="Uploaded image is empty.",
        )
    # Reject oversized images to protect LLM context windows and memory.
    if len(content) > 10_000_000:
        raise HTTPException(
            status_code=413,
            detail="Image size exceeds the 10 MB limit.",
        )
    result = await service.ingest_from_image(content, file.content_type, source_name)
    # Bind vision-extracted recipe to calling tenant identity.
    await service.db[COLLECTION_RECIPES].update_one(
        {"_id": ObjectId(result.recipe_id)},
        {"$set": {"owner_id": user.id}},
    )
    return result


@router.post("/ingest/audio", response_model=IngestResult, status_code=201)
async def ingest_recipe_audio(
    service: IngestService,
    user: CurrentUser,
    file: UploadFile = File(...),
    source_name: str = Form("Voice Note"),
) -> IngestResult:
    """Extract and import a recipe from an uploaded voice recording or audio file.

    Args:
        service: Ingestion service dependency.
        user: Authenticated caller identity.
        file: Uploaded audio file stream.
        source_name: Attribution name.

    Returns:
        IngestResult with extracted recipe.

    Raises:
        HTTPException: If file is not audio, is empty, or exceeds 50 MB limit.
    """
    content_type = file.content_type or ""
    filename = (file.filename or "").lower()
    is_audio = content_type.startswith("audio/") or any(
        filename.endswith(ext) for ext in (".mp3", ".m4a", ".wav", ".ogg", ".webm")
    )
    if not is_audio:
        raise HTTPException(
            status_code=400,
            detail="File must be an audio recording (MP3, M4A, WAV, OGG, or WebM).",
        )
    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=400,
            detail="Uploaded audio is empty.",
        )
    if len(content) > 50_000_000:
        raise HTTPException(
            status_code=413,
            detail="Audio size exceeds the 50 MB limit.",
        )
    result = await service.ingest_from_audio(content, content_type or "audio/mp3", source_name)
    # Bind transcribed recipe to calling tenant identity.
    await service.db[COLLECTION_RECIPES].update_one(
        {"_id": ObjectId(result.recipe_id)},
        {"$set": {"owner_id": user.id}},
    )
    return result


@router.post("/ingest/video", response_model=IngestResult, status_code=201)
async def ingest_recipe_video(
    service: IngestService,
    user: CurrentUser,
    file: UploadFile = File(...),
    source_name: str = Form("Video Reel"),
) -> IngestResult:
    """Extract and import a recipe from a silent video reel by sampling frames.

    Args:
        service: Ingestion service dependency.
        user: Authenticated caller identity.
        file: Uploaded video file stream.
        source_name: Attribution name.

    Returns:
        IngestResult with extracted recipe.

    Raises:
        HTTPException: If file is not video, is empty, or exceeds 100 MB limit.
    """
    content_type = file.content_type or ""
    filename = (file.filename or "").lower()
    is_video = content_type.startswith("video/") or any(
        filename.endswith(ext) for ext in (".mp4", ".mov", ".webm", ".mkv")
    )
    if not is_video:
        raise HTTPException(
            status_code=400,
            detail="File must be a video file (MP4, MOV, WebM, or MKV).",
        )
    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=400,
            detail="Uploaded video is empty.",
        )
    if len(content) > 100_000_000:
        raise HTTPException(
            status_code=413,
            detail="Video size exceeds the 100 MB limit.",
        )
    result = await service.ingest_from_video(content, content_type or "video/mp4", source_name)
    # Bind video-extracted recipe to calling tenant identity.
    await service.db[COLLECTION_RECIPES].update_one(
        {"_id": ObjectId(result.recipe_id)},
        {"$set": {"owner_id": user.id}},
    )
    return result


@router.get("/{recipe_id}", response_model=Recipe)
async def get_recipe(
    recipe_id: str,
    db: Database,
    user: CurrentUser,
) -> Recipe:
    """Retrieve a recipe by unique database identifier.

    Args:
        recipe_id: Unique record ID string.
        db: Injected database handle.
        user: Authenticated caller identity.

    Returns:
        Found Recipe record.

    Raises:
        HTTPException: If recipe is not found.
    """
    # Scope recipe lookup to document ID and tenant owner to prevent BOLA exposure.
    doc = await db[COLLECTION_RECIPES].find_one(
        {"_id": object_id(recipe_id), **owner_filter(user.id)}
    )
    if doc is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return recipe_response(doc)


@router.post("/{recipe_id}/cook", response_model=DeductionReport)
async def cook_recipe(
    recipe_id: str,
    db: Database,
    user: CurrentUser,
    servings_multiplier: float = Query(1.0, ge=0.1, le=10.0),
) -> DeductionReport:
    """Deduct recipe ingredients from pantry stock using FEFO rules.

    Args:
        recipe_id: Target recipe identifier.
        db: Injected database handle.
        user: Authenticated caller identity.
        servings_multiplier: Scale multiplier for ingredient quantities.

    Returns:
        DeductionReport detailing deducted items and shortages.

    Raises:
        HTTPException: If recipe is not found.
    """
    # Verify target recipe belongs to the caller before attempting pantry deduction.
    doc = await db[COLLECTION_RECIPES].find_one(
        {"_id": object_id(recipe_id), **owner_filter(user.id)}
    )
    if doc is None:
        raise HTTPException(status_code=404, detail="Recipe not found")

    recipe_obj = recipe_response(doc)
    service = CookingDeductionService(db)
    return await service.deduct_recipe_ingredients(
        recipe_obj,
        servings_multiplier=servings_multiplier,
    )


@router.patch("/{recipe_id}", response_model=Recipe)
async def update_recipe(
    recipe_id: str,
    update: RecipeUpdate,
    db: Database,
    user: CurrentUser,
) -> Recipe:
    """Partially update an existing recipe and increment revision number.

    Args:
        recipe_id: Unique record ID string.
        update: Fields to update.
        db: Injected database handle.
        user: Authenticated caller identity.

    Returns:
        Updated Recipe document.

    Raises:
        HTTPException: If recipe is missing, payload is empty, or version conflict occurs.
    """
    collection = db[COLLECTION_RECIPES]
    doc = await collection.find_one({"_id": object_id(recipe_id), **owner_filter(user.id)})
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

    # Reset ingredient match records when ingredients list is modified.
    if "ingredients" in changes:
        matches = [IngredientMatch(ingredient_index=i) for i in range(len(checked.ingredients))]
        changes.update(
            ingredient_matches=[match.model_dump() for match in matches],
            normalized_ingredients=[],
            needs_review=bool(matches) or not current.extraction_reviewed,
        )

    # Invalidate embedding vectors when text content changes.
    if {"title", "description", "ingredients", "steps"} & changes.keys():
        changes.update(embedding=None, embedding_model=None)
    changes["updated_at"] = datetime.now(UTC)

    # Enforce optimistic lock query scoped to tenant owner.
    match_query = {**revision_filter(doc, current.revision), **owner_filter(user.id)}

    updated = await collection.find_one_and_update(
        match_query,
        {"$set": changes, "$inc": {"revision": 1}},
        return_document=ReturnDocument.AFTER,
    )
    if updated is None:
        raise HTTPException(status_code=409, detail="Recipe changed; reload and retry")
    return recipe_response(updated)


@router.post("/{recipe_id}/review", response_model=Recipe)
async def review_recipe(
    recipe_id: str,
    review: RecipeReview,
    db: Database,
    user: CurrentUser,
) -> Recipe:
    """Submit human review decisions for recipe ingredient mappings.

    Args:
        recipe_id: Unique record ID string.
        review: Review decisions payload.
        db: Injected database handle.
        user: Authenticated caller identity.

    Returns:
        Updated Recipe document with confirmed ingredient associations.

    Raises:
        HTTPException: If recipe is missing, version conflict occurs, or decisions are invalid.
    """
    collection = db[COLLECTION_RECIPES]
    doc = await collection.find_one({"_id": object_id(recipe_id), **owner_filter(user.id)})
    if doc is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    current = recipe_response(doc)
    # Enforce revision match to prevent overwriting intermediate user edits.
    if current.revision != review.revision:
        raise HTTPException(
            status_code=409,
            detail="Recipe changed; reload before reviewing",
        )
    matches = {i: IngredientMatch(ingredient_index=i) for i in range(len(current.ingredients))}
    matches.update({match.ingredient_index: match for match in current.ingredient_matches})
    indices = [decision.ingredient_index for decision in review.decisions]
    if len(set(indices)) != len(indices) or any(i >= len(current.ingredients) for i in indices):
        raise HTTPException(
            status_code=422,
            detail="Review contains duplicate or invalid row numbers",
        )
    # Verify each chosen ingredient ID exists in the database.
    for decision in review.decisions:
        if decision.ingredient_id:
            ingredient = await db[COLLECTION_INGREDIENTS].find_one(
                {
                    "_id": object_id(decision.ingredient_id),
                }
            )
            if ingredient is None:
                raise HTTPException(status_code=422, detail="Chosen ingredient does not exist")
        matches[decision.ingredient_index] = IngredientMatch(
            ingredient_index=decision.ingredient_index,
            ingredient_id=decision.ingredient_id,
            status="ignored" if decision.ignore else "confirmed",
            method="manual",
            score=1,
        )
    ordered = [matches[i] for i in range(len(current.ingredients))]
    extraction_reviewed = current.extraction_reviewed or review.approve_extraction

    # Update matches, mark confirmed IDs, and increment revision number.
    match_query = {**revision_filter(doc, review.revision), **owner_filter(user.id)}

    updated = await collection.find_one_and_update(
        match_query,
        {
            "$set": {
                "ingredient_matches": [match.model_dump() for match in ordered],
                "normalized_ingredients": confirmed_ids(ordered),
                "extraction_reviewed": extraction_reviewed,
                "needs_review": not extraction_reviewed
                or any(m.status == "pending" for m in ordered),
                "updated_at": datetime.now(UTC),
            },
            "$inc": {"revision": 1},
        },
        return_document=ReturnDocument.AFTER,
    )
    if updated is None:
        raise HTTPException(status_code=409, detail="Recipe changed; reload before reviewing")
    return recipe_response(updated)


@router.post("/{recipe_id}/nutrition/calculate", response_model=Recipe)
async def calculate_recipe_nutrition_endpoint(
    recipe_id: str,
    db: Database,
    user: CurrentUser,
) -> Recipe:
    """Calculate and attach ICMR/NIN IFCT nutrition values to a recipe.

    Args:
        recipe_id: Target recipe identifier.
        db: Injected database handle.
        user: Authenticated caller identity.

    Returns:
        Updated Recipe with verified IFCT nutrition information.

    Raises:
        HTTPException: If recipe does not exist.
    """
    # Scope recipe lookup to document ID and tenant owner to prevent data leakage.
    doc = await db[COLLECTION_RECIPES].find_one(
        {"_id": object_id(recipe_id), **owner_filter(user.id)}
    )
    if doc is None:
        raise HTTPException(status_code=404, detail="Recipe not found")

    recipe = recipe_response(doc)
    nutrition = calculate_recipe_nutrition(recipe)

    # Persist calculated nutritional metrics into database record.
    updated = await db[COLLECTION_RECIPES].find_one_and_update(
        {"_id": doc["_id"], **owner_filter(user.id)},
        {
            "$set": {
                "nutrition": nutrition.model_dump(),
                "updated_at": datetime.now(UTC),
            },
            "$inc": {"revision": 1},
        },
        return_document=ReturnDocument.AFTER,
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return recipe_response(updated)


@router.delete("/{recipe_id}", status_code=204)
async def delete_recipe(
    recipe_id: str,
    db: Database,
    user: CurrentUser,
) -> Response:
    """Delete a recipe record from the library.

    Args:
        recipe_id: Unique record ID string.
        db: Injected database handle.
        user: Authenticated caller identity.

    Returns:
        HTTP 204 No Content response.

    Raises:
        HTTPException: If recipe does not exist.
    """
    result = await db[COLLECTION_RECIPES].delete_one(
        {"_id": object_id(recipe_id), **owner_filter(user.id)}
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return Response(status_code=204)
