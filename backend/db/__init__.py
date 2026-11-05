"""Database connection and collection management for Iðunn.

Standardized exclusively on Supabase Cloud PostgreSQL with in-memory fallback.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from pydantic import BaseModel

from .supabase_client import SupabaseClientManager

# Canonical collection names
COLLECTION_ITEMS = "items"
COLLECTION_INGREDIENTS = "ingredients"
COLLECTION_RECIPES = "recipes"
COLLECTION_MEAL_PLANS = "meal_plans"
COLLECTION_SHOPPING_LISTS = "shopping_lists"
COLLECTION_RECEIPTS = "receipts"
COLLECTION_NUTRITION = "nutrition"
COLLECTION_EVAL_RUNS = "eval_runs"
COLLECTION_AI_USAGE = "ai_usage"

ALL_COLLECTIONS = [
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


class DatabaseRouter:
    """Routes collection lookups directly to Supabase client manager."""

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
            Supabase collection adapter instance.
        """
        canonical_name = self._resolve_name(name)
        return SupabaseClientManager.get_collection(canonical_name)

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
        return list(SupabaseClientManager._collections.keys()) or list(ALL_COLLECTIONS)

    async def command(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        """Execute administrative status command.

        Returns:
            Command execution status dictionary.
        """
        return {"ok": 1}

    async def create_collection(self, name: str, **kwargs: Any) -> Any:
        """Create or resolve collection adapter on Supabase backend.

        Args:
            name: Target collection name.
            **kwargs: Extra arguments.

        Returns:
            Resolved collection adapter.
        """
        canonical_name = self._resolve_name(name)
        return self[canonical_name]


_db_router = DatabaseRouter()


class DatabaseClient:
    """Singleton Database manager backed by Supabase."""

    @classmethod
    def get_db(cls) -> Any:
        """Get database router reference.

        Returns:
            Database router handle.
        """
        return _db_router

    @classmethod
    def get_raw_db(cls) -> Any:
        """Get underlying database reference.

        Returns:
            Database router handle.
        """
        return _db_router

    @classmethod
    def enable_in_memory_fallback(cls) -> None:
        """Enable in-memory storage mode when running without remote credentials."""
        # SupabaseClientManager automatically operates in-memory when unconfigured.
        pass

    @classmethod
    def is_mock(cls) -> bool:
        """Check whether current storage engine is operating in mock mode.

        Returns:
            True if running without live Supabase credentials.
        """
        return not SupabaseClientManager.is_configured()

    @classmethod
    async def close(cls) -> None:
        """Close database resources on server shutdown."""
        pass

    @classmethod
    async def ping(cls) -> bool:
        """Verify database connectivity.

        Returns:
            True if database responds to ping command, otherwise False.
        """
        return await SupabaseClientManager.ping()


# Backwards compatibility alias
MongoClient = DatabaseClient


def get_db() -> AsyncGenerator[Any]:
    """Provide FastAPI dependency for database access.

    Yields:
        Database collection router instance for the request lifecycle.
    """
    yield _db_router


def get_collection(collection_name: str) -> Any:
    """Retrieve collection adapter by name.

    Args:
        collection_name: Name of target collection.

    Returns:
        Collection adapter instance.
    """
    return _db_router[collection_name]


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
