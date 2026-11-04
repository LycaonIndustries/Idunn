"""Whole import pipeline with real parsing/models and isolated external boundaries."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from bson import ObjectId
from pymongo.errors import AutoReconnect

from backend.models.recipe import RecipeCreate
from backend.services.ingest_errors import ExtractionError, ProviderError
from backend.services.recipe_providers import ExtractedRecipe
from backend.services.recipe_sources import SourcePage


def extracted(data, confidence=1):
    return ExtractedRecipe(recipe=RecipeCreate(**data), confidence=confidence)


async def test_exact_synonyms_link_in_order_without_embeddings(
    service, db, recipe_html, monkeypatch
):
    potato = await db.ingredients.insert_one({
        "name": "potato", "synonyms": [{"name": "aloo"}],
    })
    turmeric = await db.ingredients.insert_one({
        "name": "turmeric", "synonyms": [{"name": "haldi"}],
    })
    page = SourcePage(recipe_html, "https://example.org/r")
    monkeypatch.setattr(service.reader.fetcher, "fetch", AsyncMock(return_value=page))
    result = await service.ingest_from_url("https://example.org/r")
    doc = await db.recipes.find_one({"_id": ObjectId(result.recipe_id)})
    assert doc["normalized_ingredients"] == [str(potato.inserted_id), str(turmeric.inserted_id)]
    assert doc["needs_review"] is False
    assert [m["ingredient_index"] for m in doc["ingredient_matches"]] == [0, 1]
    assert doc["embedding"] is None
    assert "VOYAGE_API_KEY" in result.warnings[0]


async def test_ambiguous_synonym_is_not_guessed(service, db, recipe_data):
    for name in ("potato", "sweet potato"):
        await db.ingredients.insert_one({"name": name, "synonyms": [{"name": "aloo"}]})
    result = await service.store(extracted(recipe_data), "manual")
    doc = await db.recipes.find_one({"_id": ObjectId(result.recipe_id)})
    assert doc["normalized_ingredients"] == []
    assert doc["ingredient_matches"][0]["status"] == "pending"


async def test_synonym_region_disambiguates(service, db, recipe_data):
    north = await db.ingredients.insert_one({
        "name": "potato", "synonyms": [{"name": "aloo", "region": "north_india"}],
    })
    await db.ingredients.insert_one({
        "name": "another tuber", "synonyms": [{"name": "aloo", "region": "south_india"}],
    })
    result = await service.store(extracted(recipe_data), "manual")
    doc = await db.recipes.find_one({"_id": ObjectId(result.recipe_id)})
    assert doc["normalized_ingredients"] == [str(north.inserted_id)]


@pytest.mark.parametrize(
    ("scores", "ready"), [([0.97, 0.7], True), ([0.97, 0.96], False), ([0.7], False)]
)
async def test_vector_threshold_and_ambiguity_margin(
    service, db, recipe_data, monkeypatch, scores, ready
):
    ids = [ObjectId() for _ in scores]
    service.embedder.config.voyage_api_key = "test-key"
    monkeypatch.setattr(service.embedder, "embed", AsyncMock(return_value=[[1.0, 0.0, 0.0]]))

    def aggregate(pipeline):
        assert pipeline[0]["$vectorSearch"]["filter"] == {"embedding_model": "voyage-3-large"}
        return SimpleNamespace(to_list=AsyncMock(return_value=[
            {"_id": item, "score": score} for item, score in zip(ids, scores, strict=True)
        ]))

    monkeypatch.setattr(service.matcher.collection, "aggregate", aggregate)
    result = await service.store(extracted(recipe_data), "manual")
    doc = await db.recipes.find_one({"_id": ObjectId(result.recipe_id)})
    assert doc["needs_review"] is not ready
    assert doc["ingredient_matches"][0]["suggested_id"] == str(ids[0])
    assert doc["normalized_ingredients"] == ([str(ids[0])] if ready else [])
    assert doc["embedding"] == [1.0, 0.0, 0.0]


async def test_invalid_extraction_is_not_stored(service, db):
    with pytest.raises(ExtractionError):
        await service.store(extracted({"title": "Not a recipe"}, confidence=0), "blog")
    assert await db.recipes.count_documents({}) == 0


async def test_provider_failure_does_not_save_partial_recipe(
    service, db, recipe_data, monkeypatch
):
    service.embedder.config.voyage_api_key = "test-key"
    monkeypatch.setattr(service.embedder, "embed", AsyncMock(side_effect=ProviderError("offline")))
    with pytest.raises(ProviderError):
        await service.store(extracted(recipe_data), "blog")
    assert await db.recipes.count_documents({}) == 0


async def test_database_failure_propagates(service, db, recipe_data, monkeypatch):
    failure = AsyncMock(side_effect=AutoReconnect("unavailable"))
    monkeypatch.setattr(type(db.recipes), "insert_one", failure)
    with pytest.raises(AutoReconnect):
        await service.store(extracted(recipe_data), "manual")


async def test_uncertain_extraction_stays_in_review_with_exact_matches(service, db, recipe_data):
    await db.ingredients.insert_one({"name": "aloo"})
    result = await service.store(extracted(recipe_data, confidence=0.4), "blog")
    assert result.needs_review is True
