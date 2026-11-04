"""Tests for generative Pantry-to-Plate chef service.

Validates prompt generation, strict staple constraints, and structured response
parsing for AI meal proposals.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from backend.models.cook_ai import PantryToPlateRequest, PantryToPlateResponse
from backend.models.inventory import Item, Location, Unit
from backend.services.pantry_to_plate import generate_pantry_meal


def _make_item(name: str, days_to_expiry: int | None = None) -> Item:
    """Helper to create active pantry item."""
    expiry = None
    if days_to_expiry is not None:
        expiry = datetime.now(UTC) + timedelta(days=days_to_expiry)
    return Item(
        _id=f"item_{name}",
        name=name,
        quantity=500.0,
        unit=Unit.GRAM,
        location=Location.FRIDGE,
        added_at=datetime.now(UTC),
        expiry_date=expiry,
        consumed=False,
    )


def test_generate_pantry_meal_empty_pantry_raises_error():
    """Verify ValueError is raised if pantry has no active stock."""
    pantry = []
    req = PantryToPlateRequest()
    mock_provider = MagicMock()

    with pytest.raises(ValueError, match="Pantry has no active items"):
        generate_pantry_meal(pantry, req, mock_provider)


def test_generate_pantry_meal_success():
    """Verify prompt invocation and parsing into PantryToPlateResponse."""
    pantry = [
        _make_item("potato", days_to_expiry=1),  # expiring soon
        _make_item("cumin"),
        _make_item("mustard seeds"),
    ]
    req = PantryToPlateRequest(dietary_preference="vegetarian", max_prep_time_minutes=25)

    mock_provider = MagicMock()
    mock_provider.generate_structured_content.return_value = {
        "title": "Jeera Aloo",
        "description": "Pan-tossed spiced potatoes with cumin and mustard seeds",
        "ingredients": [
            {"item": "potato", "amount": 2.0, "unit": "piece"},
            {"item": "cumin", "amount": 1.0, "unit": "tsp"},
            {"item": "cooking oil", "amount": 1.0, "unit": "tbsp"},
            {"item": "salt", "amount": 0.5, "unit": "tsp"},
        ],
        "steps": [
            "Boil and dice potatoes",
            "Heat oil, add cumin and mustard seeds until they crackle",
            "Toss potatoes with salt until golden",
        ],
        "prep_time_minutes": 10,
        "cook_time_minutes": 15,
        "servings": 2,
        "used_expiring_items": ["potato"],
    }

    res = generate_pantry_meal(pantry, req, mock_provider)

    assert isinstance(res, PantryToPlateResponse)
    assert res.title == "Jeera Aloo"
    assert "potato" in res.used_expiring_items
    assert len(res.steps) == 3

    # Ensure provider was invoked with prompt mentioning active items
    prompt_arg = mock_provider.generate_structured_content.call_args[0][0]
    assert "potato" in prompt_arg
    assert "cumin" in prompt_arg
    assert "expiring soon" in prompt_arg.lower()
