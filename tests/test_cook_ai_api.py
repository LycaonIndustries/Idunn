"""Integration tests for the Cook AI what-can-i-cook API endpoint."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest


@pytest.fixture
async def seed_matching_data(db):
    """Seed test recipes and inventory items into mock database."""
    recipe1 = {
        "_id": "rec_101",
        "title": "Jeera Aloo",
        "ingredients": [
            {"name": "potato", "quantity": 500, "unit": "g"},
            {"name": "cumin", "quantity": 10, "unit": "g"},
        ],
        "steps": [{"step_number": 1, "instruction": "Boil potatoes"}],
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    recipe2 = {
        "_id": "rec_102",
        "title": "Paneer Butter Masala",
        "ingredients": [
            {"name": "paneer", "quantity": 250, "unit": "g"},
            {"name": "butter", "quantity": 50, "unit": "g"},
            {"name": "tomato", "quantity": 200, "unit": "g"},
        ],
        "steps": [{"step_number": 1, "instruction": "Sauté paneer"}],
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    await db.recipes.insert_many([recipe1, recipe2])

    item1 = {
        "_id": "item_1",
        "name": "potato",
        "quantity": 1000.0,
        "unit": "g",
        "location": "fridge",
        "consumed": False,
        "added_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    item2 = {
        "_id": "item_2",
        "name": "cumin",
        "quantity": 100.0,
        "unit": "g",
        "location": "spice_box",
        "consumed": False,
        "added_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    await db.inventory.insert_many([item1, item2])


@pytest.mark.asyncio
async def test_what_can_i_cook_endpoint_all(api_client, seed_matching_data):
    """Verify endpoint ranks all recipes descending by coverage."""
    response = api_client.get("/api/v1/cook-ai/what-can-i-cook")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2

    # Jeera Aloo has 100% ingredients in stock
    first = data[0]
    assert first["recipe_id"] == "rec_101"
    assert first["recipe_title"] == "Jeera Aloo"
    assert first["can_cook_now"] is True
    assert first["coverage_percentage"] == 100.0

    # Paneer Butter Masala is missing ingredients
    second = data[1]
    assert second["recipe_id"] == "rec_102"
    assert second["can_cook_now"] is False


@pytest.mark.asyncio
async def test_what_can_i_cook_endpoint_ready_only(api_client, seed_matching_data):
    """Verify ready_only filter returns exclusively 100% ready recipes."""
    response = api_client.get("/api/v1/cook-ai/what-can-i-cook?ready_only=true")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["recipe_title"] == "Jeera Aloo"
    assert data[0]["can_cook_now"] is True
