"""Supabase client and collection adapter for Iðunn.

Provides an async interface for Supabase (PostgreSQL + JSONB) with:
1. Real Supabase integration when SUPABASE_URL and SUPABASE_KEY are provided.
2. In-memory fallback (using mongomock_motor) when credentials are not configured or offline.
"""

from __future__ import annotations

import asyncio
import contextlib
from datetime import datetime
from typing import Any
from uuid import uuid4

from bson import ObjectId
from supabase import Client, create_client

from ..config import settings
from .resilience import with_db_retry


def _format_id(val: Any) -> str:
    """Format MongoDB ObjectId or raw scalar into a string identifier.

    Args:
        val: Unique ID value, either ObjectId, string, or None.

    Returns:
        String identifier representation.
    """
    if isinstance(val, ObjectId):
        return str(val)
    return str(val) if val is not None else str(uuid4())


class SupabaseCursor:
    """Cursor wrapper for Supabase queries supporting sort, skip, limit, and async iteration."""

    def __init__(self, data: list[dict[str, Any]]) -> None:
        """Initialize in-memory cursor with document list.

        Args:
            data: Raw document dictionaries returned by storage.
        """
        self._data = data
        self._skip = 0
        self._limit = len(data)
        self._sort_key: str | None = None
        self._sort_reverse: bool = False

    def sort(self, key_or_list: Any, direction: int = 1) -> SupabaseCursor:
        """Apply sorting key and direction to the cursor.

        Args:
            key_or_list: Sort attribute name or list of (key, direction) tuples.
            direction: 1 for ascending sort, -1 for descending sort.

        Returns:
            Self cursor reference for chaining.
        """
        # Parse MongoDB tuple format or direct string field name.
        if isinstance(key_or_list, list) and key_or_list:
            key, direction = key_or_list[0]
            self._sort_key = key
            self._sort_reverse = direction == -1
        elif isinstance(key_or_list, str):
            self._sort_key = key_or_list
            self._sort_reverse = direction == -1
        return self

    def skip(self, count: int) -> SupabaseCursor:
        """Set number of records to skip for pagination.

        Args:
            count: Number of initial records to skip.

        Returns:
            Self cursor reference for chaining.
        """
        self._skip = count
        return self

    def limit(self, count: int) -> SupabaseCursor:
        """Set maximum number of records to return.

        Args:
            count: Maximum record count.

        Returns:
            Self cursor reference for chaining.
        """
        self._limit = count
        return self

    def _execute(self) -> list[dict[str, Any]]:
        """Slice and sort internal document list according to cursor options.

        Returns:
            Processed list of document dictionaries.
        """
        res = list(self._data)
        if self._sort_key:
            res.sort(
                key=lambda x: (x.get(self._sort_key) is None, x.get(self._sort_key)),
                reverse=self._sort_reverse,
            )
        start = self._skip
        end = start + self._limit
        return res[start:end]

    def __aiter__(self) -> SupabaseCursor:
        """Begin asynchronous iteration over results.

        Returns:
            Self cursor reference.
        """
        self._iter_data = iter(self._execute())
        return self

    async def __anext__(self) -> dict[str, Any]:
        """Fetch next document from the cursor.

        Returns:
            Next document dictionary.

        Raises:
            StopAsyncIteration: When no further documents remain.
        """
        try:
            return next(self._iter_data)
        except StopIteration:
            raise StopAsyncIteration from None


class InsertResult:
    """Result object returned from insert_one operations."""

    def __init__(self, inserted_id: Any) -> None:
        """Initialize insertion result with created identifier.

        Args:
            inserted_id: Created document identifier.
        """
        self.inserted_id = inserted_id


class DeleteResult:
    """Result object returned from delete_one operations."""

    def __init__(self, deleted_count: int) -> None:
        """Initialize deletion result with modified row count.

        Args:
            deleted_count: Number of deleted rows.
        """
        self.deleted_count = deleted_count


class UpdateResult:
    """Result object returned from update_one operations."""

    def __init__(self, modified_count: int) -> None:
        """Initialize update result with modified row count.

        Args:
            modified_count: Number of modified rows.
        """
        self.modified_count = modified_count


