"""Recipe storage and review behavior through the public API."""

from datetime import datetime
from unittest.mock import AsyncMock

import pytest
from bson import ObjectId
from pymongo.errors import AutoReconnect

from backend.services.ingest_errors import (
    ExtractionError,
    ProviderError,
    ProviderNotConfiguredError,
    SourceError,
)
from backend.services.recipe_sources import SourcePage


def test_recipe_crud_and_timestamps(api_client, recipe_data):
    created = api_client.post("/api/v1/recipes", json=recipe_data)
    assert created.status_code == 201
    data = created.json()
    assert datetime.fromisoformat(data["created_at"]).tzinfo is not None
    assert data["created_at"] == data["updated_at"]
    assert data["needs_review"] is True
    recipe_id = data["_id"]
    assert api_client.get(f"/api/v1/recipes/{recipe_id}").json()["title"] == "Aloo Gobi"
    assert len(api_client.get("/api/v1/recipes?region=north_india").json()) == 1
    assert api_client.get("/api/v1/recipes?region=south_india").json() == []
    updated = api_client.patch(f"/api/v1/recipes/{recipe_id}", json={"description": None})
    assert updated.status_code == 200
    assert updated.json()["description"] is None
    assert updated.json()["revision"] == 1
    assert api_client.delete(f"/api/v1/recipes/{recipe_id}").status_code == 204
    assert api_client.get(f"/api/v1/recipes/{recipe_id}").status_code == 404


def test_empty_list_is_isolated(api_client):
    assert api_client.get("/api/v1/recipes").json() == []
    assert api_client.get("/api/v1/recipes/review").json() == []


@pytest.mark.parametrize("patch", [{"title": None}, {"ingredients": None}, {"servings": 0}])
def test_invalid_updates_do_not_corrupt_recipe(api_client, recipe_data, patch):
    recipe_id = api_client.post("/api/v1/recipes", json=recipe_data).json()["_id"]
    assert api_client.patch(f"/api/v1/recipes/{recipe_id}", json=patch).status_code == 422
    assert api_client.get(f"/api/v1/recipes/{recipe_id}").json()["title"] == "Aloo Gobi"


def test_search_treats_input_as_text(api_client, recipe_data):
    api_client.post("/api/v1/recipes", json=recipe_data)
    assert api_client.get("/api/v1/recipes", params={"query": ".*"}).json() == []


async def test_review_confirms_rows_and_prevents_stale_decisions(api_client, db, recipe_data):
    ingredient_id = (await db.ingredients.insert_one({"name": "potato"})).inserted_id
    recipe_id = api_client.post("/api/v1/recipes", json=recipe_data).json()["_id"]
    review = {
        "revision": 0,
        "decisions": [{"ingredient_index": 0, "ingredient_id": str(ingredient_id)}],
    }
    response = api_client.post(f"/api/v1/recipes/{recipe_id}/review", json=review)
    assert response.status_code == 200
    assert response.json()["normalized_ingredients"] == [str(ingredient_id)]
    assert response.json()["needs_review"] is False
    assert api_client.get("/api/v1/recipes/review").json() == []
    assert api_client.post(f"/api/v1/recipes/{recipe_id}/review", json=review).status_code == 409
    edited = api_client.patch(
        f"/api/v1/recipes/{recipe_id}", json={"ingredients": [{"name": "rice"}]}
    )
    assert edited.json()["normalized_ingredients"] == []
    assert edited.json()["needs_review"] is True
    assert edited.json()["embedding"] is None
    assert edited.json()["ingredient_matches"][0]["ingredient_id"] is None


@pytest.mark.parametrize(
    "decisions",
    [
        [{"ingredient_index": 9, "ignore": True}],
        [{"ingredient_index": 0, "ignore": True}, {"ingredient_index": 0, "ignore": True}],
        [{"ingredient_index": 0, "ingredient_id": str(ObjectId())}],
        [{"ingredient_index": 0}],
        [{"ingredient_index": 0, "ingredient_id": str(ObjectId()), "ignore": True}],
    ],
)
def test_invalid_review_leaves_queue_unchanged(api_client, recipe_data, decisions):
    recipe_id = api_client.post("/api/v1/recipes", json=recipe_data).json()["_id"]
    response = api_client.post(
        f"/api/v1/recipes/{recipe_id}/review", json={"revision": 0, "decisions": decisions}
    )
    assert response.status_code == 422
    assert api_client.get(f"/api/v1/recipes/{recipe_id}").json()["revision"] == 0


