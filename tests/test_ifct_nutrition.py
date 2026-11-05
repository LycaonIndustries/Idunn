"""Tests for ICMR/NIN IFCT nutrition calculation engine and endpoints."""

from __future__ import annotations

from starlette.testclient import TestClient

from backend.api.deps import AuthenticatedUser, get_current_user
from backend.main import app
from backend.models.recipe import IngredientItem, Recipe
from backend.services.ifct_nutrition import (
    calculate_recipe_nutrition,
    convert_ingredient_to_grams,
    find_ifct_match,
)


def test_ifct_alias_matching() -> None:
    """Verify alias lookup matches regional Hindi and English ingredient terms."""
    # Multi-word alias lookup.
    arhar = find_ifct_match("arhar dal")
    assert arhar is not None
    assert arhar.food_code == "B001"

    toor = find_ifct_match("organic toor dal")
    assert toor is not None
    assert toor.food_code == "B001"

    # Regional vegetable alias lookup.
    palak = find_ifct_match("fresh palak leaves")
    assert palak is not None
    assert palak.food_code == "D001"

    spinach = find_ifct_match("spinach")
    assert spinach is not None
    assert spinach.food_code == "D001"

    # Fat and oil matching.
    ghee = find_ifct_match("desi ghee")
    assert ghee is not None
    assert ghee.food_code == "C004"

    # Non-food or unrecognized token returns None.
    assert find_ifct_match("xylitol powder") is None


def test_indian_unit_conversions() -> None:
    """Verify Indian kitchen unit conversions to gram equivalents."""
    # Traditional Indian mass unit paav (250g).
    assert (
        convert_ingredient_to_grams(IngredientItem(name="paneer", quantity=2.0, unit="paav"))
        == 500.0
    )

    # Volumetric katori / cup (150g).
    assert (
        convert_ingredient_to_grams(IngredientItem(name="dahi", quantity=1.0, unit="katori"))
        == 150.0
    )

    # Spoon measures chamcha / tsp (5g) and tbsp (15g).
    assert (
        convert_ingredient_to_grams(IngredientItem(name="haldi", quantity=2.0, unit="tsp")) == 10.0
    )
    assert (
        convert_ingredient_to_grams(IngredientItem(name="ghee", quantity=1.0, unit="tbsp")) == 15.0
    )

    # Discrete count measures for eggs and vegetables.
    assert (
        convert_ingredient_to_grams(IngredientItem(name="eggs", quantity=2.0, unit="nos")) == 100.0
    )
    assert (
        convert_ingredient_to_grams(IngredientItem(name="onion", quantity=1.0, unit="piece"))
        == 80.0
    )


def test_calculate_recipe_nutrition_macros() -> None:
    """Verify macronutrient summation and per-serving division across recipe ingredients."""
    # 2 servings recipe containing 100g paneer (18.3g protein, 20.8g fat, 257 kcal).
    recipe = Recipe(
        _id="test_rec_paneer",
        title="Quick Paneer Fry",
        ingredients=[
            IngredientItem(name="paneer", quantity=100.0, unit="g"),
            IngredientItem(name="ghee", quantity=10.0, unit="g"),
        ],
        servings=2,
        steps=[],
    )
    macros = calculate_recipe_nutrition(recipe)

    # Validate per-serving calculation.
    assert macros.is_ifct_verified is True
    # Total protein is 18.3g; per serving should be approx 9.2g.
    assert macros.protein == 9.2
    # Total calories = 257 (paneer) + 90 (10g ghee) = 347 kcal -> 173.5 kcal per serving.
    assert macros.calories == 173.5


def test_recipe_nutrition_api_lifecycle(api_client: TestClient) -> None:
    """Verify recipe creation auto-populates IFCT macros and recalculate endpoint functions."""
    caller = AuthenticatedUser(id="nutri_tester", email="nutri@test.com")
    app.dependency_overrides[get_current_user] = lambda: caller

    # Create recipe without explicit nutrition info.
    payload = {
        "title": "Homestyle Palak Paneer",
        "servings": 2,
        "ingredients": [
            {"name": "palak", "quantity": 200.0, "unit": "g"},
            {"name": "paneer", "quantity": 100.0, "unit": "g"},
        ],
        "steps": [{"step_number": 1, "instruction": "Blanch palak and saute paneer"}],
    }

    create_res = api_client.post("/api/v1/recipes", json=payload)
    assert create_res.status_code == 201
    created_data = create_res.json()
    rec_id = created_data["_id"]

    # Verify IFCT macros were automatically calculated on recipe creation.
    nutrition = created_data.get("nutrition")
    assert nutrition is not None
    assert nutrition["is_ifct_verified"] is True
    assert nutrition["protein"] is not None and nutrition["protein"] > 0

    # Call recalculate endpoint and verify response.
    recalc_res = api_client.post(f"/api/v1/recipes/{rec_id}/nutrition/calculate")
    assert recalc_res.status_code == 200
    recalc_data = recalc_res.json()
    assert recalc_data["nutrition"]["is_ifct_verified"] is True
    assert recalc_data["nutrition"]["protein"] == nutrition["protein"]
