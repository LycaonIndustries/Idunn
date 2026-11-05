"""Inventory API routes for Iðunn.

Provides CRUD endpoints for pantry items with FEFO (First Expire First Out)
ordering and expiry alerts.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..db import COLLECTION_ITEMS, MongoClient, get_db
from ..models.inventory import (
    Item,
    ItemCreate,
    ItemUpdate,
    Location,
)
from .deps import AuthenticatedUser, get_current_user

router = APIRouter(prefix="/api/v1/items", tags=["inventory"])


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


def get_items_collection():
    """Retrieve items collection handle from the default database client.

    Returns:
        Collection adapter for inventory items.
    """
    return MongoClient.get_db()[COLLECTION_ITEMS]


@router.post("", response_model=Item, status_code=status.HTTP_201_CREATED)
async def create_item(
    item: ItemCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> Item:
    """Add a new ingredient or grocery item to the kitchen pantry.

    Args:
        item: Item creation payload.
        db: Injected database handle.
        user: Authenticated tenant context.

    Returns:
        Created Item record with persistent database identifier.

    Raises:
        HTTPException: If created record cannot be retrieved from storage.
    """
    collection = db[COLLECTION_ITEMS]

    # Stamp tenant owner identity to enforce multi-user isolation.
    now = datetime.now(UTC)
    item_dict = item.model_dump()
    item_dict["owner_id"] = user.id
    item_dict["added_at"] = now
    item_dict["updated_at"] = now
    item_dict["consumed"] = False

    result = await collection.insert_one(item_dict)

    created = await collection.find_one({"_id": result.inserted_id, "owner_id": user.id})
    if not created:
        raise HTTPException(status_code=500, detail="Failed to create item")

    created["_id"] = str(created["_id"])
    return Item(**created)


@router.get("", response_model=list[Item])
async def list_items(
    location: Location | None = Query(None, description="Filter by location"),
    expired: bool | None = Query(None, description="Filter by expiry status"),
    expiring_soon: bool | None = Query(None, description="Filter items expiring within 3 days"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> list[Item]:
    """List pantry items ordered by FEFO (First Expire First Out) priority.

    Args:
        location: Filter items by storage zone.
        expired: Filter by expired status boolean.
        expiring_soon: Filter items expiring in the next 3 days.
        skip: Pagination offset.
        limit: Maximum results count.
        db: Injected database handle.
        user: Authenticated tenant context.

    Returns:
        List of active inventory items ordered with earliest expiring first.
    """
    collection = db[COLLECTION_ITEMS]

    # Exclude consumed items and restrict query scope to calling tenant.
    filter_query: dict = {"consumed": False, **owner_filter(user.id)}

    if location:
        filter_query["location"] = location.value

    now = datetime.now(UTC)
    if expired is not None:
        if expired:
            filter_query["expiry_date"] = {"$lt": now}
        else:
            filter_query["expiry_date"] = {"$gte": now}

    if expiring_soon:
        three_days = now + timedelta(days=3)
        filter_query["expiry_date"] = {"$lte": three_days, "$gte": now}

    # Normalize null expiry timestamps to maximum date so dated items sort first.
    pipeline = [
        {"$match": filter_query},
        {"$addFields": {"_fefo": {"$ifNull": ["$expiry_date", datetime.max]}}},
        {"$sort": {"_fefo": 1, "added_at": -1}},
        {"$skip": skip},
        {"$limit": limit},
    ]
    cursor = collection.aggregate(pipeline)

    items = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        items.append(Item(**doc))

    return items


@router.get("/expiring", response_model=list[Item])
async def get_expiring_items(
    days: int = Query(3, ge=1, le=30, description="Days to look ahead"),
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> list[Item]:
    """Retrieve pantry items expiring within a designated number of days.

    Args:
        days: Threshold number of days to inspect.
        db: Injected database handle.
        user: Authenticated tenant context.

    Returns:
        List of items expiring soon, sorted chronologically.
    """
    collection = db[COLLECTION_ITEMS]

    # Select tenant unconsumed items with expiry dates in lookahead window.
    cutoff = datetime.now(UTC) + timedelta(days=days)
    filter_query = {
        "consumed": False,
        **owner_filter(user.id),
        "expiry_date": {"$lte": cutoff, "$gte": datetime.now(UTC)},
    }

    cursor = collection.find(filter_query).sort("expiry_date", 1)
    items = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        items.append(Item(**doc))

    return items


@router.get("/{item_id}", response_model=Item)
async def get_item(
    item_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> Item:
    """Retrieve a single pantry item by unique identifier.

    Args:
        item_id: Unique record ID string.
        db: Injected database handle.
        user: Authenticated tenant context.

    Returns:
        Found Item record.

    Raises:
        HTTPException: If identifier is invalid or item is missing.
    """
    collection = db[COLLECTION_ITEMS]

    try:
        obj_id = ObjectId(item_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid item ID") from None

    # Scope lookup to item identifier and calling user to prevent BOLA access.
    doc = await collection.find_one({"_id": obj_id, **owner_filter(user.id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Item not found")

    doc["_id"] = str(doc["_id"])
    return Item(**doc)


@router.patch("/{item_id}", response_model=Item)
async def update_item(
    item_id: str,
    update: ItemUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> Item:
    """Perform partial update on pantry item attributes.

    Args:
        item_id: Target item ID string.
        update: Partial item update payload.
        db: Injected database handle.
        user: Authenticated tenant context.

    Returns:
        Updated Item document.

    Raises:
        HTTPException: If ID is invalid, payload is empty, or item is missing.
    """
    collection = db[COLLECTION_ITEMS]

    try:
        obj_id = ObjectId(item_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid item ID") from None

    # Exclude omitted fields to avoid overwriting attributes with None.
    update_dict = {k: v for k, v in update.model_dump(exclude_none=True).items()}
    if not update_dict:
        raise HTTPException(status_code=400, detail="No fields to update")

    update_dict["updated_at"] = datetime.now(UTC)

    # Restrict mutation to item owned by the active caller.
    result = await collection.find_one_and_update(
        {"_id": obj_id, **owner_filter(user.id)},
        {"$set": update_dict},
        return_document=True,
    )

    if not result:
        raise HTTPException(status_code=404, detail="Item not found")

    result["_id"] = str(result["_id"])
    return Item(**result)


@router.post("/{item_id}/consume", response_model=Item)
async def consume_item(
    item_id: str,
    quantity: float = Query(..., gt=0, description="Quantity to consume"),
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> Item:
    """Deduct quantity from an inventory item or flag as consumed.

    Args:
        item_id: Unique record ID string.
        quantity: Amount consumed in cooking or meal preparation.
        db: Injected database handle.
        user: Authenticated tenant context.

    Returns:
        Updated Item record showing remaining quantity or consumed status.

    Raises:
        HTTPException: If ID is invalid or record is missing.
    """
    collection = db[COLLECTION_ITEMS]

    try:
        obj_id = ObjectId(item_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid item ID") from None

    # Ensure calling user owns target pantry item prior to applying deductions.
    doc = await collection.find_one({"_id": obj_id, **owner_filter(user.id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Item not found")

    # Mark consumed when deducted quantity reaches or exceeds available stock.
    new_quantity = doc["quantity"] - quantity
    update_dict: dict = {"updated_at": datetime.now(UTC)}

    if new_quantity <= 0:
        update_dict["consumed"] = True
        update_dict["quantity"] = 0.0
    else:
        update_dict["quantity"] = new_quantity

    result = await collection.find_one_and_update(
        {"_id": obj_id, **owner_filter(user.id)},
        {"$set": update_dict},
        return_document=True,
    )

    result["_id"] = str(result["_id"])
    return Item(**result)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    item_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> None:
    """Hard-delete an inventory item from database storage.

    Args:
        item_id: Unique record ID string.
        db: Injected database handle.
        user: Authenticated tenant context.

    Returns:
        None.

    Raises:
        HTTPException: If ID is invalid or record does not exist.
    """
    collection = db[COLLECTION_ITEMS]

    try:
        obj_id = ObjectId(item_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid item ID") from None

    # Enforce that delete actions cannot remove pantry rows of other users.
    result = await collection.delete_one({"_id": obj_id, **owner_filter(user.id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")
