"""Tests for recipe matching and ranking against pantry stock.

Validates coverage calculation, regional synonym matching, expiry urgency
scoring, and pantry-first ranking.
"""

from datetime import UTC, datetime, timedelta

from backend.models.inventory import Item, Location, Unit
from backend.models.recipe import IngredientItem, Recipe, Region, Step
from backend.services.recipe_matching import (
    calculate_recipe_pantry_match,
    rank_recipes_for_pantry,
)


def _make_item(name: str, days_to_expiry: int | None = None) -> Item:
    """Helper to create dummy Item."""
    expiry = None
    if days_to_expiry is not None:
        expiry = datetime.now(UTC) + timedelta(days=days_to_expiry)
    return Item(
        _id=f"item_{name}",
        name=name,
        quantity=500.0,
        unit=Unit.GRAM,
        location=Location.FRIDGE,
        added_at=datetime.now(UTC),
        expiry_date=expiry,
        consumed=False,
    )


def _make_recipe(recipe_id: str, title: str, ingredient_names: list[str]) -> Recipe:
    """Helper to create dummy Recipe."""
    return Recipe(
        _id=recipe_id,
        title=title,
        prep_time_minutes=15,
        cook_time_minutes=20,
        region=Region.NORTH,
        ingredients=[
            IngredientItem(name=name, quantity=100.0, unit="g") for name in ingredient_names
        ],
        steps=[
            Step(step_number=1, instruction="Step 1"),
            Step(step_number=2, instruction="Step 2"),
        ],
    )


def test_calculate_recipe_pantry_match_full_match():
    """Verify 100% coverage when all ingredients are present."""
    pantry = [
        _make_item("paneer"),
        _make_item("palak"),
        _make_item("garlic"),
    ]
    recipe = _make_recipe("r1", "Palak Paneer", ["palak", "paneer", "garlic"])

    result = calculate_recipe_pantry_match(recipe, pantry)
    assert result.recipe_id == "r1"
    assert result.can_cook_now is True
    assert result.coverage_percentage == 100.0
    assert set(result.matched_ingredients) == {"palak", "paneer", "garlic"}
    assert result.missing_ingredients == []


def test_calculate_recipe_pantry_match_synonyms():
    """Verify Hindi and English regional synonyms match correctly."""
    pantry = [
        _make_item("spinach"),
        _make_item("cottage cheese"),
        _make_item("lahsun"),
    ]
    # Recipe uses Hindi / Indian names: palak, paneer, garlic
    recipe = _make_recipe("r1", "Palak Paneer", ["palak", "paneer", "garlic"])

    result = calculate_recipe_pantry_match(recipe, pantry)
    assert result.can_cook_now is True
    assert result.coverage_percentage == 100.0
    assert len(result.missing_ingredients) == 0


def test_calculate_recipe_pantry_match_partial():
    """Verify partial coverage calculation and missing ingredients list."""
    pantry = [
        _make_item("paneer"),
    ]
    recipe = _make_recipe("r2", "Matar Paneer", ["paneer", "green peas", "tomato"])

    result = calculate_recipe_pantry_match(recipe, pantry)
    assert result.can_cook_now is False
    assert round(result.coverage_percentage, 1) == 33.3
    assert result.matched_ingredients == ["paneer"]
    assert set(result.missing_ingredients) == {"green peas", "tomato"}


def test_expiry_urgency_boost_scoring():
    """Verify recipes using soon-to-expire ingredients receive higher score."""
    # Item expiring tomorrow (urgent: +20 points)
    expiring_soon = _make_item("tomato", days_to_expiry=1)
    # Long shelf-life staple (0 bonus points)
    shelf_stable = _make_item("rice", days_to_expiry=90)

    pantry = [expiring_soon, shelf_stable]
    recipe_urgent = _make_recipe("r_urg", "Tomato Rice", ["tomato", "rice"])
    recipe_plain = _make_recipe("r_pln", "Steamed Rice", ["rice"])

    res_urg = calculate_recipe_pantry_match(recipe_urgent, pantry)
    res_pln = calculate_recipe_pantry_match(recipe_plain, pantry)

    assert res_urg.expiry_urgency_score > res_pln.expiry_urgency_score
    assert res_urg.expiry_urgency_score >= 20


def test_rank_recipes_for_pantry():
    """Verify ranking order: can_cook_now > expiry_urgency > coverage."""
    pantry = [
        _make_item("palak", days_to_expiry=1),  # expiring soon!
        _make_item("paneer", days_to_expiry=5),
        _make_item("dal", days_to_expiry=60),
    ]

    r1 = _make_recipe("r1", "Palak Paneer", ["palak", "paneer"])  # 100% + expiring
    r2 = _make_recipe("r2", "Tadkaa Dal", ["dal"])  # 100% no expiring
    r3 = _make_recipe("r3", "Dal Palak Paneer Butter", ["palak", "paneer", "dal", "butter"])  # 75%

    ranked = rank_recipes_for_pantry([r2, r3, r1], pantry)
    # r1 should be #1 because it is 100% match and has expiring palak
    assert ranked[0].recipe_id == "r1"
    # r2 should be #2 because it is 100% match
    assert ranked[1].recipe_id == "r2"
    # r3 should be #3 because it is missing butter
    assert ranked[2].recipe_id == "r3"


def test_rank_recipes_filter_ready_only():
    """Verify ready_only filters out incomplete recipes."""
    pantry = [_make_item("dal")]
    r1 = _make_recipe("r1", "Dal Fry", ["dal"])
    r2 = _make_recipe("r2", "Dal Makhani", ["dal", "butter", "cream"])

    ranked = rank_recipes_for_pantry([r1, r2], pantry, ready_only=True)
    assert len(ranked) == 1
    assert ranked[0].recipe_id == "r1"
