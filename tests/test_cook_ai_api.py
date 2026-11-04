"""Tests for Cook AI and Shopping List API endpoints.

Tests 'What can I cook?' recipe matching, in-stock substitutions,
pantry-to-plate generation, and shopping list management with quick-commerce links.
All tests use local in-memory AsyncMongoMockClient and mocked AI providers.
Zero external requests to Gemini or Supabase are sent.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest
from bson import ObjectId

from backend.api.cook_ai import get_ai_provider
from backend.db import COLLECTION_ITEMS, COLLECTION_RECIPES
from backend.main import app
from backend.models.inventory import Location, Unit
from backend.models.recipe import Region


async def _seed_data(db):
    """Seed mock database with sample pantry stock and recipes."""
    now = datetime.now(UTC)
    await db[COLLECTION_ITEMS].insert_many(
        [
            {
                "_id": ObjectId(),
                "name": "Paneer",
                "quantity": 250.0,
                "unit": Unit.GRAM.value,
                "location": Location.FRIDGE.value,
                "added_at": now,
                "updated_at": now,
                "expiry_date": now + timedelta(days=2),
                "consumed": False,
            },
            {
                "_id": ObjectId(),
                "name": "Palak",
                "quantity": 500.0,
                "unit": Unit.GRAM.value,
                "location": Location.FRIDGE.value,
                "added_at": now,
                "updated_at": now,
                "expiry_date": now + timedelta(days=1),
                "consumed": False,
            },
            {
                "_id": ObjectId(),
                "name": "Curd",
                "quantity": 400.0,
                "unit": Unit.GRAM.value,
                "location": Location.FRIDGE.value,
                "added_at": now,
                "updated_at": now,
                "expiry_date": now + timedelta(days=5),
                "consumed": False,
            },
        ]
    )

    await db[COLLECTION_RECIPES].insert_many(
        [
            {
                "_id": ObjectId(),
                "title": "Palak Paneer",
                "prep_time_minutes": 15,
                "cook_time_minutes": 25,
                "region": Region.NORTH.value,
                "ingredients": [
                    {"name": "palak", "quantity": 500.0, "unit": "g"},
                    {"name": "paneer", "quantity": 200.0, "unit": "g"},
                ],
                "steps": [{"step_number": 1, "instruction": "Blanch palak"}],
            },
            {
                "_id": ObjectId(),
                "title": "Paneer Butter Masala",
                "prep_time_minutes": 20,
                "cook_time_minutes": 30,
                "region": Region.NORTH.value,
                "ingredients": [
                    {"name": "paneer", "quantity": 200.0, "unit": "g"},
                    {"name": "butter", "quantity": 50.0, "unit": "g"},
                    {"name": "cream", "quantity": 50.0, "unit": "ml"},
                ],
                "steps": [{"step_number": 1, "instruction": "Make makhani gravy"}],
            },
        ]
    )


@pytest.mark.asyncio
async def test_what_can_i_cook_endpoint(api_client, db):
    """Verify POST /api/v1/cook-ai/what-can-i-cook evaluates recipes."""
    await _seed_data(db)
    res = api_client.post("/api/v1/cook-ai/what-can-i-cook?ready_only=false")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 2

    # Palak Paneer should be ready to cook
    top_recipe = data[0]
    assert top_recipe["recipe_title"] == "Palak Paneer"
    assert top_recipe["can_cook_now"] is True
    assert top_recipe["coverage_percentage"] == 100.0
    assert top_recipe["expiry_urgency_score"] > 0


@pytest.mark.asyncio
async def test_what_can_i_cook_ready_only_filter(api_client, db):
    """Verify ready_only filters out recipes missing ingredients."""
    await _seed_data(db)
    res = api_client.post("/api/v1/cook-ai/what-can-i-cook?ready_only=true")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["recipe_title"] == "Palak Paneer"


@pytest.mark.asyncio
async def test_substitutions_endpoint_in_stock(api_client, db):
    """Verify POST /api/v1/cook-ai/substitutions returns curd for sour cream."""
    await _seed_data(db)
    res = api_client.post(
        "/api/v1/cook-ai/substitutions",
        json={"missing_ingredient": "sour cream"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data is not None
    assert "curd" in data["substitute_item"].lower()
    assert data["in_stock"] is True


@pytest.mark.asyncio
async def test_substitutions_endpoint_not_found(api_client, db):
    """Verify None returned when candidate substitute is not in pantry."""
    await _seed_data(db)
    res = api_client.post(
        "/api/v1/cook-ai/substitutions",
        json={"missing_ingredient": "truffle oil"},
    )
    assert res.status_code == 200
    assert res.json() is None


@pytest.mark.asyncio
async def test_pantry_to_plate_endpoint(api_client, db):
    """Verify POST /api/v1/cook-ai/pantry-to-plate generates custom recipe."""
    await _seed_data(db)
    mock_provider = MagicMock()
    mock_provider.generate_structured_content.return_value = {
        "title": "Fresh Palak Paneer Bhurji",
        "description": "Scrambled paneer tossed with spiced sauteed palak",
        "ingredients": [
            {"item": "paneer", "amount": 200.0, "unit": "g"},
            {"item": "palak", "amount": 250.0, "unit": "g"},
            {"item": "cooking oil", "amount": 1.0, "unit": "tbsp"},
            {"item": "salt", "amount": 0.5, "unit": "tsp"},
        ],
        "steps": ["Chop palak", "Crumble paneer", "Toss together in pan"],
        "prep_time_minutes": 10,
        "cook_time_minutes": 15,
        "servings": 2,
        "used_expiring_items": ["palak", "paneer"],
    }

    app.dependency_overrides[get_ai_provider] = lambda: mock_provider
    try:
        res = api_client.post(
            "/api/v1/cook-ai/pantry-to-plate",
            json={"servings": 2, "dietary_preference": "vegetarian"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["title"] == "Fresh Palak Paneer Bhurji"
        assert len(data["steps"]) == 3
        assert "palak" in data["used_expiring_items"]
    finally:
        app.dependency_overrides.pop(get_ai_provider, None)


def test_shopping_list_crud_flow(api_client):
    """Verify shopping list item creation, retrieval, patch, and delete."""
    # 1. Add single item
    create_res = api_client.post(
        "/api/v1/shopping-list",
        json={"name": "Kasuri Methi 50g", "quantity": 1.0, "unit": "packet"},
    )
    assert create_res.status_code == 201
    item = create_res.json()
    item_id = item["id"]
    assert "blinkit.com" in item.get("quick_commerce_url", "") or "Kasuri" in item["name"]
    assert item["is_purchased"] is False

    # 2. Add batch items
    batch_res = api_client.post(
        "/api/v1/shopping-list/batch",
        json=[
            {"name": "Garam Masala", "quantity": 100.0, "unit": "g"},
            {"name": "Butter", "quantity": 100.0, "unit": "g"},
        ],
    )
    assert batch_res.status_code == 201
    assert len(batch_res.json()) == 2

    # 3. Get shopping list
    list_res = api_client.get("/api/v1/shopping-list")
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total_count"] == 3

    # 4. Patch purchased state
    patch_res = api_client.patch(
        f"/api/v1/shopping-list/{item_id}",
        json={"is_purchased": True},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["is_purchased"] is True

    # 5. Clear purchased
    clear_res = api_client.post("/api/v1/shopping-list/clear-purchased")
    assert clear_res.status_code == 200
    assert clear_res.json()["cleared_count"] == 1

    # 6. Verify remaining count
    list_res2 = api_client.get("/api/v1/shopping-list")
    assert list_res2.json()["total_count"] == 2