async def test_uncertain_extraction_needs_explicit_approval(api_client, db, recipe_data):
    recipe_id = api_client.post("/api/v1/recipes", json=recipe_data).json()["_id"]
    await db.recipes.update_one(
        {"_id": ObjectId(recipe_id)}, {"$set": {"extraction_reviewed": False}}
    )
    response = api_client.post(
        f"/api/v1/recipes/{recipe_id}/review",
        json={
            "revision": 0,
            "decisions": [{"ingredient_index": 0, "ignore": True}],
        },
    )
    assert response.json()["needs_review"] is True
    approved = api_client.post(
        f"/api/v1/recipes/{recipe_id}/review",
        json={
            "revision": 1,
            "approve_extraction": True,
        },
    )
    assert approved.json()["needs_review"] is False


def test_import_stores_a_readable_recipe(api_client, service, recipe_html, monkeypatch):
    monkeypatch.setattr(
        service.reader.fetcher,
        "fetch",
        AsyncMock(
            return_value=SourcePage(
                recipe_html,
                "https://recipes.example/aloo-gobi",
            )
        ),
    )
    response = api_client.post(
        "/api/v1/recipes/ingest", params={"url": "https://recipes.example/aloo-gobi"}
    )
    assert response.status_code == 201
    result = response.json()
    stored = api_client.get(f"/api/v1/recipes/{result['recipe_id']}").json()
    assert stored["source_url"] == "https://recipes.example/aloo-gobi"
    assert stored["ingredients"][1]["quantity"] == 0.5
    assert stored["created_at"]
    assert len(api_client.get("/api/v1/recipes/review").json()) == 1


@pytest.mark.parametrize(
    ("error", "code"),
    [
        (SourceError("bad source"), 400),
        (ExtractionError("no recipe"), 422),
        (ProviderNotConfiguredError("missing key"), 503),
        (ProviderError("provider failed"), 502),
        (AutoReconnect("database failed"), 503),
    ],
)
def test_import_errors_never_report_success(api_client, service, monkeypatch, error, code):
    monkeypatch.setattr(service, "ingest_from_url", AsyncMock(side_effect=error))
    response = api_client.post(
        "/api/v1/recipes/ingest", params={"url": "https://recipes.example/a"}
    )
    assert response.status_code == code
    assert "recipe_id" not in response.json()
    assert api_client.get("/api/v1/recipes").json() == []


def test_review_race_returns_conflict(api_client, db, recipe_data, monkeypatch):
    recipe_id = api_client.post("/api/v1/recipes", json=recipe_data).json()["_id"]
    monkeypatch.setattr(type(db.recipes), "find_one_and_update", AsyncMock(return_value=None))
    response = api_client.post(
        f"/api/v1/recipes/{recipe_id}/review",
        json={
            "revision": 0,
            "decisions": [{"ingredient_index": 0, "ignore": True}],
        },
    )
    assert response.status_code == 409


def test_paste_missing_key_is_clear(api_client):
    response = api_client.post("/api/v1/recipes/ingest/text", json={"text": "Cook rice."})
    assert response.status_code == 503
    assert "ANTHROPIC_API_KEY" in response.json()["detail"]


async def test_ingredient_edits_invalidate_old_vectors(api_client, db):
    created = api_client.post(
        "/api/v1/ingredients", json={"name": "potato", "category": "vegetable"}
    )
    ingredient_id = created.json()["_id"]
    for path, payload in [
        (f"/api/v1/ingredients/{ingredient_id}", {"name": "sweet potato"}),
        (f"/api/v1/ingredients/{ingredient_id}/synonyms", {"name": "shakarkandi"}),
    ]:
        await db.ingredients.update_one(
            {"_id": ObjectId(ingredient_id)},
            {
                "$set": {
                    "embedding": [1.0, 0.0, 0.0],
                    "embedding_model": "test",
                    "embedding_text": "potato",
                }
            },
        )
        method = api_client.post if path.endswith("synonyms") else api_client.patch
        assert method(path, json=payload).status_code == 200
        stored = await db.ingredients.find_one({"_id": ObjectId(ingredient_id)})
        assert "embedding_model" not in stored


def test_new_inventory_items_still_need_positive_quantity(api_client):
    response = api_client.post(
        "/api/v1/items",
        json={
            "name": "Rice",
            "quantity": 0,
            "unit": "kg",
            "location": "pantry",
        },
    )
    assert response.status_code == 422
