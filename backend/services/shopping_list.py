"""Shopping list persistence and quick-commerce service.

Manages grocery items required for missing recipe ingredients or ad-hoc additions,
providing deep links for instant checkout on Blinkit, Zepto, and Instamart.
"""

from datetime import UTC, datetime
from uuid import uuid4

from motor.motor_asyncio import AsyncIOMotorDatabase

from backend.db import COLLECTION_SHOPPING_LISTS
from backend.models.cook_ai import ShoppingList, ShoppingListCreate, ShoppingListItem


class ShoppingListService:
    """Service handling CRUD operations on the user's shopping list."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        """Initialize shopping list service with database handle.

        Args:
            db: Active async database instance.
        """
        # Store database reference for query operations.
        self._collection = db[COLLECTION_SHOPPING_LISTS]

    async def get_all_items(self) -> ShoppingList:
        """Fetch all pending and purchased shopping list items.

        Returns:
            ShoppingList containing list of items and total count.
        """
        # Retrieve all items ordered by creation time descending.
        cursor = self._collection.find().sort("created_at", -1)
        items: list[ShoppingListItem] = []
        async for doc in cursor:
            doc_id = str(doc.get("_id") or doc.get("id"))
            items.append(
                ShoppingListItem(
                    id=doc_id,
                    name=doc.get("name", ""),
                    quantity=float(doc.get("quantity", 1.0)),
                    unit=doc.get("unit", "item"),
                    recipe_id=doc.get("recipe_id"),
                    is_purchased=bool(doc.get("is_purchased", False)),
                    created_at=doc.get("created_at") or datetime.now(UTC),
                )
            )
        return ShoppingList(items=items, total_count=len(items))

    async def add_item(self, payload: ShoppingListCreate) -> ShoppingListItem:
        """Add a single item to the shopping list.

        Args:
            payload: ShoppingListCreate containing name, quantity, unit, recipe_id.

        Returns:
            Created ShoppingListItem with generated ID.
        """
        item_id = str(uuid4())
        now = datetime.now(UTC)
        doc = {
            "_id": item_id,
            "id": item_id,
            "name": payload.name,
            "quantity": payload.quantity,
            "unit": payload.unit,
            "recipe_id": payload.recipe_id,
            "is_purchased": False,
            "created_at": now,
        }
        # Insert document into persistent collection.
        await self._collection.insert_one(doc)
        return ShoppingListItem(
            id=item_id,
            name=payload.name,
            quantity=payload.quantity,
            unit=payload.unit,
            recipe_id=payload.recipe_id,
            is_purchased=False,
            created_at=now,
        )

    async def add_batch(self, payloads: list[ShoppingListCreate]) -> list[ShoppingListItem]:
        """Add multiple items to the shopping list in a single batch.

        Args:
            payloads: Collection of item creation payloads.

        Returns:
            List of created ShoppingListItem instances.
        """
        created: list[ShoppingListItem] = []
        for p in payloads:
            item = await self.add_item(p)
            created.append(item)
        return created

    async def update_purchased(self, item_id: str, is_purchased: bool) -> ShoppingListItem | None:
        """Update purchased status of a shopping list item.

        Args:
            item_id: Target item identifier.
            is_purchased: Boolean purchase status flag.

        Returns:
            Updated ShoppingListItem or None if not found.
        """
        # Find item by primary key identifier.
        doc = await self._collection.find_one({"$or": [{"_id": item_id}, {"id": item_id}]})
        if not doc:
            return None

        # Mutate purchase status in storage.
        await self._collection.update_one(
            {"$or": [{"_id": item_id}, {"id": item_id}]},
            {"$set": {"is_purchased": is_purchased}},
        )
        doc["is_purchased"] = is_purchased
        doc_id = str(doc.get("_id") or doc.get("id"))
        return ShoppingListItem(
            id=doc_id,
            name=doc.get("name", ""),
            quantity=float(doc.get("quantity", 1.0)),
            unit=doc.get("unit", "item"),
            recipe_id=doc.get("recipe_id"),
            is_purchased=is_purchased,
            created_at=doc.get("created_at") or datetime.now(UTC),
        )

    async def delete_item(self, item_id: str) -> bool:
        """Delete an item from the shopping list.

        Args:
            item_id: Target item identifier.

        Returns:
            True if item was deleted, False if item was not found.
        """
        # Remove item document matching identifier.
        result = await self._collection.delete_one({"$or": [{"_id": item_id}, {"id": item_id}]})
        return result.deleted_count > 0

    async def clear_purchased(self) -> int:
        """Remove all purchased items from the shopping list.

        Returns:
            Number of cleared items.
        """
        # Delete completed items to maintain a lean shopping list.
        result = await self._collection.delete_many({"is_purchased": True})
        return result.deleted_count
