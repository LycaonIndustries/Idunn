"""Tests for inventory models - Phase 1.

Tests unit conversions using Hypothesis property-based testing
as specified in the design doc exit criteria.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from backend.models.inventory import (
    UNIT_CONVERSIONS,
    Item,
    ItemCreate,
    Location,
    Unit,
)


class TestUnitConversions:
    """Test Indian unit graph conversions."""

    def test_gram_to_kilogram(self):
        """1 kg = 1000 g"""
        item = Item(
            _id="test1",
            name="Rice",
            quantity=1000,
            unit=Unit.GRAM,
            location=Location.PANTRY,
            added_at=datetime.now(UTC),
        )
        result = item.convert_quantity(Unit.KILOGRAM)
        assert result == pytest.approx(1.0)

    def test_kilogram_to_gram(self):
        """1000 g = 1 kg"""
        item = Item(
            _id="test2",
            name="Rice",
            quantity=1,
            unit=Unit.KILOGRAM,
            location=Location.PANTRY,
            added_at=datetime.now(UTC),
        )
        result = item.convert_quantity(Unit.GRAM)
        assert result == pytest.approx(1000.0)

    def test_paav_to_gram(self):
        """1 paav = 250 g"""
        item = Item(
            _id="test3",
            name="Atta",
            quantity=1,
            unit=Unit.PAAV,
            location=Location.DRY_STORE,
            added_at=datetime.now(UTC),
        )
        result = item.convert_quantity(Unit.GRAM)
        assert result == pytest.approx(250.0)

    def test_chamcha_to_ml(self):
        """1 chamcha ≈ 5 ml (≈ 1 tsp)"""
        item = Item(
            _id="test4",
            name="Oil",
            quantity=1,
            unit=Unit.CHAMCHA,
            location=Location.SPICE_BOX,
            added_at=datetime.now(UTC),
        )
        result = item.convert_quantity(Unit.MILLILITER)
        assert result == pytest.approx(5.0)

    def test_katori_to_ml(self):
        """1 katori ≈ 150 ml"""
        item = Item(
            _id="test5",
            name="Dal",
            quantity=1,
            unit=Unit.KATORI,
            location=Location.FRIDGE,
            added_at=datetime.now(UTC),
        )
        result = item.convert_quantity(Unit.MILLILITER)
        assert result == pytest.approx(150.0)

    def test_katori_to_tablespoon(self):
        """1 katori ≈ 10 tbsp (150ml / 15ml)"""
        item = Item(
            _id="test6",
            name="Yogurt",
            quantity=1,
            unit=Unit.KATORI,
            location=Location.FRIDGE,
            added_at=datetime.now(UTC),
        )
        result = item.convert_quantity(Unit.TABLESPOON)
        assert result == pytest.approx(10.0)

    def test_teaspoon_to_tablespoon(self):
        """1 tbsp = 3 tsp"""
        item = Item(
            _id="test7",
            name="Turmeric",
            quantity=3,
            unit=Unit.TEASPOON,
            location=Location.SPICE_BOX,
            added_at=datetime.now(UTC),
        )
        result = item.convert_quantity(Unit.TABLESPOON)
        assert result == pytest.approx(1.0)

    def test_invalid_conversion_returns_none(self):
        """Count units can't convert to mass/volume."""
        item = Item(
            _id="test8",
            name="Onions",
            quantity=5,
            unit=Unit.PIECE,
            location=Location.PANTRY,
            added_at=datetime.now(UTC),
        )
        result = item.convert_quantity(Unit.GRAM)
        assert result is None

    @given(
        quantity=st.floats(
            min_value=0.001, max_value=1000.0, allow_nan=False, allow_infinity=False
        ),
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_gram_kilogram_roundtrip(self, quantity):
        """Converting g → kg → g should return original value."""
        item = Item(
            _id="test9",
            name="Test",
            quantity=quantity,
            unit=Unit.GRAM,
            location=Location.PANTRY,
            added_at=datetime.now(UTC),
        )
        kg = item.convert_quantity(Unit.KILOGRAM)
        assert kg is not None

        # Create a new item in kg and convert back
        item2 = Item(
            _id="test10",
            name="Test",
            quantity=kg,
            unit=Unit.KILOGRAM,
            location=Location.PANTRY,
            added_at=datetime.now(UTC),
        )
        grams_back = item2.convert_quantity(Unit.GRAM)
        assert grams_back == pytest.approx(quantity, rel=1e-6)

    @given(
        quantity=st.floats(
            min_value=0.001, max_value=1000.0, allow_nan=False, allow_infinity=False
        ),
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_ml_liter_roundtrip(self, quantity):
        """Converting ml → l → ml should return original value."""
        item = Item(
            _id="test11",
            name="Test",
            quantity=quantity,
            unit=Unit.MILLILITER,
            location=Location.PANTRY,
            added_at=datetime.now(UTC),
        )
        liters = item.convert_quantity(Unit.LITER)
        assert liters is not None

        item2 = Item(
            _id="test12",
            name="Test",
            quantity=liters,
            unit=Unit.LITER,
            location=Location.PANTRY,
            added_at=datetime.now(UTC),
        )
        ml_back = item2.convert_quantity(Unit.MILLILITER)
        assert ml_back == pytest.approx(quantity, rel=1e-6)

    def test_all_conversion_paths_exist(self):
        """Verify all defined conversion paths work."""
        for (from_unit, to_unit), factor in UNIT_CONVERSIONS.items():
            item = Item(
                _id="test",
                name="Test",
                quantity=1.0,
                unit=from_unit,
                location=Location.PANTRY,
                added_at=datetime.now(UTC),
            )
            result = item.convert_quantity(to_unit)
            assert result == pytest.approx(factor), f"Failed: {from_unit} → {to_unit}"


class TestItemModel:
    """Test Item model validation and methods."""

    def test_item_create_basic(self):
        """Basic item creation."""
        item = ItemCreate(
            name="Potatoes",
            quantity=2.5,
            unit=Unit.KILOGRAM,
            location=Location.PANTRY,
        )
        assert item.name == "Potatoes"
        assert item.quantity == 2.5
        assert item.unit == Unit.KILOGRAM

    def test_item_create_with_expiry(self):
        """Item with expiry date."""
        from datetime import UTC, datetime

        expiry = datetime.now(UTC) + timedelta(days=7)
        item = ItemCreate(
            name="Milk",
            quantity=1,
            unit=Unit.LITER,
            location=Location.FRIDGE,
            expiry_date=expiry,
        )
        assert item.expiry_date is not None

    def test_item_create_invalid_quantity(self):
        """Zero or negative quantity should fail."""
        with pytest.raises(ValidationError):  # Pydantic validation error
            ItemCreate(
                name="Test",
                quantity=0,
                unit=Unit.PIECE,
                location=Location.PANTRY,
            )

    def test_item_is_expired(self):
        """Test expiry check."""
        from datetime import UTC, datetime

        # Expired item
        old_expiry = datetime.now(UTC) - timedelta(days=1)
        item = Item(
            _id="test123",
            name="Expired Milk",
            quantity=1,
            unit=Unit.LITER,
            location=Location.FRIDGE,
            expiry_date=old_expiry,
            added_at=datetime.now(UTC),
        )
        assert item.is_expired() is True

    def test_item_not_expired(self):
        """Test non-expired item."""
        from datetime import UTC, datetime

        future_expiry = datetime.now(UTC) + timedelta(days=7)
        item = Item(
            _id="test123",
            name="Fresh Milk",
            quantity=1,
            unit=Unit.LITER,
            location=Location.FRIDGE,
            expiry_date=future_expiry,
            added_at=datetime.now(UTC),
        )
        assert item.is_expired() is False
        assert item.is_expiring_soon(3) is False
        # This item expires in 7 days, so it IS expiring soon if we ask for 10 days
        assert item.is_expiring_soon(10) is True


class TestLocationEnum:
    """Test Location enum values."""

    def test_all_locations(self):
        """Verify all expected locations exist."""
        expected = [
            "fridge",
            "freezer",
            "pantry",
            "dry_store",
            "cabinet",
            "counter",
            "spice_box",
            "windowsill",
        ]
        actual = [loc.value for loc in Location]
        assert set(actual) == set(expected)


class TestUnitEnum:
    """Test Unit enum values."""

    def test_mass_units(self):
        """Mass units exist."""
        assert Unit.GRAM.value == "g"
        assert Unit.KILOGRAM.value == "kg"
        assert Unit.PAAV.value == "paav"

    def test_volume_units(self):
        """Volume units exist."""
        assert Unit.MILLILITER.value == "ml"
        assert Unit.LITER.value == "l"
        assert Unit.TEASPOON.value == "tsp"
        assert Unit.TABLESPOON.value == "tbsp"
        assert Unit.CHAMCHA.value == "chamcha"
        assert Unit.KATORI.value == "katori"

    def test_count_units(self):
        """Count units exist."""
        assert Unit.PIECE.value == "piece"
        assert Unit.BUNCH.value == "bunch"
        assert Unit.PACKET.value == "packet"
        assert Unit.BOX.value == "box"
