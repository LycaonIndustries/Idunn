"""Tests for strict in-stock substitution engine.

Validates Indian culinary substitution table matching, strict in-stock
enforcement, and provider fallback behavior.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock

from backend.models.inventory import Item, Location, Unit
from backend.services.substitution_engine import (
    find_substitutes,
)


def _make_item(name: str) -> Item:
    """Helper to create active pantry item."""
    return Item(
        _id=f"item_{name}",
        name=name,
        quantity=500.0,
        unit=Unit.GRAM,
        location=Location.FRIDGE,
        added_at=datetime.now(UTC),
        consumed=False,
    )


def test_find_substitutes_in_stock_match():
    """Verify substitution succeeds when a valid replacement is in the pantry."""
    # User lacks sour cream, but has curd (dahi) in fridge
    pantry = [_make_item("curd"), _make_item("onion")]

    sub = find_substitutes("sour cream", pantry)
    assert sub is not None
    assert sub.missing_ingredient == "sour cream"
    assert "curd" in sub.substitute_item.lower() or "dahi" in sub.substitute_item.lower()
    assert sub.in_stock is True


def test_find_substitutes_rejected_when_not_in_stock():
    """Verify substitution is rejected when candidate replacement is absent."""
    # User lacks sour cream, but pantry does NOT have curd, yogurt, or malai
    pantry = [_make_item("potato"), _make_item("rice")]

    sub = find_substitutes("sour cream", pantry)
    assert sub is None


def test_find_substitutes_indian_staples():
    """Verify various Indian staple substitutions."""
    # Kasuri methi absent, but fresh methi present
    pantry1 = [_make_item("fresh methi")]
    sub1 = find_substitutes("kasuri methi", pantry1)
    assert sub1 is not None
    assert "methi" in sub1.substitute_item.lower()

    # Lemon juice absent, but amchur present
    pantry2 = [_make_item("amchur powder")]
    sub2 = find_substitutes("lemon juice", pantry2)
    assert sub2 is not None
    assert "amchur" in sub2.substitute_item.lower()

    # Tomato puree absent, but fresh tomatoes present
    pantry3 = [_make_item("tomato")]
    sub3 = find_substitutes("tomato puree", pantry3)
    assert sub3 is not None
    assert "tomato" in sub3.substitute_item.lower()


def test_find_substitutes_provider_fallback_success():
    """Verify provider fallback selects candidate strictly from pantry list."""
    pantry = [_make_item("walnut"), _make_item("cumin")]
    mock_provider = MagicMock()
    mock_provider.generate_structured_content.return_value = {
        "missing_ingredient": "pecan",
        "substitute_item": "walnut",
        "ratio_or_amount": "1:1 ratio, roughly chopped",
        "reason": "Walnuts have a similar buttery crunch and rich oil content",
        "in_stock": True,
    }

    sub = find_substitutes("pecan", pantry, provider=mock_provider)
    assert sub is not None
    assert sub.substitute_item == "walnut"
    mock_provider.generate_structured_content.assert_called_once()


def test_find_substitutes_provider_fallback_none():
    """Verify provider fallback returns None when no suitable item in pantry."""
    pantry = [_make_item("mustard oil")]
    mock_provider = MagicMock()
    mock_provider.generate_structured_content.return_value = None

    sub = find_substitutes("chocolate", pantry, provider=mock_provider)
    assert sub is None
