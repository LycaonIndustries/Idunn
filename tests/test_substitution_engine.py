"""Unit tests for the algorithmic culinary substitution engine and API."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from backend.models.inventory import Item, Location, Unit
from backend.services.substitution_engine import SubstitutionEngine


def make_dummy_item(name: str, item_id: str) -> Item:
    """Helper to instantiate Item with required fields for tests.

    Args:
        name: Item display name.
        item_id: Mock document id.

    Returns:
        Instantiated Item model.
    """
    now = datetime.now(UTC)
    return Item(
        _id=item_id,
        name=name,
        quantity=1.0,
        unit=Unit.PIECE,
        location=Location.PANTRY,
        added_at=now,
        updated_at=now,
    )


def test_get_culinary_substitutions_direct_match() -> None:
    """Verify exact match returns known functional culinary substitutes."""
    subs = SubstitutionEngine.get_culinary_substitutions("lemon juice")
    sub_names = [s.substitute_name for s in subs]
    assert "lime juice" in sub_names
    assert "white vinegar" in sub_names
    assert all(s.category == "acid" for s in subs)


def test_get_culinary_substitutions_substring_match() -> None:
    """Verify compound ingredient name matches parent category in ontology."""
    subs = SubstitutionEngine.get_culinary_substitutions("unsalted butter")
    sub_names = [s.substitute_name for s in subs]
    assert "ghee" in sub_names
    assert "olive oil" in sub_names


def test_find_pantry_substitutions_prioritizes_stock() -> None:
    """Verify pantry stock flags matching substitute and sorts it to top."""
    pantry = [make_dummy_item("lime juice", "item_1")]
    subs = SubstitutionEngine.find_pantry_substitutions("lemon juice", pantry)
    assert len(subs) > 0
    assert subs[0].substitute_name == "lime juice"
    assert subs[0].in_pantry is True


def test_unknown_ingredient_returns_empty_list() -> None:
    """Verify uncatalogued non-food item returns empty list deterministically."""
    subs = SubstitutionEngine.get_culinary_substitutions("synthetic plastic polymer")
    assert subs == []


@pytest.mark.asyncio
async def test_substitutions_api_endpoint(api_client, db) -> None:
    """Verify POST /api/v1/cook-ai/substitutions returns substitutes with pantry state."""
    item = {
        "_id": "item_yogurt_1",
        "name": "greek yogurt",
        "quantity": 1.0,
        "unit": "piece",
        "location": "fridge",
        "consumed": False,
        "added_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    await db.inventory.insert_one(item)

    response = api_client.post(
        "/api/v1/cook-ai/substitutions",
        json={"ingredient": "sour cream"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    # Greek yogurt is in pantry mock, so it must be marked in_pantry=True and sorted first
    assert data[0]["substitute_name"] == "greek yogurt"
    assert data[0]["in_pantry"] is True
