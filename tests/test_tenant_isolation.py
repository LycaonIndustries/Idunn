"""Integration tests for BOLA and IDOR tenant isolation across inventory and recipes."""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from backend.api.deps import AuthenticatedUser, get_current_user
from backend.main import app
from backend.models.inventory import Location, Unit


@pytest.fixture
def user_alice() -> AuthenticatedUser:
    """Fixture providing authenticated caller Alice."""
    return AuthenticatedUser(id="user_alice", email="alice@kitchen.org")


@pytest.fixture
def user_bob() -> AuthenticatedUser:
    """Fixture providing authenticated caller Bob."""
    return AuthenticatedUser(id="user_bob", email="bob@kitchen.org")


@pytest.mark.asyncio
async def test_inventory_tenant_isolation(
    api_client: TestClient,
    user_alice: AuthenticatedUser,
    user_bob: AuthenticatedUser,
) -> None:
    """Verify inventory items cannot be read or mutated across distinct tenants.

    Args:
        api_client: HTTP test client.
        user_alice: Identity for first user.
        user_bob: Identity for second user.
    """
    # Authenticate as User Alice to create private inventory item.
    app.dependency_overrides[get_current_user] = lambda: user_alice
    item_payload = {
        "name": "Kashmiri Chilli Powder",
        "quantity": 100.0,
        "unit": Unit.GRAM.value,
        "location": Location.SPICE_BOX.value,
    }
    create_res = api_client.post("/api/v1/items", json=item_payload)
    assert create_res.status_code == 201
    item_id = create_res.json()["_id"]

    # Verify Alice can read her own created item.
    alice_get = api_client.get(f"/api/v1/items/{item_id}")
    assert alice_get.status_code == 200
    assert alice_get.json()["name"] == "Kashmiri Chilli Powder"

    # Switch identity to User Bob to verify BOLA/IDOR protection.
    app.dependency_overrides[get_current_user] = lambda: user_bob

    # Verify Bob receives 404 when querying Alice's item ID.
    bob_get = api_client.get(f"/api/v1/items/{item_id}")
    assert bob_get.status_code == 404

    # Verify Bob cannot update Alice's item.
    bob_patch = api_client.patch(f"/api/v1/items/{item_id}", json={"quantity": 50.0})
    assert bob_patch.status_code == 404

    # Verify Bob cannot consume Alice's item.
    bob_consume = api_client.post(f"/api/v1/items/{item_id}/consume?quantity=20")
    assert bob_consume.status_code == 404

    # Verify Bob cannot delete Alice's item.
    bob_delete = api_client.delete(f"/api/v1/items/{item_id}")
    assert bob_delete.status_code == 404

    # Verify Bob's inventory list does not leak Alice's item.
    bob_list = api_client.get("/api/v1/items")
    assert bob_list.status_code == 200
    assert not any(i["_id"] == item_id for i in bob_list.json())

    # Switch back to Alice and delete item.
    app.dependency_overrides[get_current_user] = lambda: user_alice
    alice_delete = api_client.delete(f"/api/v1/items/{item_id}")
    assert alice_delete.status_code == 204


@pytest.mark.asyncio
async def test_recipe_tenant_isolation(
    api_client: TestClient,
    user_alice: AuthenticatedUser,
    user_bob: AuthenticatedUser,
) -> None:
    """Verify recipe documents cannot be accessed or modified across tenants.

    Args:
        api_client: HTTP test client.
        user_alice: Identity for first user.
        user_bob: Identity for second user.
    """
    # Create private recipe under Alice's identity.
    app.dependency_overrides[get_current_user] = lambda: user_alice
    recipe_payload = {
        "title": "Alice Secret Biryani",
        "ingredients": [{"name": "Basmati Rice", "quantity": 500.0, "unit": "g"}],
        "steps": [{"step_number": 1, "instruction": "Cook rice with spices."}],
    }
    create_res = api_client.post("/api/v1/recipes", json=recipe_payload)
    assert create_res.status_code == 201
    recipe_id = create_res.json()["_id"]

    # Verify Alice can access her recipe.
    alice_get = api_client.get(f"/api/v1/recipes/{recipe_id}")
    assert alice_get.status_code == 200
    assert alice_get.json()["title"] == "Alice Secret Biryani"

    # Switch identity to Bob to test cross-tenant boundaries.
    app.dependency_overrides[get_current_user] = lambda: user_bob

    # Verify Bob cannot retrieve Alice's recipe.
    bob_get = api_client.get(f"/api/v1/recipes/{recipe_id}")
    assert bob_get.status_code == 404

    # Verify Bob cannot update Alice's recipe.
    bob_patch = api_client.patch(f"/api/v1/recipes/{recipe_id}", json={"title": "Hacked Title"})
    assert bob_patch.status_code == 404

    # Verify Bob cannot delete Alice's recipe.
    bob_delete = api_client.delete(f"/api/v1/recipes/{recipe_id}")
    assert bob_delete.status_code == 404

    # Verify Bob's recipe list does not include Alice's private recipe.
    bob_list = api_client.get("/api/v1/recipes")
    assert bob_list.status_code == 200
    assert not any(r["_id"] == recipe_id for r in bob_list.json())

    # Clean up recipe using Alice's authenticated session.
    app.dependency_overrides[get_current_user] = lambda: user_alice
    alice_delete = api_client.delete(f"/api/v1/recipes/{recipe_id}")
    assert alice_delete.status_code == 204
