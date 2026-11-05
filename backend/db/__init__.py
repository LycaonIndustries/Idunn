"""Database connection and collection management for Iðunn."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel

from ..config import settings
from .resilience import with_db_retry


# Route collection requests to active storage engine.
class DatabaseRouter:
    """Routes collection lookups to Supabase or MongoDB based on configuration."""

    def __getitem__(self, name: str) -> Any:
        """Resolve collection adapter by target collection name.

        Args:
            name: Table or collection name to resolve.

        Returns:
            Collection adapter instance for Supabase or MongoDB.
        """
        # Return Supabase client wrapper when configured for cloud storage.
        if settings.database_backend == "supabase":
            from .supabase_client import SupabaseClientManager

            return SupabaseClientManager.get_collection(name)
        return MongoClient.get_db()[name]


_db_router = DatabaseRouter()


# Manage singleton connection lifecycle across requests.
class MongoClient:
    """Singleton Database client wrapper with Supabase & MongoDB support."""

    _client: Any = None
    _db: Any = None
    _is_mock: bool = False

    @classmethod
    def get_client(cls) -> Any:
        """Get or initialize the underlying database client connection.

        Returns:
            Active client driver instance.
        """
        # Create client connection only once to preserve connection pooling.
        if cls._client is None:
            cls._client = AsyncIOMotorClient(
                settings.mongodb_url,
                serverSelectionTimeoutMS=2000,
            )
        return cls._client

    @classmethod
    def get_db(cls) -> Any:
        """Get or initialize database reference.

        Returns:
            Database or router handle.
        """
        if settings.database_backend == "supabase":
            return _db_router
        if cls._db is None:
            cls._db = cls.get_client()[settings.mongodb_db_name]
        return cls._db

    @classmethod
    def enable_in_memory_fallback(cls) -> None:
        """Enable in-memory mock client when live database is unreachable."""
        # Use in-memory mock so developers can build features without running Docker.
        try:
            from mongomock_motor import AsyncMongoMockClient

            cls._client = AsyncMongoMockClient()
            cls._db = cls._client[settings.mongodb_db_name]
            cls._is_mock = True
        except ImportError:
            pass

    @classmethod
    def is_mock(cls) -> bool:
        """Check whether current storage engine is operating in mock mode.

        Returns:
            True if running in mock mode, otherwise False.
        """
        if settings.database_backend == "supabase":
            from .supabase_client import SupabaseClientManager

            return not SupabaseClientManager.is_configured()
        return cls._is_mock

    @classmethod
    async def close(cls) -> None:
        """Close database connection pool on server shutdown."""
        # Cleanly release socket resources when terminating processes.
        if cls._client is not None and not cls._is_mock:
            cls._client.close()
        cls._client = None
        cls._db = None
        cls._is_mock = False

    @classmethod
    @with_db_retry(max_attempts=2, initial_delay=0.1, max_delay=0.5)
    async def _execute_ping(cls) -> bool:
        """Run ping admin command against MongoDB socket."""
        await cls.get_client().admin.command("ping")
        return True

    @classmethod
    async def ping(cls) -> bool:
        """Verify database connectivity.

        Returns:
            True if database responds to ping command, otherwise False.
        """
        # Check Supabase connectivity when operating under cloud storage mode.
        if settings.database_backend == "supabase":
            from .supabase_client import SupabaseClientManager

            return await SupabaseClientManager.ping()
        if cls._is_mock:
            return True
        try:
            return await cls._execute_ping()
        except Exception:
            return False


def get_db() -> AsyncGenerator[Any]:
    """Provide FastAPI dependency for database access.

    Yields:
        Database or collection router instance for the request lifecycle.
    """
    # Supply correct database router depending on current configuration.
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


def get_collection(collection_name: str) -> Any:
    """Retrieve collection adapter by name.

    Args:
        collection_name: Name of target collection.

    Returns:
        Collection adapter instance.
    """
    return MongoClient.get_db()[collection_name]


class MongoDocument(BaseModel):
    """Base class for documents stored in database collections."""

    model_config = {"populate_by_name": True}

    @classmethod
    def get_collection_name(cls) -> str:
        """Return the collection name for this document type.

        Returns:
            Collection name string.

        Raises:
            NotImplementedError: Subclasses must provide collection name.
        """
        raise NotImplementedError