class SupabaseCollection:
    """Collection wrapper that writes to Supabase table or in-memory fallback."""

    def __init__(
        self,
        table_name: str,
        supabase_client: Client | None,
        memory_collection: Any,
    ) -> None:
        """Initialize collection adapter with live Supabase client and fallback cache.

        Args:
            table_name: Target Postgres table name.
            supabase_client: Authenticated Supabase client or None.
            memory_collection: In-memory collection handle.
        """
        self.table_name = table_name
        self.client = supabase_client
        self.memory = memory_collection

    @property
    def is_live_supabase(self) -> bool:
        """Check if active cloud connection exists.

        Returns:
            True if client is connected to Supabase cloud, otherwise False.
        """
        return self.client is not None

    def _clean_doc_for_supabase(self, doc: dict[str, Any]) -> dict[str, Any]:
        """Sanitize document fields for PostgREST JSON serialization.

        Args:
            doc: Raw Python document.

        Returns:
            Sanitized dictionary ready for Supabase insertion.
        """
        cleaned = dict(doc)
        raw_id = cleaned.pop("_id", None) or cleaned.get("id") or str(uuid4())
        cleaned["id"] = _format_id(raw_id)
        # Convert datetime objects to ISO strings for PostgREST compatibility.
        for k, v in list(cleaned.items()):
            if isinstance(v, datetime):
                cleaned[k] = v.isoformat()
            elif isinstance(v, ObjectId):
                cleaned[k] = str(v)
        return cleaned

    def _restore_id(self, doc: dict[str, Any]) -> dict[str, Any]:
        """Ensure both 'id' and '_id' keys exist for caller compatibility.

        Args:
            doc: Document dictionary from Supabase.

        Returns:
            Dictionary with synchronized id and _id fields.
        """
        res = dict(doc)
        if "id" in res and "_id" not in res:
            res["_id"] = res["id"]
        elif "_id" in res and "id" not in res:
            res["id"] = str(res["_id"])
        return res

    @with_db_retry()
    async def _execute_remote_insert(
        self, loop: asyncio.AbstractEventLoop, clean: dict[str, Any]
    ) -> Any:
        """Execute remote Supabase insert with exponential backoff on transient errors."""
        return await loop.run_in_executor(
            None,
            lambda: self.client.table(self.table_name).insert(clean).execute(),
        )

    @with_db_retry()
    async def _execute_remote_find_one(self, loop: asyncio.AbstractEventLoop, str_id: str) -> Any:
        """Execute remote Supabase primary key lookup with exponential backoff."""
        return await loop.run_in_executor(
            None,
            lambda: self.client.table(self.table_name).select("*").eq("id", str_id).execute(),
        )

    @with_db_retry()
    async def _execute_remote_update(
        self,
        loop: asyncio.AbstractEventLoop,
        str_id: str,
        clean_updates: dict[str, Any],
    ) -> Any:
        """Execute remote Supabase row update with exponential backoff."""
        return await loop.run_in_executor(
            None,
            lambda: (
                self.client.table(self.table_name).update(clean_updates).eq("id", str_id).execute()
            ),
        )

    @with_db_retry()
    async def _execute_remote_delete(self, loop: asyncio.AbstractEventLoop, str_id: str) -> Any:
        """Execute remote Supabase row deletion with exponential backoff."""
        return await loop.run_in_executor(
            None,
            lambda: self.client.table(self.table_name).delete().eq("id", str_id).execute(),
        )

    async def insert_one(self, doc: dict[str, Any]) -> InsertResult:
        """Insert a single document into Supabase and local cache.

        Args:
            doc: Document payload dictionary.

        Returns:
            InsertResult containing created document identifier.
        """
        if not self.is_live_supabase:
            res = await self.memory.insert_one(doc)
            return InsertResult(res.inserted_id)

        clean = self._clean_doc_for_supabase(doc)
        loop = asyncio.get_running_loop()
        try:
            # Dispatch synchronous PostgREST call with exponential backoff on network errors.
            await self._execute_remote_insert(loop, clean)
            await self.memory.insert_one(dict(clean, _id=clean["id"]))
            return InsertResult(clean["id"])
        except Exception:
            # Fall back to local memory if remote network fails.
            res = await self.memory.insert_one(doc)
            return InsertResult(res.inserted_id)

    async def find_one(self, filter_query: dict[str, Any]) -> dict[str, Any] | None:
        """Find a single document matching criteria.

        Args:
            filter_query: Query criteria dictionary.

        Returns:
            Matching document or None if not found.
        """
        if not self.is_live_supabase:
            doc = await self.memory.find_one(filter_query)
            return self._restore_id(doc) if doc else None

        # Query directly by primary key when filter contains id.
        doc_id = filter_query.get("_id") or filter_query.get("id")
        if doc_id:
            str_id = _format_id(doc_id)
            loop = asyncio.get_running_loop()
            try:
                res = await self._execute_remote_find_one(loop, str_id)
                if res.data and len(res.data) > 0:
                    return self._restore_id(res.data[0])
            except Exception:
                pass

        # Fall back to in-memory store for complex filters.
        doc = await self.memory.find_one(filter_query)
        return self._restore_id(doc) if doc else None

    def find(self, filter_query: dict[str, Any] | None = None) -> Any:
        """Execute query across records.

        Args:
            filter_query: Optional criteria dictionary.

        Returns:
            Cursor supporting pagination and sorting.
        """
        # Delegate to memory collection for rich MongoDB operator support.
        return self.memory.find(filter_query or {})

    async def update_one(
        self,
        filter_query: dict[str, Any],
        update: dict[str, Any],
    ) -> UpdateResult:
        """Update a single document matching query.

        Args:
            filter_query: Selection criteria dictionary.
            update: Mutation operations dictionary.

        Returns:
            UpdateResult with modified document count.
        """
        res = await self.memory.update_one(filter_query, update)
        if self.is_live_supabase:
            doc_id = filter_query.get("_id") or filter_query.get("id")
            if doc_id and "$set" in update:
                str_id = _format_id(doc_id)
                clean_updates = self._clean_doc_for_supabase(update["$set"])
                clean_updates.pop("id", None)
                loop = asyncio.get_running_loop()
                with contextlib.suppress(Exception):
                    await self._execute_remote_update(loop, str_id, clean_updates)
        return UpdateResult(res.modified_count if hasattr(res, "modified_count") else 1)

    async def delete_one(self, filter_query: dict[str, Any]) -> DeleteResult:
        """Delete a single document matching query.

        Args:
            filter_query: Selection criteria dictionary.

        Returns:
            DeleteResult with deleted document count.
        """
        res = await self.memory.delete_one(filter_query)
        if self.is_live_supabase:
            doc_id = filter_query.get("_id") or filter_query.get("id")
            if doc_id:
                str_id = _format_id(doc_id)
                loop = asyncio.get_running_loop()
                with contextlib.suppress(Exception):
                    await self._execute_remote_delete(loop, str_id)
        return DeleteResult(res.deleted_count if hasattr(res, "deleted_count") else 1)

    async def delete_many(self, filter_query: dict[str, Any]) -> DeleteResult:
        """Delete multiple documents matching criteria.

        Args:
            filter_query: Selection criteria dictionary.

        Returns:
            DeleteResult with deleted document count.
        """
        res = await self.memory.delete_many(filter_query)
        count = getattr(res, "deleted_count", 0)
        return DeleteResult(count)

    async def insert_many(self, docs: list[dict[str, Any]]) -> Any:
        """Insert multiple documents in batch.

        Args:
            docs: List of document payloads to store.

        Returns:
            Batch insertion result handle.
        """
        for doc in docs:
            if "_id" not in doc:
                doc["_id"] = _format_id(None)
        return await self.memory.insert_many(docs)

    async def find_one_and_update(
        self,
        filter_query: dict[str, Any],
        update: dict[str, Any],
        **kwargs: Any,
    ) -> dict[str, Any] | None:
        """Find a single document and apply mutations atomically.

        Args:
            filter_query: Query criteria to locate record.
            update: Mutation operator dictionary ($set, etc.).
            **kwargs: Additional update flags (upsert, return_document).

        Returns:
            Mutated document dictionary or None.
        """
        return await self.memory.find_one_and_update(filter_query, update, **kwargs)

    def aggregate(self, pipeline: list[dict[str, Any]]) -> Any:
        """Execute aggregation pipeline against underlying storage.

        Args:
            pipeline: MongoDB aggregation pipeline stages.

        Returns:
            Async iterator or cursor yielding aggregation results.
        """
        return self.memory.aggregate(pipeline)

    async def count_documents(self, filter_query: dict[str, Any] | None = None) -> int:
        """Count total documents matching criteria.

        Args:
            filter_query: Optional selection criteria.

        Returns:
            Total count of matching documents.
        """
        return await self.memory.count_documents(filter_query or {})


