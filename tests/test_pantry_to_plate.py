"""Unit tests for the user-triggered generative pantry-to-plate chef service."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from backend.config import Settings
from backend.models.cook_ai import PantryToPlateRequest
from backend.models.inventory import Item, Location, Unit
from backend.services.ingest_errors import ProviderNotConfiguredError
from backend.services.pantry_to_plate import PantryToPlateService


def make_test_item(name: str, item_id: str) -> Item:
    """Helper to instantiate test inventory item.

    Args:
        name: Ingredient display name.
        item_id: Mock document ID.

    Returns:
        Instantiated Item model.
    """
    now = datetime.now(UTC)
    return Item(
        _id=item_id,
        name=name,
        quantity=2.0,
        unit=Unit.PIECE,
        location=Location.PANTRY,
        added_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_pantry_to_plate_unconfigured_error() -> None:
    """Verify ProviderNotConfiguredError is raised when no API key is provided."""
    config = Settings(gemini_api_key="", anthropic_api_key="")
    service = PantryToPlateService(config)
    req = PantryToPlateRequest(servings=2)
    items = [make_test_item("potato", "item_1")]

    with pytest.raises(ProviderNotConfiguredError):
        await service.generate_recipe(req, items)


@pytest.mark.asyncio
async def test_pantry_to_plate_mock_generation() -> None:
    """Verify recipe generation completes successfully with mocked Gemini response."""
    config = Settings(gemini_api_key="test-key-123")
    service = PantryToPlateService(config)
    req = PantryToPlateRequest(servings=4, meal_type="lunch", dietary_preference="veg")
    items = [make_test_item("paneer", "item_1"), make_test_item("bell pepper", "item_2")]

    mock_gemini_payload = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": (
                                '{"title": "Kadai Paneer", "description": "Quick stir fry", '
                                '"prep_time_minutes": 10, "cook_time_minutes": 15, "servings": 4, '
                                '"cuisine_type": "veg", '
                                '"ingredients": [{"name": "paneer", "quantity": 250, "unit": "g"}], '
                                '"steps": [{"step_number": 1, "instruction": "Toss in pan"}], '
                                '"assumed_staples": ["salt", "water", "cooking oil", "black pepper"]}'
                            )
                        }
                    ]
                }
            }
        ]
    }

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_gemini_payload

    with patch("httpx.AsyncClient.post", return_value=mock_response):
        recipe = await service.generate_recipe(req, items)
        assert recipe.title == "Kadai Paneer"
        assert recipe.servings == 4
        assert len(recipe.assumed_staples) == 4


@pytest.mark.asyncio
async def test_pantry_to_plate_api_empty_inventory(api_client, db) -> None:
    """Verify 400 error when attempting to generate recipe with empty pantry."""
    res = api_client.post(
        "/api/v1/cook-ai/pantry-to-plate",
        json={"servings": 2, "meal_type": "dinner"},
    )
    assert res.status_code == 400
    assert "No ingredients available in pantry" in res.json()["detail"]
