"""Tests for recipe API endpoints - Phase 2."""

from __future__ import annotations

from datetime import datetime
from typing import Generator

import pytest
from fastapi.testclient import TestClient

from idunn.main import app
from idunn.models.recipe import RecipeCreate, Region, CuisineType


@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    """Create test client."""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def sample_recipe() -> dict:
    """Sample recipe data."""
    return {
        "title": "Aloo Gobi",
        "description": "North Indian dry potato and cauliflower curry",
        "ingredients": [
            {"name": "potato", "quantity": 2.0, "unit": "piece"},
            {"name": "cauliflower", "quantity": 1.0, "unit": "piece"},
            {"name": "turmeric", "quantity": 0.5, "unit": "tsp"},
            {"name": "cumin seeds", "quantity": 1.0, "unit": "tsp"},
        ],
        "steps": [
            {"step_number": 1, "instruction": "Heat oil in a pan"},
            {"step_number": 2, "instruction": "Add cumin seeds and let them splutter"},
            {"step_number": 3, "instruction": "Add potatoes and cook for 5 minutes"},
            {"step_number": 4, "instruction": "Add cauliflower and spices, mix well"},
            {"step_number": 5, "instruction": "Cover and cook for 10 minutes until done"},
        ],
        "region": Region.NORTH.value,
        "cuisine_type": CuisineType.VEG.value,
        "difficulty": "easy",
        "prep_time_minutes": 15,
        "cook_time_minutes": 20,
        "servings": 4,
        "tags": ["north_indian", "dry_curry", "veg"],
    }


class TestCreateRecipe:
    def test_create_recipe_success(self, client, sample_recipe):
        """Test successful recipe creation."""
        response = client.post("/api/v1/recipes", json=sample_recipe)
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Aloo Gobi"
        assert len(data["ingredients"]) == 4
        assert len(data["steps"]) == 5
        assert data["region"] == "north_india"
        assert data["cuisine_type"] == "veg"


class TestListRecipes:
    def test_list_recipes_empty(self, client):
        """Test listing when no recipes exist."""
        response = client.get("/api/v1/recipes")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_recipes_with_region_filter(self, client, sample_recipe):
        """Test filtering by region."""
        # Create a recipe
        client.post("/api/v1/recipes", json=sample_recipe)

        # Filter by north_india
        response = client.get(f"/api/v1/recipes?region={Region.NORTH.value}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert all(r["region"] == Region.NORTH.value for r in data)


class TestIngestRecipe:
    def test_ingest_not_implemented(self, client):
        """Test that ingest endpoint returns 501 (not implemented)."""
        response = client.post(
            "/api/v1/recipes/ingest", params={"url": "https://example.com/recipe"}
        )
        # Currently returns 501 (not implemented in service)
        assert response.status_code == 501