class SupabaseClientManager:
    """Manages Supabase connection and collections with seamless in-memory fallback."""

    _supabase_client: Client | None = None
    _memory_db: Any = None
    _collections: dict[str, SupabaseCollection] = {}
    _hydrated_tables: set[str] = set()

    @classmethod
    async def hydrate_table(cls, table_name: str) -> None:
        """Hydrate in-memory collection cache from remote Supabase table.

        Args:
            table_name: Canonical collection or table name to hydrate.
        """
        # Skip if already hydrated or if running without cloud credentials.
        if table_name in cls._hydrated_tables or not cls.is_configured():
            return
        sb = cls.get_supabase_client()
        if sb is None:
            return
        loop = asyncio.get_running_loop()
        try:
            res = await loop.run_in_executor(
                None,
                lambda: sb.table(table_name).select("*").execute(),
            )
            if res.data:
                mem_col = cls.get_memory_db()[table_name]
                await mem_col.delete_many({})
                for row in res.data:
                    doc = dict(row)
                    if "id" in doc and "_id" not in doc:
                        doc["_id"] = doc["id"]
                    await mem_col.insert_one(doc)
            cls._hydrated_tables.add(table_name)
        except Exception:
            # Table might not exist yet in remote schema.
            pass

    @classmethod
    async def hydrate_all(cls) -> None:
        """Hydrate primary data collections from Supabase on application startup."""
        if not cls.is_configured():
            return
        tables = [
            "recipes",
            "items",
            "ingredients",
            "meal_plans",
            "shopping_lists",
            "receipts",
            "settings",
        ]
        for table in tables:
            await cls.hydrate_table(table)

    @classmethod
    def get_memory_db(cls) -> Any:
        """Get or initialize in-memory database mock.

        Returns:
            Async in-memory MongoDB client handle.
        """
        if cls._memory_db is None:
            from mongomock_motor import AsyncMongoMockClient

            cls._memory_db = AsyncMongoMockClient()["idunn_db"]
        return cls._memory_db

    @classmethod
    def get_supabase_client(cls) -> Client | None:
        """Get or create singleton Supabase client.

        Returns:
            Authenticated Supabase Client or None.
        """
        # Connect to Supabase when URL and credentials are both configured.
        if cls._supabase_client is None and settings.supabase_url and settings.supabase_key:
            try:
                cls._supabase_client = create_client(
                    settings.supabase_url,
                    settings.supabase_key,
                )
            except Exception as exc:
                print(f"Supabase connection warning: {exc}")
                cls._supabase_client = None
        return cls._supabase_client

    @classmethod
    def get_collection(cls, name: str) -> SupabaseCollection:
        """Retrieve wrapped collection adapter by table name.

        Args:
            name: Postgres table or collection name.

        Returns:
            Configured SupabaseCollection adapter.
        """
        if name not in cls._collections:
            sb = cls.get_supabase_client()
            mem = cls.get_memory_db()[name]
            cls._collections[name] = SupabaseCollection(name, sb, mem)
        return cls._collections[name]

    @classmethod
    def reset(cls) -> None:
        """Reset cached client connection and collections after settings change."""
        cls._supabase_client = None
        cls._collections.clear()
        cls._hydrated_tables.clear()

    @classmethod
    async def _execute_ping(cls, loop: asyncio.AbstractEventLoop, sb: Client) -> None:
        """Execute ping query against Supabase database."""
        await loop.run_in_executor(
            None,
            lambda: sb.table("recipes").select("id").limit(1).execute(),
        )

    @classmethod
    async def ping(cls) -> bool:
        """Check if Supabase cloud database responds.

        Returns:
            True if cloud or in-memory database is operational, otherwise False.
        """
        sb = cls.get_supabase_client()
        if sb is not None:
            try:
                loop = asyncio.get_running_loop()
                await cls._execute_ping(loop, sb)
                return True
            except Exception:
                return False
        # In-memory store is always ready when no credentials are provided.
        return True

    @classmethod
    def is_configured(cls) -> bool:
        """Check if valid Supabase cloud credentials are set.

        Returns:
            True if project URL and key are configured, otherwise False.
        """
        return bool(settings.supabase_url and settings.supabase_key)
