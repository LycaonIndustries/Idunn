"""Tests for Cook AI and Shopping List data models.

Ensures strict validation of pantry matching results, substitution
proposals, pantry-to-plate schemas, and quick-commerce shopping links.
"""

from datetime import UTC, datetime

from backend.models.cook_ai import (
    PantryMatchResult,
    PantryToPlateRequest,
    PantryToPlateResponse,
    ShoppingList,
    ShoppingListItem,
    SubstitutionSuggestion,
)


def test_pantry_match_result_validation():
    """Verify PantryMatchResult computes can_cook_now flag and validates fields."""
    match = PantryMatchResult(
        recipe_id="rec_123",
        recipe_title="Palak Paneer",
        coverage_percentage=100.0,
        matched_ingredients=["palak", "paneer", "garlic", "onion"],
        missing_ingredients=[],
        expiry_urgency_score=20,
        can_cook_now=True,
    )
    assert match.recipe_id == "rec_123"
    assert match.can_cook_now is True
    assert match.coverage_percentage == 100.0
    assert len(match.missing_ingredients) == 0


def test_pantry_match_result_partial_coverage():
    """Verify PantryMatchResult handles partial matches with missing items."""
    match = PantryMatchResult(
        recipe_id="rec_456",
        recipe_title="Chole Bhature",
        coverage_percentage=60.0,
        matched_ingredients=["chana", "onion"],
        missing_ingredients=["maida", "baking soda"],
        expiry_urgency_score=0,
        can_cook_now=False,
    )
    assert match.can_cook_now is False
    assert len(match.missing_ingredients) == 2


def test_substitution_suggestion_validation():
    """Verify in-stock substitution suggestion schema."""
    sub = SubstitutionSuggestion(
        missing_ingredient="fresh cream",
        substitute_item="curd (dahi)",
        ratio_or_amount="1:1 ratio, whisked until smooth",
        reason="Adds required acidity and body without purchasing dairy cream",
        in_stock=True,
    )
    assert sub.missing_ingredient == "fresh cream"
    assert sub.in_stock is True


def test_pantry_to_plate_request_defaults():
    """Verify default values for pantry-to-plate generation request."""
    req = PantryToPlateRequest()
    assert req.servings == 2
    assert req.dietary_preference is None
    assert req.max_prep_time_minutes is None


def test_pantry_to_plate_response_validation():
    """Verify structure of generated pantry-to-plate recipe."""
    res = PantryToPlateResponse(
        title="Quick Jeera Aloo",
        description="Spiced cumin potatoes made from pantry staples",
        ingredients=[
            {"item": "potato", "amount": 3.0, "unit": "piece"},
            {"item": "cumin seeds", "amount": 1.0, "unit": "tsp"},
        ],
        steps=["Boil potatoes", "Heat oil and add cumin", "Toss potatoes with spices"],
        prep_time_minutes=10,
        cook_time_minutes=15,
        servings=2,
        used_expiring_items=["potato"],
    )
    assert res.title == "Quick Jeera Aloo"
    assert len(res.steps) == 3
    assert "potato" in res.used_expiring_items


def test_shopping_list_item_quick_commerce_urls():
    """Verify generation of Blinkit, Zepto, and Instamart search deep links."""
    item = ShoppingListItem(
        id="shop_1",
        name="Kasuri Methi 50g",
        quantity=1.0,
        unit="packet",
        recipe_id="rec_789",
        is_purchased=False,
        created_at=datetime.now(UTC),
    )
    blinkit_url = item.get_quick_commerce_url("blinkit")
    zepto_url = item.get_quick_commerce_url("zepto")
    instamart_url = item.get_quick_commerce_url("instamart")

    assert "blinkit.com/s/?q=" in blinkit_url
    assert "Kasuri" in blinkit_url
    assert "zepto.com/search?q=" in zepto_url
    assert "swiggy.com/instamart/search?query=" in instamart_url


def test_shopping_list_container():
    """Verify aggregate shopping list collection model."""
    item = ShoppingListItem(
        id="shop_1",
        name="Paneer",
        quantity=200.0,
        unit="g",
        recipe_id=None,
        is_purchased=False,
        created_at=datetime.now(UTC),
    )
    shopping_list = ShoppingList(items=[item], total_count=1)
    assert shopping_list.total_count == 1
    assert shopping_list.items[0].name == "Paneer"
