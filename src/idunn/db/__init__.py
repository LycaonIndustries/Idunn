"""MongoDB connection and collection management for Iðunn."""

from __future__ import annotations

from typing import Any, AsyncGenerator

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pydantic import BaseModel

from ..config import settings


class DatabaseRouter:
    """Routes collection lookups to Supabase or MongoDB based on configuration."""

    def __getitem__(self, name: str) -> Any:
        if settings.database_backend == "supabase":
            from .supabase_client import SupabaseClientManager

            return SupabaseClientManager.get_collection(name)
        return MongoClient.get_db()[name]


_db_router = DatabaseRouter()


class MongoClient:
    """Singleton Database client wrapper with Supabase & MongoDB support."""

    _client: Any = None
    _db: Any = None
    _is_mock: bool = False

    @classmethod
    def get_client(cls) -> Any:
        """Get or create client."""
        if cls._client is None:
            cls._client = AsyncIOMotorClient(
                settings.mongodb_url,
                serverSelectionTimeoutMS=2000,
            )
        return cls._client

    @classmethod
    def get_db(cls) -> Any:
        """Get or create database reference."""
        if settings.database_backend == "supabase":
            return _db_router
        if cls._db is None:
            cls._db = cls.get_client()[settings.mongodb_db_name]
        return cls._db

    @classmethod
    def enable_in_memory_fallback(cls) -> None:
        """Enable in-memory mock client when live database is unreachable."""
        try:
            from mongomock_motor import AsyncMongoMockClient

            cls._client = AsyncMongoMockClient()
            cls._db = cls._client[settings.mongodb_db_name]
            cls._is_mock = True
        except ImportError:
            pass

    @classmethod
    def is_mock(cls) -> bool:
        """True if running in in-memory fallback mode."""
        if settings.database_backend == "supabase":
            from .supabase_client import SupabaseClientManager

            return not SupabaseClientManager.is_configured()
        return cls._is_mock

    @classmethod
    async def close(cls) -> None:
        """Close connection."""
        if cls._client is not None and not cls._is_mock:
            cls._client.close()
        cls._client = None
        cls._db = None
        cls._is_mock = False

    @classmethod
    async def ping(cls) -> bool:
        """Check database connectivity."""
        if settings.database_backend == "supabase":
            from .supabase_client import SupabaseClientManager

            return await SupabaseClientManager.ping()
        if cls._is_mock:
            return True
        try:
            await cls.get_client().admin.command("ping")
            return True
        except Exception:
            return False


def get_db() -> AsyncGenerator[Any, None]:
    """FastAPI dependency for database access."""
    if settings.database_backend == "supabase":
        yield _db_router
    else:
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


def get_collection(collection_name: str):
    """Get a collection by name."""
    return MongoClient.get_db()[collection_name]


class MongoDocument(BaseModel):
    """Base class for documents stored in MongoDB."""

    model_config = {"populate_by_name": True}

    @classmethod
    def get_collection_name(cls) -> str:
        """Return the MongoDB collection name for this document type."""
        raise NotImplementedError
