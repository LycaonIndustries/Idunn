"""Tests for inventory API endpoints - Phase 1."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import AsyncGenerator

import pytest
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi.testclient import TestClient

from idunn.main import app
from idunn.models.inventory import Unit, Location


@pytest.fixture(scope="module")
def client():
    """Create test client."""
    from idunn.db import MongoClient

    # Use test database
    MongoClient._db = None  # Reset
    with TestClient(app) as c:
        yield c
    # Cleanup
    import asyncio
    asyncio.get_event_loop().run_until_complete(MongoClient.close())


@pytest.fixture
def sample_item():
    """Sample item data."""
    return {
        "name": "Potatoes",
        "quantity": 2.5,
        "unit": Unit.KILOGRAM.value,
        "location": Location.PANTRY.value,
    }


@pytest.fixture
def expiring_item():
    """Item expiring in 2 days."""
    return {
        "name": "Milk",
        "quantity": 1.0,
        "unit": Unit.LITER.value,
        "location": Location.FRIDGE.value,
        "expiry_date": (datetime.utcnow() + timedelta(days=2)).isoformat(),
    }


class TestCreateItem:
    def test_create_item_success(self, client, sample_item):
        """Test successful item creation."""
        response = client.post("/api/v1/items", json=sample_item)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Potatoes"
        assert data["quantity"] == 2.5
        assert data["unit"] == "kg"
        assert data["consumed"] is False

    def test_create_item_missing_field(self, client):
        """Test creation with missing required field."""
        response = client.post(
            "/api/v1/items",
            json={"name": "Test"},  # Missing quantity, unit, location
        )
        assert response.status_code == 422  # Validation error


class TestListItems:
    def test_list_items_empty(self, client):
        """Test listing when no items exist."""
        response = client.get("/api/v1/items")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_items_with_location_filter(self, client, sample_item):
        """Test filtering by location."""
        # Create item in pantry
        client.post("/api/v1/items", json=sample_item)

        # Filter by pantry
        response = client.get(f"/api/v1/items?location={Location.PANTRY.value}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert all(item["location"] == Location.PANTRY.value for item in data)


class TestExpiringItems:
    def test_get_expiring_items(self, client, expiring_item):
        """Test getting items expiring soon."""
        # Create expiring item
        client.post("/api/v1/items", json=expiring_item)

        # Get items expiring within 3 days
        response = client.get("/api/v1/items/expiring?days=3")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any(item["name"] == "Milk" for item in data)


class TestUpdateItem:
    def test_update_item_quantity(self, client, sample_item):
        """Test updating item quantity."""
        # Create item
        create_resp = client.post("/api/v1/items", json=sample_item)
        item_id = create_resp.json()["_id"]

        # Update quantity
        response = client.patch(
            f"/api/v1/items/{item_id}", json={"quantity": 3.0}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["quantity"] == 3.0


class TestConsumeItem:
    def test_consume_partial(self, client, sample_item):
        """Test partial consumption."""
        # Create item
        create_resp = client.post("/api/v1/items", json=sample_item)
        item_id = create_resp.json()["_id"]

        # Consume 1 kg
        response = client.post(
            f"/api/v1/items/{item_id}/consume", params={"quantity": 1.0}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["quantity"] == 1.5  # 2.5 - 1.0
        assert data["consumed"] is False

    def test_consume_all(self, client, sample_item):
        """Test consuming entire item."""
        # Create item
        create_resp = client.post("/api/v1/items", json=sample_item)
        item_id = create_resp.json()["_id"]

        # Consume all 2.5 kg
        response = client.post(
            f"/api/v1/items/{item_id}/consume", params={"quantity": 2.5}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["quantity"] == 0
        assert data["consumed"] is True
