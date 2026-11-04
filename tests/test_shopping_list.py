"""Unit tests for the shopping list API endpoints and quick-commerce links."""

from __future__ import annotations

import pytest

from backend.models.shopping import generate_quick_commerce_links


def test_generate_quick_commerce_links() -> None:
    """Verify generated links contain query-encoded search terms."""
    links = generate_quick_commerce_links("greek yogurt")
    assert "blinkit" in links
    assert "zepto" in links
    assert "instamart" in links
    assert "greek%20yogurt" in links["blinkit"]
    assert "greek%20yogurt" in links["zepto"]
    assert "greek%20yogurt" in links["instamart"]


@pytest.mark.asyncio
async def test_shopping_list_crud_flow(api_client, db) -> None:
    """Verify add, list, update, and delete flow for shopping items."""
    # 1. Initially empty
    res = api_client.get("/api/v1/shopping-list")
    assert res.status_code == 200
    assert res.json() == []

    # 2. Add single item
    add_res = api_client.post(
        "/api/v1/shopping-list/items",
        json={"name": "lemon", "quantity": 3.0, "unit": "piece"},
    )
    assert add_res.status_code == 201
    created = add_res.json()
    item_id = created["_id"]
    assert created["name"] == "lemon"
    assert created["quantity"] == 3.0
    assert created["checked"] is False
    assert "blinkit" in created["quick_links"]

    # 3. Batch add items
    batch_res = api_client.post(
        "/api/v1/shopping-list/batch",
        json={
            "items": [
                {"name": "olive oil", "quantity": 1.0, "unit": "bottle"},
                {"name": "black pepper", "quantity": 50.0, "unit": "g"},
            ]
        },
    )
    assert batch_res.status_code == 201
    assert len(batch_res.json()) == 2

    # 4. List items (3 total)
    list_res = api_client.get("/api/v1/shopping-list")
    assert list_res.status_code == 200
    items = list_res.json()
    assert len(items) == 3

    # 5. Check item off
    patch_res = api_client.patch(
        f"/api/v1/shopping-list/items/{item_id}",
        json={"checked": True},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["checked"] is True

    # 6. Clear purchased items
    clear_res = api_client.post("/api/v1/shopping-list/clear-purchased")
    assert clear_res.status_code == 200
    assert clear_res.json()["deleted_count"] == 1

    # 7. Verify remaining active count
    remain_res = api_client.get("/api/v1/shopping-list")
    assert remain_res.status_code == 200
    assert len(remain_res.json()) == 2


@pytest.mark.asyncio
async def test_shopping_item_not_found(api_client, db) -> None:
    """Verify 404 response on nonexistent item update or delete."""
    patch_res = api_client.patch(
        "/api/v1/shopping-list/items/nonexistent-id",
        json={"checked": True},
    )
    assert patch_res.status_code == 404

    del_res = api_client.delete("/api/v1/shopping-list/items/nonexistent-id")
    assert del_res.status_code == 404
