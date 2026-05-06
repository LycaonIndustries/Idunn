"""Inventory API routes for Iðunn.

Provides CRUD endpoints for pantry items with FEFO (First Expire First Out)
ordering and expiry alerts.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..config import settings
from ..db import (
    COLLECTION_ITEMS,
    MongoClient,
    get_db,
)
from ..models.inventory import (
    Item,
    ItemCreate,
    ItemUpdate,
    Location,
    Unit,
)

router = APIRouter(prefix="/api/v1/items", tags=["inventory"])


def get_items_collection():
    """Get the items collection."""
    return MongoClient.get_db()[COLLECTION_ITEMS]


@router.post("", response_model=Item, status_code=status.HTTP_201_CREATED)
async def create_item(item: ItemCreate, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Add a new item to the pantry."""
    collection = db[COLLECTION_ITEMS]

    now = datetime.utcnow()
    item_dict = item.model_dump()
    item_dict["added_at"] = now
    item_dict["updated_at"] = now
    item_dict["consumed"] = False

    result = await collection.insert_one(item_dict)

    created = await collection.find_one({"_id": result.inserted_id})
    if not created:
        raise HTTPException(status_code=500, detail="Failed to create item")

    created["_id"] = str(created["_id"])
    return Item(**created)


@router.get("", response_model=list[Item])
async def list_items(
    location: Optional[Location] = Query(None, description="Filter by location"),
    expired: Optional[bool] = Query(None, description="Filter by expiry status"),
    expiring_soon: Optional[bool] = Query(
        None, description="Filter items expiring within 3 days"
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """List pantry items with optional filters.

    Default ordering: FEFO (First Expire First Out) - items expiring soon first.
    Items without expiry dates appear last.
    """
    collection = db[COLLECTION_ITEMS]

    # Build filter
    filter_query: dict = {"consumed": False}

    if location:
        filter_query["location"] = location.value

    if expired is not None:
        if expired:
            filter_query["expiry_date"] = {"$lt": datetime.utcnow()}
        else:
            filter_query["expiry_date"] = {"$gte": datetime.utcnow()}

    if expiring_soon:
        three_days = datetime.utcnow() + timedelta(days=3)
        filter_query["expiry_date"] = {"$lte": three_days, "$gte": datetime.utcnow()}

    # FEFO ordering: items with expiry first (ascending), then items without expiry
    cursor = collection.find(filter_query).sort(
        [("expiry_date", 1), ("added_at", -1)]
    ).skip(skip).limit(limit)

    items = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        items.append(Item(**doc))

    return items


@router.get("/expiring", response_model=list[Item])
async def get_expiring_items(
    days: int = Query(3, ge=1, le=30, description="Days to look ahead"),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Get items expiring within specified days (FEFO ordering)."""
    collection = db[COLLECTION_ITEMS]

    cutoff = datetime.utcnow() + timedelta(days=days)
    filter_query = {
        "consumed": False,
        "expiry_date": {"$lte": cutoff, "$gte": datetime.utcnow()},
    }

    cursor = collection.find(filter_query).sort("expiry_date", 1)
    items = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        items.append(Item(**doc))

    return items


@router.get("/{item_id}", response_model=Item)
async def get_item(item_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Get a specific item by ID."""
    from bson import ObjectId

    collection = db[COLLECTION_ITEMS]

    try:
        obj_id = ObjectId(item_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid item ID")

    doc = await collection.find_one({"_id": obj_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Item not found")

    doc["_id"] = str(doc["_id"])
    return Item(**doc)


@router.patch("/{item_id}", response_model=Item)
async def update_item(
    item_id: str, update: ItemUpdate, db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Update an item (partial update)."""
    from bson import ObjectId

    collection = db[COLLECTION_ITEMS]

    try:
        obj_id = ObjectId(item_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid item ID")

    update_dict = {k: v for k, v in update.model_dump(exclude_none=True).items()}
    if not update_dict:
        raise HTTPException(status_code=400, detail="No fields to update")

    update_dict["updated_at"] = datetime.utcnow()

    result = await collection.find_one_and_update(
        {"_id": obj_id},
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
):
    """Consume part or all of an item."""
    from bson import ObjectId

    collection = db[COLLECTION_ITEMS]

    try:
        obj_id = ObjectId(item_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid item ID")

    doc = await collection.find_one({"_id": obj_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Item not found")

    new_quantity = doc["quantity"] - quantity
    update_dict = {"updated_at": datetime.utcnow()}

    if new_quantity <= 0:
        update_dict["consumed"] = True
        update_dict["quantity"] = 0
    else:
        update_dict["quantity"] = new_quantity

    result = await collection.find_one_and_update(
        {"_id": obj_id},
        {"$set": update_dict},
        return_document=True,
    )

    result["_id"] = str(result["_id"])
    return Item(**result)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(item_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Delete an item (hard delete)."""
    from bson import ObjectId

    collection = db[COLLECTION_ITEMS]

    try:
        obj_id = ObjectId(item_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid item ID")

    result = await collection.delete_one({"_id": obj_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")
