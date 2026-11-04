"""API integration tests for receipt ingestion and recipe cooking deduction."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from bson import ObjectId

from backend.db import COLLECTION_ITEMS, COLLECTION_RECEIPTS, COLLECTION_RECIPES
from backend.models.inventory import Location, Unit
from backend.models.receipt import Receipt, ReceiptItemCandidate


@pytest.fixture
def client(api_client):
    """Reuse isolated test client fixture."""
    return api_client


def test_ingest_image_receipt_endpoint(client, db) -> None:
    """Verify POST /api/v1/receipts/ingest/image accepts image and stores pending receipt."""
    candidate = ReceiptItemCandidate(
        raw_text="Fresh Paneer 200g",
        name="Fresh Paneer",
        quantity=200.0,
        unit=Unit.GRAM,
        category="dairy",
        estimated_shelf_life_days=4,
        suggested_location="fridge",
        price=90.0,
    )
    fake_receipt = Receipt(
        _id="rcpt_test_123",
        store_name="Blinkit",
        purchase_date=datetime.now(UTC),
        items=[candidate],
        confidence=0.96,
        status="pending",
        confirmed=False,
    )

    with patch(
        "backend.services.receipt_ingest.ReceiptIngestService.extract_from_image",
        new=AsyncMock(return_value=fake_receipt),
    ):
        fake_image = b"\xff\xd8\xff\xe0dummyjpegcontent"
        response = client.post(
            "/api/v1/receipts/ingest/image",
            files={"file": ("receipt.jpg", fake_image, "image/jpeg")},
            data={"store_hint": "Blinkit"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["_id"] == "rcpt_test_123"
        assert data["store_name"] == "Blinkit"
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "Fresh Paneer"
        assert data["confirmed"] is False


@pytest.mark.asyncio
async def test_confirm_receipt_adds_items_to_pantry(client, db) -> None:
    """Verify POST /api/v1/receipts/confirm commits candidate items to pantry collection."""
    receipt_id = "rcpt_confirm_test"
    await db[COLLECTION_RECEIPTS].insert_one(
        {
            "_id": receipt_id,
            "store_name": "Zepto",
            "items": [],
            "status": "pending",
            "confirmed": False,
        }
    )

    confirm_payload = {
        "receipt_id": receipt_id,
        "store_name": "Zepto",
        "items": [
            {
                "raw_text": "Amul Milk 500ml",
                "name": "Amul Milk",
                "quantity": 500.0,
                "unit": "ml",
                "category": "dairy",
                "estimated_shelf_life_days": 3,
                "suggested_location": "fridge",
                "price": 27.0,
            },
            {
                "raw_text": "Onion 1kg",
                "name": "Onion",
                "quantity": 1.0,
                "unit": "kg",
                "category": "vegetable",
                "estimated_shelf_life_days": 21,
                "suggested_location": "pantry",
                "price": 35.0,
            },
        ],
    }

    response = client.post("/api/v1/receipts/confirm", json=confirm_payload)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["confirmed_count"] == 2

    # Check inventory items created in DB
    milk = await db[COLLECTION_ITEMS].find_one({"name": "Amul Milk"})
    assert milk is not None
    assert milk["quantity"] == 500.0
    assert milk["unit"] == "ml"
    assert milk["location"] == "fridge"
    assert milk["consumed"] is False
    assert milk["expiry_date"] is not None

    onion = await db[COLLECTION_ITEMS].find_one({"name": "Onion"})
    assert onion is not None
    assert onion["quantity"] == 1.0
    assert onion["unit"] == "kg"
    assert onion["location"] == "pantry"

    # Verify receipt record is marked confirmed
    rcpt = await db[COLLECTION_RECEIPTS].find_one({"_id": receipt_id})
    assert rcpt["confirmed"] is True
    assert rcpt["status"] == "confirmed"


@pytest.mark.asyncio
async def test_cook_recipe_endpoint_deducts_pantry(client, db) -> None:
    """Verify POST /api/v1/recipes/{id}/cook decrements pantry items and returns report."""
    now = datetime.now(UTC)
    # Insert pantry item
    paneer_doc = await db[COLLECTION_ITEMS].insert_one(
        {
            "name": "Paneer",
            "quantity": 400.0,
            "unit": Unit.GRAM.value,
            "location": Location.FRIDGE.value,
            "expiry_date": now + timedelta(days=4),
            "consumed": False,
            "added_at": now,
            "updated_at": now,
        }
    )

    # Insert recipe
    recipe_oid = ObjectId()
    await db[COLLECTION_RECIPES].insert_one(
        {
            "_id": recipe_oid,
            "title": "Paneer Tikka",
            "ingredients": [{"name": "Paneer", "quantity": 250.0, "unit": "g"}],
            "steps": [{"step_number": 1, "instruction": "Marinate and grill paneer."}],
            "created_at": now,
            "updated_at": now,
        }
    )

    response = client.post(f"/api/v1/recipes/{recipe_oid}/cook?servings_multiplier=1.0")
    assert response.status_code == 200
    data = response.json()
    assert data["fully_satisfied"] is True
    assert len(data["deductions"]) == 1
    assert data["deductions"][0]["item_id"] == str(paneer_doc.inserted_id)
    assert data["deductions"][0]["deducted_quantity"] == 250.0
    assert data["deductions"][0]["remaining_quantity"] == 150.0

    # Verify database was updated
    updated_paneer = await db[COLLECTION_ITEMS].find_one({"_id": paneer_doc.inserted_id})
    assert updated_paneer["quantity"] == 150.0
    assert updated_paneer["consumed"] is False
