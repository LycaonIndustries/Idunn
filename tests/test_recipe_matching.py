"""Unit tests for the algorithmic recipe pantry matcher and FEFO ranker."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from backend.models.inventory import Item, Location, Unit
from backend.models.recipe import IngredientItem, Recipe, Step
from backend.services.recipe_matching import RecipeMatchingService


def make_dummy_item(name: str, hours_to_expiry: float | None = None) -> Item:
    """Helper to instantiate mock inventory item."""
    expiry = datetime.now(UTC) + timedelta(hours=hours_to_expiry) if hours_to_expiry else None
    return Item(
        _id="item_1",
        name=name,
        quantity=500.0,
        unit=Unit.GRAM,
        location=Location.FRIDGE,
        expiry_date=expiry,
        consumed=False,
        added_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def make_dummy_recipe(title: str, ingredient_names: list[str]) -> Recipe:
    """Helper to instantiate mock recipe."""
    return Recipe(
        _id="rec_1",
        title=title,
        description="Test recipe",
        ingredients=[
            IngredientItem(name=ing, quantity=100.0, unit="g") for ing in ingredient_names
        ],
        steps=[Step(step_number=1, instruction="Cook")],
    )


def test_exact_match_all_ingredients_in_stock() -> None:
    """Verify recipe with 100% ingredients in stock returns can_cook_now True."""
    recipe = make_dummy_recipe("Jeera Aloo", ["potato", "cumin"])
    inventory = [make_dummy_item("potato"), make_dummy_item("cumin")]

    result = RecipeMatchingService.match_recipe(recipe, inventory)
    assert result.can_cook_now is True
    assert result.coverage_percentage == 100.0
    assert len(result.missing_ingredients) == 0
    assert "potato" in result.matched_ingredients


def test_partial_match_with_missing_items() -> None:
    """Verify recipe missing items reports correct coverage percentage."""
    recipe = make_dummy_recipe("Paneer Butter Masala", ["paneer", "butter", "tomato"])
    inventory = [make_dummy_item("paneer"), make_dummy_item("butter")]

    result = RecipeMatchingService.match_recipe(recipe, inventory)
    assert result.can_cook_now is False
    assert result.coverage_percentage == 66.7
    assert "tomato" in result.missing_ingredients


def test_regional_synonym_matching() -> None:
    """Verify Hindi regional aliases match English recipe ingredient names."""
    recipe = make_dummy_recipe("Dal Tadka", ["coriander leaves", "turmeric"])
    inventory = [make_dummy_item("dhania"), make_dummy_item("haldi")]

    result = RecipeMatchingService.match_recipe(recipe, inventory)
    assert result.coverage_percentage == 100.0
    assert result.can_cook_now is True


def test_fefo_expiry_urgency_boost() -> None:
    """Verify perishables expiring within 72 hours yield an urgency score."""
    recipe = make_dummy_recipe("Aloo Methi", ["potato"])
    inventory = [make_dummy_item("potato", hours_to_expiry=24.0)]

    result = RecipeMatchingService.match_recipe(recipe, inventory)
    assert result.expiry_urgency_score > 0.0


def test_empty_pantry_returns_zero_coverage() -> None:
    """Verify empty inventory returns 0% coverage without errors."""
    recipe = make_dummy_recipe("Curry", ["onion", "garlic"])
    result = RecipeMatchingService.match_recipe(recipe, [])
    assert result.coverage_percentage == 0.0
    assert result.can_cook_now is False
    assert len(result.missing_ingredients) == 2


def test_rank_recipes_sorts_by_coverage_and_expiry() -> None:
    """Verify rank_recipes orders results descending by coverage and FEFO score."""
    r1 = make_dummy_recipe("Fully Ready High Expiry", ["paneer"])
    r2 = make_dummy_recipe("Fully Ready Low Expiry", ["onion"])
    r3 = make_dummy_recipe("Partial Ready", ["potato", "tomato"])

    inventory = [
        make_dummy_item("paneer", hours_to_expiry=12.0),
        make_dummy_item("onion", hours_to_expiry=60.0),
        make_dummy_item("potato"),
    ]

    ranked = RecipeMatchingService.rank_recipes([r3, r2, r1], inventory)
    assert ranked[0].recipe_title == "Fully Ready High Expiry"
    assert ranked[1].recipe_title == "Fully Ready Low Expiry"
    assert ranked[2].recipe_title == "Partial Ready"
