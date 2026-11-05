"""Database connection and collection management for Iðunn."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel

from ..config import settings


# Route collection requests to active storage engine.
class DatabaseRouter:
    """Routes collection lookups to Supabase or MongoDB based on configuration."""

    COLLECTION_ALIASES: dict[str, str] = {
        "inventory": "items",
        "shopping_list": "shopping_lists",
    }

    def _resolve_name(self, name: str) -> str:
        """Resolve canonical collection name using alias mappings.

        Args:
            name: Requested collection or table name.

        Returns:
            Canonical collection name.
        """
        return self.COLLECTION_ALIASES.get(name, name)

    def __getitem__(self, name: str) -> Any:
        """Resolve collection adapter by target collection name.

        Args:
            name: Table or collection name to resolve.

        Returns:
            Collection adapter instance for Supabase or MongoDB.
        """
        canonical_name = self._resolve_name(name)
        # Return Supabase client wrapper when configured for cloud storage.
        if settings.database_backend == "supabase":
            from .supabase_client import SupabaseClientManager

            return SupabaseClientManager.get_collection(canonical_name)
        return MongoClient.get_raw_db()[canonical_name]

    def __getattr__(self, name: str) -> Any:
        """Route attribute-based collection lookups (e.g., db.recipes, db.shopping_list).

        Args:
            name: Attribute collection name.

        Returns:
            Collection adapter instance.
        """
        if name.startswith("_"):
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
        return self[name]

    async def list_collection_names(self) -> list[str]:
        """List active collection or table names.

        Returns:
            List of collection names.
        """
        if settings.database_backend == "supabase":
            from .supabase_client import SupabaseClientManager

            return list(SupabaseClientManager._collections.keys()) or [
                COLLECTION_ITEMS,
                COLLECTION_INGREDIENTS,
                COLLECTION_RECIPES,
                COLLECTION_MEAL_PLANS,
                COLLECTION_SHOPPING_LISTS,
                COLLECTION_RECEIPTS,
                COLLECTION_NUTRITION,
                COLLECTION_EVAL_RUNS,
                COLLECTION_AI_USAGE,
            ]
        raw_db = MongoClient.get_raw_db()
        if hasattr(raw_db, "list_collection_names"):
            return await raw_db.list_collection_names()
        return []

    async def command(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        """Execute administrative command on active backend.

        Returns:
            Command execution status dictionary.
        """
        if settings.database_backend != "supabase":
            raw_db = MongoClient.get_raw_db()
            if hasattr(raw_db, "command"):
                return await raw_db.command(*args, **kwargs)
        return {"ok": 1}

    async def create_collection(self, name: str, **kwargs: Any) -> Any:
        """Create collection on active database backend.

        Args:
            name: Target collection name.
            **kwargs: Backend collection configuration arguments.

        Returns:
            Created or resolved collection adapter.
        """
        canonical_name = self._resolve_name(name)
        if settings.database_backend != "supabase":
            raw_db = MongoClient.get_raw_db()
            if hasattr(raw_db, "create_collection"):
                return await raw_db.create_collection(canonical_name, **kwargs)
        return self[canonical_name]


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
    def get_raw_db(cls) -> Any:
        """Get underlying MongoDB database instance without routing layer.

        Returns:
            Active MongoDB database instance.
        """
        if cls._db is None:
            cls._db = cls.get_client()[settings.mongodb_db_name]
        return cls._db

    @classmethod
    def get_db(cls) -> Any:
        """Get or initialize database reference.

        Returns:
            Database or router handle.
        """
        return _db_router

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
COLLECTION_AI_USAGE = "ai_usage"


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
