"""Unit tests for receipt and quick-commerce bill extraction service."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from backend.config import Settings
from backend.models.inventory import Unit
from backend.services.ingest_errors import ExtractionError, ProviderNotConfiguredError
from backend.services.receipt_ingest import ReceiptIngestService


@pytest.fixture
def fake_settings() -> Settings:
    """Provide settings with a dummy Gemini key for mock tests.

    Returns:
        Settings configured for testing.
    """
    return Settings(gemini_api_key="mock-gemini-key", gemini_model="gemini-2.5-flash")


@pytest.mark.asyncio
async def test_extract_missing_api_key_raises() -> None:
    """Verify that unconfigured providers fail with clear error messages."""
    settings = Settings(gemini_api_key=None, anthropic_api_key=None)
    service = ReceiptIngestService(settings)
    with pytest.raises(ProviderNotConfiguredError):
        await service.extract_from_text("Blinkit Order #1234: Milk 500ml")


@pytest.mark.asyncio
async def test_extract_from_text_parses_items_and_estimates_shelf_life(
    fake_settings: Settings,
) -> None:
    """Verify text bill extraction parses items and applies shelf life heuristics."""
    service = ReceiptIngestService(fake_settings)

    mock_llm_json = {
        "store_name": "Blinkit",
        "items": [
            {
                "raw_text": "Amul Taaza Milk 500ml x 2",
                "name": "Amul Taaza Milk",
                "quantity": 1000.0,
                "unit": "ml",
                "category": "dairy",
                "price": 54.0,
            },
            {
                "raw_text": "Fresh Coriander 100g",
                "name": "Fresh Coriander",
                "quantity": 100.0,
                "unit": "g",
                "category": "herb",
                "price": 15.0,
            },
        ],
        "confidence": 0.95,
    }

    mock_resp = AsyncMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": str(mock_llm_json).replace("'", '"')}]}}]
    }

    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=mock_resp)):
        receipt = await service.extract_from_text("Blinkit Order: Milk and Coriander")

        assert receipt.store_name == "Blinkit"
        assert len(receipt.items) == 2
        assert receipt.status == "pending"
        assert receipt.confirmed is False

        milk_item = receipt.items[0]
        assert milk_item.name == "Amul Taaza Milk"
        assert milk_item.quantity == 1000.0
        assert milk_item.unit == Unit.MILLILITER
        assert milk_item.category == "dairy"
        assert milk_item.estimated_shelf_life_days == 3
        assert milk_item.suggested_location == "fridge"

        coriander_item = receipt.items[1]
        assert coriander_item.name == "Fresh Coriander"
        assert coriander_item.unit == Unit.GRAM
        assert coriander_item.estimated_shelf_life_days == 3
        assert coriander_item.suggested_location == "fridge"


@pytest.mark.asyncio
async def test_fee_and_delivery_exclusion_filters_out_platform_charges(
    fake_settings: Settings,
) -> None:
    """Ensure platform fees, rain surge, handling charges, and GST are filtered out."""
    service = ReceiptIngestService(fake_settings)

    mock_llm_json = {
        "store_name": "Zepto",
        "items": [
            {
                "raw_text": "Onion 1kg",
                "name": "Onion",
                "quantity": 1.0,
                "unit": "kg",
                "category": "vegetable",
                "price": 40.0,
            },
            {
                "raw_text": "Delivery Fee",
                "name": "Delivery Fee",
                "quantity": 1.0,
                "unit": "piece",
                "category": "other",
                "price": 25.0,
            },
            {
                "raw_text": "Handling Charge",
                "name": "Handling Charge",
                "quantity": 1.0,
                "unit": "piece",
                "category": "other",
                "price": 5.0,
            },
            {
                "raw_text": "Carry Bag",
                "name": "Carry Bag",
                "quantity": 1.0,
                "unit": "piece",
                "category": "other",
                "price": 6.0,
            },
        ],
        "confidence": 0.90,
    }

    mock_resp = AsyncMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": str(mock_llm_json).replace("'", '"')}]}}]
    }

    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=mock_resp)):
        receipt = await service.extract_from_text("Zepto order with charges")
        assert len(receipt.items) == 1
        assert receipt.items[0].name == "Onion"
        assert receipt.items[0].estimated_shelf_life_days == 21
        assert receipt.items[0].suggested_location == "pantry"


@pytest.mark.asyncio
async def test_unit_normalization_maps_to_standard_units(fake_settings: Settings) -> None:
    """Ensure informal unit names (gms, ltr, pkt, bunches) normalize to Unit enum values."""
    service = ReceiptIngestService(fake_settings)

    mock_llm_json = {
        "store_name": "Instamart",
        "items": [
            {
                "raw_text": "Cumin Seeds 100gms",
                "name": "Jeera",
                "quantity": 100.0,
                "unit": "gms",
                "category": "spice",
                "price": 30.0,
            },
            {
                "raw_text": "Sunflower Oil 1ltr",
                "name": "Sunflower Oil",
                "quantity": 1.0,
                "unit": "ltr",
                "category": "oil",
                "price": 140.0,
            },
            {
                "raw_text": "Methi 2 bunches",
                "name": "Methi Leaves",
                "quantity": 2.0,
                "unit": "bunches",
                "category": "herb",
                "price": 20.0,
            },
        ],
        "confidence": 0.92,
    }

    mock_resp = AsyncMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": str(mock_llm_json).replace("'", '"')}]}}]
    }

    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=mock_resp)):
        receipt = await service.extract_from_text("Instamart order")
        assert receipt.items[0].unit == Unit.GRAM
        assert receipt.items[0].suggested_location == "spice_box"
        assert receipt.items[1].unit == Unit.LITER
        assert receipt.items[1].suggested_location == "pantry"
        assert receipt.items[2].unit == Unit.BUNCH
        assert receipt.items[2].suggested_location == "fridge"


@pytest.mark.asyncio
async def test_extract_from_image_success(fake_settings: Settings) -> None:
    """Verify image binary extraction correctly passes base64 content to Gemini."""
    service = ReceiptIngestService(fake_settings)

    mock_llm_json = {
        "store_name": "Blinkit",
        "items": [
            {
                "raw_text": "Paneer 200g",
                "name": "Fresh Paneer",
                "quantity": 200.0,
                "unit": "g",
                "category": "dairy",
                "price": 85.0,
            }
        ],
        "confidence": 0.94,
    }

    mock_resp = AsyncMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": str(mock_llm_json).replace("'", '"')}]}}]
    }

    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=mock_resp)) as mock_post:
        fake_jpeg = b"\xff\xd8\xff\xe0fakejpegdata"
        receipt = await service.extract_from_image(fake_jpeg, mime_type="image/jpeg")

        assert mock_post.called
        assert len(receipt.items) == 1
        assert receipt.items[0].name == "Fresh Paneer"
        assert receipt.items[0].estimated_shelf_life_days == 4


@pytest.mark.asyncio
async def test_malformed_llm_output_raises_extraction_error(fake_settings: Settings) -> None:
    """Verify that malformed JSON or empty candidates raise ExtractionError."""
    service = ReceiptIngestService(fake_settings)

    mock_resp = AsyncMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"candidates": [{"content": {"parts": [{"text": "not json"}]}}]}

    with (
        patch("httpx.AsyncClient.post", new=AsyncMock(return_value=mock_resp)),
        pytest.raises(ExtractionError),
    ):
        await service.extract_from_text("Invalid content")
