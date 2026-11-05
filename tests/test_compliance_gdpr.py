"""Tests for GDPR and DPDP user account deletion cascade and data portability export."""

from __future__ import annotations

import pytest
from mongomock_motor import AsyncMongoMockClient
from starlette.testclient import TestClient

from backend.api.deps import AuthenticatedUser, get_current_user
from backend.db import (
    COLLECTION_ITEMS,
    COLLECTION_RECEIPTS,
    COLLECTION_RECIPES,
    get_db,
)
from backend.main import app


@pytest.fixture
def user_erasure_target() -> AuthenticatedUser:
    """Fixture providing user requesting data export and erasure."""
    return AuthenticatedUser(id="user_erase_me", email="erasure@example.com")


@pytest.fixture
def user_innocent_bystander() -> AuthenticatedUser:
    """Fixture providing distinct tenant user whose data must remain intact."""
    return AuthenticatedUser(id="user_keep_me", email="keep@example.com")


@pytest.mark.asyncio
async def test_user_data_export(
    api_client: TestClient,
    user_erasure_target: AuthenticatedUser,
    user_innocent_bystander: AuthenticatedUser,
) -> None:
    """Verify machine-readable data portability export aggregates only caller documents."""
    mock_db = AsyncMongoMockClient()["test_user_export"]
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: user_erasure_target

    # Seed caller's pantry item and recipe.
    await mock_db[COLLECTION_ITEMS].insert_one(
        {
            "name": "Organic Paneer",
            "owner_id": user_erasure_target.id,
        }
    )
    await mock_db[COLLECTION_RECIPES].insert_one(
        {
            "title": "Paneer Tikka",
            "owner_id": user_erasure_target.id,
        }
    )

    # Seed bystander's item (must not appear in caller export).
    await mock_db[COLLECTION_ITEMS].insert_one(
        {
            "name": "Bystander Milk",
            "owner_id": user_innocent_bystander.id,
        }
    )

    res = api_client.get("/api/v1/users/me/export")
    assert res.status_code == 200
    export_data = res.json()

    assert export_data["user_id"] == user_erasure_target.id
    assert len(export_data["inventory_items"]) == 1
    assert export_data["inventory_items"][0]["name"] == "Organic Paneer"
    assert len(export_data["recipes"]) == 1
    assert export_data["recipes"][0]["title"] == "Paneer Tikka"


@pytest.mark.asyncio
async def test_user_account_deletion_cascade(
    api_client: TestClient,
    user_erasure_target: AuthenticatedUser,
    user_innocent_bystander: AuthenticatedUser,
) -> None:
    """Verify DELETE /api/v1/users/me purges all caller data and leaves other tenants safe."""
    mock_db = AsyncMongoMockClient()["test_user_cascade"]
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: user_erasure_target

    # Seed documents across multiple collections for target user.
    await mock_db[COLLECTION_ITEMS].insert_one(
        {
            "name": "Target Item",
            "owner_id": user_erasure_target.id,
        }
    )
    await mock_db[COLLECTION_RECIPES].insert_one(
        {
            "title": "Target Recipe",
            "owner_id": user_erasure_target.id,
        }
    )
    await mock_db[COLLECTION_RECEIPTS].insert_one(
        {
            "store": "Blinkit",
            "owner_id": user_erasure_target.id,
        }
    )

    # Seed documents for bystander.
    await mock_db[COLLECTION_ITEMS].insert_one(
        {
            "name": "Bystander Item",
            "owner_id": user_innocent_bystander.id,
        }
    )

    res = api_client.delete("/api/v1/users/me")
    assert res.status_code == 200
    report = res.json()

    assert report["status"] == "erased"
    assert report["user_id"] == user_erasure_target.id
    assert report["deleted_counts"]["inventory_items"] == 1
    assert report["deleted_counts"]["recipes"] == 1
    assert report["deleted_counts"]["receipts"] == 1

    # Verify bystander document was NOT deleted.
    bystander_item = await mock_db[COLLECTION_ITEMS].find_one(
        {"owner_id": user_innocent_bystander.id}
    )
    assert bystander_item is not None
    assert bystander_item["name"] == "Bystander Item"

    # Verify target documents were purged completely.
    target_item = await mock_db[COLLECTION_ITEMS].find_one({"owner_id": user_erasure_target.id})
    assert target_item is None
