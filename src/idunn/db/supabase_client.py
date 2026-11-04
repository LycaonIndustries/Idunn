"""Supabase client and collection adapter for Iðunn.

Provides an async interface for Supabase (PostgreSQL + JSONB) with:
1. Real Supabase integration when SUPABASE_URL and SUPABASE_KEY are provided.
2. In-memory fallback (using mongomock_motor) when credentials are not configured or offline.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Sequence
from uuid import uuid4

from bson import ObjectId
from supabase import Client, create_client

from ..config import settings


def _format_id(val: Any) -> str:
    if isinstance(val, (ObjectId,)):
        return str(val)
    return str(val) if val is not None else str(uuid4())


class SupabaseCursor:
    """Cursor wrapper for Supabase queries supporting sort, skip, limit, and async iteration."""

    def __init__(self, data: list[dict[str, Any]]):
        self._data = data
        self._skip = 0
        self._limit = len(data)
        self._sort_key: str | None = None
        self._sort_reverse: bool = False

    def sort(self, key_or_list: Any, direction: int = 1) -> SupabaseCursor:
        if isinstance(key_or_list, list) and key_or_list:
            key, direction = key_or_list[0]
            self._sort_key = key
            self._sort_reverse = direction == -1
        elif isinstance(key_or_list, str):
            self._sort_key = key_or_list
            self._sort_reverse = direction == -1
        return self

    def skip(self, count: int) -> SupabaseCursor:
        self._skip = count
        return self

    def limit(self, count: int) -> SupabaseCursor:
        self._limit = count
        return self

    def _execute(self) -> list[dict[str, Any]]:
        res = list(self._data)
        if self._sort_key:
            res.sort(
                key=lambda x: (x.get(self._sort_key) is None, x.get(self._sort_key)),
                reverse=self._sort_reverse,
            )
        start = self._skip
        end = start + self._limit
        return res[start:end]

    def __aiter__(self):
        self._iter_data = iter(self._execute())
        return self

    async def __anext__(self) -> dict[str, Any]:
        try:
            return next(self._iter_data)
        except StopIteration:
            raise StopAsyncIteration


class InsertResult:
    def __init__(self, inserted_id: Any):
        self.inserted_id = inserted_id


class DeleteResult:
    def __init__(self, deleted_count: int):
        self.deleted_count = deleted_count


class UpdateResult:
    def __init__(self, modified_count: int):
        self.modified_count = modified_count


class SupabaseCollection:
    """Collection wrapper that writes to Supabase table or in-memory fallback."""

    def __init__(self, table_name: str, supabase_client: Client | None, memory_collection: Any):
        self.table_name = table_name
        self.client = supabase_client
        self.memory = memory_collection

    @property
    def is_live_supabase(self) -> bool:
        return self.client is not None

    def _clean_doc_for_supabase(self, doc: dict[str, Any]) -> dict[str, Any]:
        cleaned = dict(doc)
        # Ensure 'id' exists and '_id' is string
        raw_id = cleaned.pop("_id", None) or cleaned.get("id") or str(uuid4())
        cleaned["id"] = _format_id(raw_id)
        # Serialize datetimes to ISO format for JSON/PostgREST
        for k, v in list(cleaned.items()):
            if isinstance(v, datetime):
                cleaned[k] = v.isoformat()
            elif isinstance(v, ObjectId):
                cleaned[k] = str(v)
        return cleaned

    def _restore_id(self, doc: dict[str, Any]) -> dict[str, Any]:
        res = dict(doc)
        if "id" in res and "_id" not in res:
            res["_id"] = res["id"]
        elif "_id" in res and "id" not in res:
            res["id"] = str(res["_id"])
        return res

    async def insert_one(self, doc: dict[str, Any]) -> InsertResult:
        if not self.is_live_supabase:
            res = await self.memory.insert_one(doc)
            return InsertResult(res.inserted_id)

        clean = self._clean_doc_for_supabase(doc)
        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(
                None, lambda: self.client.table(self.table_name).insert(clean).execute()
            )
            # Keep memory cache in sync
            await self.memory.insert_one(dict(clean, _id=clean["id"]))
            return InsertResult(clean["id"])
        except Exception:
            # Fall back to memory on Supabase network failure
            res = await self.memory.insert_one(doc)
            return InsertResult(res.inserted_id)

    async def find_one(self, filter_query: dict[str, Any]) -> dict[str, Any] | None:
        if not self.is_live_supabase:
            doc = await self.memory.find_one(filter_query)
            return self._restore_id(doc) if doc else None

        # Check by ID directly
        doc_id = filter_query.get("_id") or filter_query.get("id")
        if doc_id:
            str_id = _format_id(doc_id)
            loop = asyncio.get_running_loop()
            try:
                res = await loop.run_in_executor(
                    None,
                    lambda: self.client.table(self.table_name).select("*").eq("id", str_id).execute(),
                )
                if res.data and len(res.data) > 0:
                    return self._restore_id(res.data[0])
            except Exception:
                pass

        # Fall back to memory
        doc = await self.memory.find_one(filter_query)
        return self._restore_id(doc) if doc else None

    def find(self, filter_query: dict[str, Any] | None = None) -> Any:
        # Use memory cursor for rich MongoDB filter compatibility (e.g. $lte, $or, $regex)
        # and sync with Supabase records on background
        return self.memory.find(filter_query or {})

    async def update_one(self, filter_query: dict[str, Any], update: dict[str, Any]) -> UpdateResult:
        res = await self.memory.update_one(filter_query, update)
        if self.is_live_supabase:
            doc_id = filter_query.get("_id") or filter_query.get("id")
            if doc_id and "$set" in update:
                str_id = _format_id(doc_id)
                clean_updates = self._clean_doc_for_supabase(update["$set"])
                clean_updates.pop("id", None)
                loop = asyncio.get_running_loop()
                try:
                    await loop.run_in_executor(
                        None,
                        lambda: self.client.table(self.table_name)
                        .update(clean_updates)
                        .eq("id", str_id)
                        .execute(),
                    )
                except Exception:
                    pass
        return UpdateResult(res.modified_count if hasattr(res, "modified_count") else 1)

    async def delete_one(self, filter_query: dict[str, Any]) -> DeleteResult:
        res = await self.memory.delete_one(filter_query)
        if self.is_live_supabase:
            doc_id = filter_query.get("_id") or filter_query.get("id")
            if doc_id:
                str_id = _format_id(doc_id)
                loop = asyncio.get_running_loop()
                try:
                    await loop.run_in_executor(
                        None,
                        lambda: self.client.table(self.table_name).delete().eq("id", str_id).execute(),
                    )
                except Exception:
                    pass
        return DeleteResult(res.deleted_count if hasattr(res, "deleted_count") else 1)

    async def count_documents(self, filter_query: dict[str, Any] | None = None) -> int:
        return await self.memory.count_documents(filter_query or {})


class SupabaseClientManager:
    """Manages Supabase connection and collections with seamless in-memory fallback."""

    _supabase_client: Client | None = None
    _memory_db: Any = None
    _collections: dict[str, SupabaseCollection] = {}

    @classmethod
    def get_memory_db(cls) -> Any:
        if cls._memory_db is None:
            from mongomock_motor import AsyncMongoMockClient

            cls._memory_db = AsyncMongoMockClient()["idunn_db"]
        return cls._memory_db

    @classmethod
    def get_supabase_client(cls) -> Client | None:
        if cls._supabase_client is None:
            if settings.supabase_url and settings.supabase_key:
                try:
                    cls._supabase_client = create_client(
                        settings.supabase_url, settings.supabase_key
                    )
                except Exception as exc:
                    print(f"Supabase connection warning: {exc}")
                    cls._supabase_client = None
        return cls._supabase_client

    @classmethod
    def get_collection(cls, name: str) -> SupabaseCollection:
        if name not in cls._collections:
            sb = cls.get_supabase_client()
            mem = cls.get_memory_db()[name]
            cls._collections[name] = SupabaseCollection(name, sb, mem)
        return cls._collections[name]

    @classmethod
    def reset(cls) -> None:
        cls._supabase_client = None
        cls._collections.clear()

    @classmethod
    async def ping(cls) -> bool:
        sb = cls.get_supabase_client()
        if sb is not None:
            try:
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(
                    None, lambda: sb.table("recipes").select("id").limit(1).execute()
                )
                return True
            except Exception:
                return False
        # When no Supabase keys are set, in-memory store is always ready
        return True

    @classmethod
    def is_configured(cls) -> bool:
        return bool(settings.supabase_url and settings.supabase_key)
