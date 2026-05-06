"""MongoDB connection and collection management for Iðunn."""

from __future__ import annotations

from typing import AsyncGenerator

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pydantic import BaseModel

from ..config import settings


class MongoClient:
    """Singleton MongoDB client wrapper."""

    _client: AsyncIOMotorClient | None = None
    _db: AsyncIOMotorDatabase | None = None

    @classmethod
    def get_client(cls) -> AsyncIOMotorClient:
        """Get or create MongoDB client."""
        if cls._client is None:
            cls._client = AsyncIOMotorClient(settings.mongodb_url)
        return cls._client

    @classmethod
    def get_db(cls) -> AsyncIOMotorDatabase:
        """Get or create database reference."""
        if cls._db is None:
            cls._db = cls.get_client()[settings.mongodb_db_name]
        return cls._db

    @classmethod
    async def close(cls) -> None:
        """Close MongoDB connection."""
        if cls._client is not None:
            cls._client.close()
            cls._client = None
            cls._db = None

    @classmethod
    async def ping(cls) -> bool:
        """Check MongoDB connectivity."""
        try:
            await cls.get_client().admin.command("ping")
            return True
        except Exception:
            return False


def get_db() -> AsyncGenerator[AsyncIOMotorDatabase, None]:
    """FastAPI dependency for database access."""
    yield MongoClient.get_db()


# Collection names
COLLECTION_ITEMS = "items"
COLLECTION_INGREDIENTS = "ingredients"
COLLECTION_RECIPES = "recipes"
COLLECTION_MEAL_PLANS = "meal_plans"
COLLECTION_SHOPPING_LISTS = "shopping_lists"
COLLECTION_RECEIPTS = "receipts"
COLLECTION_NUTRITION = "nutrition"
COLLECTION_EVAL_RUNS = "eval_runs"


class MongoDocument(BaseModel):
    """Base class for documents stored in MongoDB."""

    model_config = {"populate_by_name": True}

    @classmethod
    def get_collection_name(cls) -> str:
        """Return the MongoDB collection name for this document type."""
        raise NotImplementedError
