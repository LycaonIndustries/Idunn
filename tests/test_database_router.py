"""Tests for DatabaseRouter attribute access, collection aliasing, and methods."""

from __future__ import annotations

import pytest

from backend.config import settings
from backend.db import DatabaseRouter, MongoClient


@pytest.mark.asyncio
async def test_database_router_attribute_and_item_access() -> None:
    """Verify that DatabaseRouter supports attribute and item lookup."""
    # Ensure in-memory fallback is active for testing.
    MongoClient.enable_in_memory_fallback()
    router = DatabaseRouter()

    # Attribute access should resolve collection wrappers without AttributeError.
    recipes_col = router.recipes
    assert recipes_col is not None

    shopping_col = router.shopping_list
    assert shopping_col is not None

    items_col = router.items
    assert items_col is not None

    # Item lookup should also resolve properly.
    assert router["recipes"] is not None
    assert router["shopping_lists"] is not None


@pytest.mark.asyncio
async def test_database_router_aliasing() -> None:
    """Verify that collection aliases point to canonical storage collections."""
    MongoClient.enable_in_memory_fallback()
    router = DatabaseRouter()

    # In mongodb mode, inventory maps to items.
    assert router._resolve_name("inventory") == "items"
    assert router._resolve_name("shopping_list") == "shopping_lists"
    assert router._resolve_name("recipes") == "recipes"


@pytest.mark.asyncio
async def test_database_router_list_collection_names() -> None:
    """Verify that list_collection_names returns list without throwing."""
    MongoClient.enable_in_memory_fallback()
    router = DatabaseRouter()

    names = await router.list_collection_names()
    assert isinstance(names, list)


@pytest.mark.asyncio
async def test_database_router_supabase_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify DatabaseRouter behavior when database_backend is supabase."""
    monkeypatch.setattr(settings, "database_backend", "supabase")
    router = DatabaseRouter()

    # Both attribute and item access should succeed under supabase configuration.
    recipes_col = router.recipes
    assert recipes_col is not None

    shopping_col = router.shopping_list
    assert shopping_col is not None

    inventory_col = router.inventory
    assert inventory_col is not None

    # Administrative commands should safely return ok without error.
    cmd_res = await router.command("ping")
    assert cmd_res.get("ok") == 1

    # list_collection_names should return collections list.
    names = await router.list_collection_names()
    assert "recipes" in names
    assert "items" in names


@pytest.mark.asyncio
async def test_database_router_missing_private_attribute() -> None:
    """Verify that private attribute lookups still raise AttributeError."""
    router = DatabaseRouter()
    with pytest.raises(AttributeError):
        _ = router._non_existent_private_attr
