"""Isolated API tests: no application database or paid model services are used."""

import json

import pytest
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient

from idunn.api.recipes import get_ingest_service
from idunn.config import Settings
from idunn.db import get_db
from idunn.main import app
from idunn.services.recipe_ingest import RecipeIngestService


@pytest.fixture
def config():
    return Settings(
        _env_file=None, anthropic_api_key=None, voyage_api_key=None,
        embedding_dimensions=3,
    )


@pytest.fixture
def db():
    return AsyncMongoMockClient()["idunn_test"]


@pytest.fixture
def service(db, config):
    return RecipeIngestService(db, config)


@pytest.fixture
def api_client(db, service):
    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_ingest_service] = lambda: service
    # No lifespan: a unit test must not connect to the developer's configured MongoDB.
    client = TestClient(app)
    try:
        yield client
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)


@pytest.fixture
def recipe_data():
    return {
        "title": "Aloo Gobi",
        "ingredients": [{"name": "aloo", "quantity": 2, "unit": "piece"}],
        "steps": [{"step_number": 1, "instruction": "Cook until tender."}],
        "region": "north_india",
        "description": "A simple curry",
    }


@pytest.fixture
def recipe_html():
    data = {
        "@context": "https://schema.org",
        "@type": "Recipe",
        "name": "Aloo Gobi",
        "recipeIngredient": ["2 aloo", "½ tsp haldi"],
        "recipeInstructions": [
            {"@type": "HowToSection", "name": "Cook", "itemListElement": [
                {"@type": "HowToStep", "text": "Heat oil."},
                {"@type": "HowToStep", "text": "Add vegetables and cook."},
            ]},
        ],
        "recipeYield": ["4 servings"],
        "prepTime": "PT1H15M",
        "cookTime": "PT30M30S",
        "image": [{"@type": "ImageObject", "url": "/curry.jpg"}],
    }
    return '<html><script type="application/ld+json">' + json.dumps(data) + '</script></html>'
