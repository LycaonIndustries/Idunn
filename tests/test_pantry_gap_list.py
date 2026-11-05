"""Unit and integration tests for pantry gap shopping list calculation."""

from __future__ import annotations

import pytest

from backend.db import COLLECTION_MEAL_PLANS
from backend.models.shopping import AisleCategory
from backend.services.gap_list import categorize_aisle


@pytest.fixture
def client(api_client):
    """Provide isolated API test client fixture."""
    return api_client


def test_categorize_aisle_mappings() -> None:
    """Verify keyword classification maps ingredients into correct grocery aisles."""
    assert categorize_aisle("Red Onion") == AisleCategory.PRODUCE
    assert categorize_aisle("Amul Cow Milk") == AisleCategory.DAIRY
    assert categorize_aisle("Garam Masala") == AisleCategory.SPICES
    assert categorize_aisle("Basmati Rice") == AisleCategory.GRAINS
    assert categorize_aisle("Fortune Mustard Oil") == AisleCategory.STAPLES
    assert categorize_aisle("Matchbox") == AisleCategory.OTHER


@pytest.mark.asyncio
async def test_gap_list_generation_and_pantry_subtraction(client, db) -> None:
    """Verify gap list aggregates recipe ingredients and subtracts pantry stock."""
    # Create test recipe in database via API.
    rec = client.post(
        "/api/v1/recipes",
        json={
            "title": "Aloo Paneer Bhurji",
            "servings": 2,
            "ingredients": [
                {"name": "Paneer", "quantity": 250.0, "unit": "g"},
                {"name": "Potato", "quantity": 2.0, "unit": "piece"},
                {"name": "Onion", "quantity": 1.0, "unit": "piece"},
            ],
            "instructions": [{"step_number": 1, "instruction": "Cook."}],
        },
    ).json()

    # Seed partial pantry inventory: 100g Paneer and 2 Potatoes.
    client.post(
        "/api/v1/items",
        json={"name": "Paneer", "quantity": 100.0, "unit": "g", "location": "fridge"},
    )
    client.post(
        "/api/v1/items",
        json={"name": "Potato", "quantity": 2.0, "unit": "piece", "location": "pantry"},
    )

    plan_id = "test-gap-plan-001"
    await db[COLLECTION_MEAL_PLANS].insert_one(
        {
            "_id": plan_id,
            "week_start_date": "2026-11-09",
            "days": [
                {
                    "date": "2026-11-09",
                    "day_of_week": "monday",
                    "slots": [{"slot_id": "s1", "recipe_id": rec["_id"], "servings": 2.0}],
                }
            ],
        }
    )

    resp = client.post(f"/api/v1/shopping-list/plan/{plan_id}/gap-analysis?auto_add=true")
    assert resp.status_code == 200
    data = resp.json()
    gap_items = {item["name"]: item for item in data["gap_items"]}

    assert "Potato" not in gap_items  # Fully stocked
    assert gap_items["Paneer"]["gap_quantity"] == 150.0
    assert gap_items["Paneer"]["aisle"] == "Dairy"
    assert "blinkit" in gap_items["Paneer"]["quick_links"]
    assert gap_items["Onion"]["gap_quantity"] == 1.0

    # Missing plan returns 404.
    assert client.post("/api/v1/shopping-list/plan/missing/gap-analysis").status_code == 404


@pytest.mark.asyncio
async def test_gap_list_serving_scale_and_unit_conversion(client, db) -> None:
    """Verify ingredients scale with meal slot servings and convert units correctly."""
    rec = client.post(
        "/api/v1/recipes",
        json={
            "title": "Jeera Rice",
            "servings": 2,
            "ingredients": [{"name": "Basmati Rice", "quantity": 1.0, "unit": "kg"}],
            "instructions": [{"step_number": 1, "instruction": "Boil rice."}],
        },
    ).json()

    client.post(
        "/api/v1/items",
        json={"name": "Basmati Rice", "quantity": 500.0, "unit": "g", "location": "pantry"},
    )

    plan_id = "scale-plan-002"
    await db[COLLECTION_MEAL_PLANS].insert_one(
        {
            "_id": plan_id,
            "week_start_date": "2026-11-16",
            "days": [
                {
                    "date": "2026-11-16",
                    "day_of_week": "monday",
                    "slots": [{"slot_id": "s1", "recipe_id": rec["_id"], "servings": 4.0}],
                }
            ],
        }
    )

    resp = client.post(f"/api/v1/shopping-list/plan/{plan_id}/gap-analysis")
    assert resp.status_code == 200
    gap_items = {item["name"]: item for item in resp.json()["gap_items"]}

    rice = gap_items["Basmati Rice"]
    assert rice["required_quantity"] == 2.0
    assert rice["in_stock_quantity"] == 0.5
    assert rice["gap_quantity"] == 1.5
    assert rice["aisle"] == "Grains"
