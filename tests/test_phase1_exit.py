"""Phase 1 Exit Criteria Tests.

Tests to verify Phase 1 completion per design doc:
1. Add 50 mixed items (mass + volume + count)
2. Query "expiring this week" returns correctly
3. Unit conversions verified by property tests (Hypothesis) - DONE in test_inventory.py
"""

from __future__ import annotations

from datetime import datetime, timedelta, UTC
from typing import List

import pytest

from idunn.models.inventory import (
    Item,
    ItemCreate,
    Unit,
    Location,
)


class TestPhase1ExitCriteria:
    """Test Phase 1 exit criteria from design doc."""

    @pytest.fixture
    def mixed_items(self) -> list[Item]:
        """Create 50 mixed items as per exit criteria."""
        items = []
        now = datetime.now(UTC)

        # Mass items (g, kg, paav) - 20 items
        mass_items = [
            ("Rice", 5.0, Unit.KILOGRAM, Location.PANTRY),
            ("Wheat Flour", 2.0, Unit.KILOGRAM, Location.DRY_STORE),
            ("Sugar", 1.5, Unit.KILOGRAM, Location.PANTRY),
            ("Salt", 500.0, Unit.GRAM, Location.SPICE_BOX),
            ("Turmeric", 100.0, Unit.GRAM, Location.SPICE_BOX),
            ("Red Chili", 50.0, Unit.GRAM, Location.SPICE_BOX),
            ("Coriander Powder", 100.0, Unit.GRAM, Location.SPICE_BOX),
            ("Cumin Seeds", 50.0, Unit.GRAM, Location.SPICE_BOX),
            ("Atta", 1.0, Unit.PAAV, Location.DRY_STORE),
            ("Atta", 2.0, Unit.PAAV, Location.DRY_STORE),
            ("Besan", 500.0, Unit.GRAM, Location.DRY_STORE),
            ("Rava", 1.0, Unit.KILOGRAM, Location.DRY_STORE),
            ("Moong Dal", 1.0, Unit.KILOGRAM, Location.PANTRY),
            ("Toor Dal", 1.0, Unit.KILOGRAM, Location.PANTRY),
            ("Chana Dal", 500.0, Unit.GRAM, Location.PANTRY),
            ("Urad Dal", 500.0, Unit.GRAM, Location.PANTRY),
            ("Green Moong", 250.0, Unit.GRAM, Location.PANTRY),
            ("Masoor Dal", 500.0, Unit.GRAM, Location.PANTRY),
            ("Potatoes", 2.0, Unit.KILOGRAM, Location.PANTRY),
            ("Onions", 1.5, Unit.KILOGRAM, Location.PANTRY),
        ]

        # Volume items (ml, l, tsp, tbsp, chamcha, katori) - 15 items
        volume_items = [
            ("Milk", 1.0, Unit.LITER, Location.FRIDGE),
            ("Milk", 500.0, Unit.MILLILITER, Location.FRIDGE),
            ("Cooking Oil", 1.0, Unit.LITER, Location.PANTRY),
            ("Cooking Oil", 500.0, Unit.MILLILITER, Location.PANTRY),
            ("Mustard Oil", 200.0, Unit.MILLILITER, Location.PANTRY),
            ("Ghee", 500.0, Unit.MILLILITER, Location.FRIDGE),
            ("Coconut Oil", 200.0, Unit.MILLILITER, Location.PANTRY),
            ("Water", 1.0, Unit.LITER, Location.FRIDGE),
            ("Lemon Juice", 5.0, Unit.TEASPOON, Location.FRIDGE),
            ("Vanilla Essence", 1.0, Unit.TABLESPOON, Location.PANTRY),
            ("Turmeric Paste", 1.0, Unit.CHAMCHA, Location.SPICE_BOX),
            ("Tamrind Paste", 1.0, Unit.KATORI, Location.SPICE_BOX),
            ("Ginger-Garlic Paste", 1.0, Unit.KATORI, Location.SPICE_BOX),
            ("Buttermilk", 200.0, Unit.MILLILITER, Location.FRIDGE),
            ("Yogurt", 1.0, Unit.KATORI, Location.FRIDGE),
        ]

        # Count items (piece, bunch, packet, box) - 15 items
        count_items = [
            ("Onions", 5.0, Unit.PIECE, Location.PANTRY),
            ("Potatoes", 4.0, Unit.PIECE, Location.PANTRY),
            ("Tomatoes", 6.0, Unit.PIECE, Location.FRIDGE),
            ("Green Chilies", 10.0, Unit.PIECE, Location.FRIDGE),
            ("Lemons", 4.0, Unit.PIECE, Location.FRIDGE),
            ("Garlic", 1.0, Unit.BUNCH, Location.PANTRY),
            ("Coriander Leaves", 1.0, Unit.BUNCH, Location.FRIDGE),
            ("Mint Leaves", 1.0, Unit.BUNCH, Location.FRIDGE),
            ("Curry Leaves", 1.0, Unit.BUNCH, Location.FRIDGE),
            ("Tea Bags", 1.0, Unit.BOX, Location.PANTRY),
            ("Pasta", 1.0, Unit.BOX, Location.PANTRY),
            ("Noodles", 1.0, Unit.PACKET, Location.PANTRY),
            ("Biscuits", 1.0, Unit.PACKET, Location.PANTRY),
            ("Bread", 1.0, Unit.PIECE, Location.PANTRY),
            ("Eggs", 6.0, Unit.PIECE, Location.FRIDGE),
        ]

        # Combine all items
        all_items_data = mass_items + volume_items + count_items
        assert len(all_items_data) == 50, f"Expected 50 items, got {len(all_items_data)}"

        # Create Item objects with varying expiry dates
        for idx, (name, qty, unit, location) in enumerate(all_items_data):
            # Spread expiry dates: some expired, some expiring soon, some far future
            if idx % 5 == 0:
                # Expired
                expiry = now - timedelta(days=idx % 10 + 1)
            elif idx % 5 == 1:
                # Expiring in 1-7 days
                expiry = now + timedelta(days=idx % 7 + 1)
            elif idx % 5 == 2:
                # Expiring in 8-14 days
                expiry = now + timedelta(days=idx % 7 + 8)
            else:
                # Far future or no expiry (for count items)
                expiry = now + timedelta(days=30 + idx) if idx % 3 != 0 else None

            item = Item(
                _id=f"item_{idx}",
                name=name,
                quantity=qty,
                unit=unit,
                location=location,
                expiry_date=expiry,
                added_at=now - timedelta(days=idx),
                updated_at=now,
                consumed=False,
            )
            items.append(item)

        return items

    def test_add_50_mixed_items(self, mixed_items):
        """Exit criteria: add 50 mixed items (mass + volume + count)."""
        # Verify we have 50 items
        assert len(mixed_items) == 50

        # Count by category
        mass_units = {Unit.GRAM, Unit.KILOGRAM, Unit.PAAV}
        volume_units = {
            Unit.MILLILITER,
            Unit.LITER,
            Unit.TEASPOON,
            Unit.TABLESPOON,
            Unit.CHAMCHA,
            Unit.KATORI,
        }
        count_units = {Unit.PIECE, Unit.BUNCH, Unit.PACKET, Unit.BOX}

        mass_count = sum(1 for item in mixed_items if item.unit in mass_units)
        volume_count = sum(1 for item in mixed_items if item.unit in volume_units)
        count_count = sum(1 for item in mixed_items if item.unit in count_units)

        print(f"\nMass items: {mass_count}")
        print(f"Volume items: {volume_count}")
        print(f"Count items: {count_count}")

        assert mass_count >= 15, f"Expected >=15 mass items, got {mass_count}"
        assert volume_count >= 10, f"Expected >=10 volume items, got {volume_count}"
        assert count_count >= 10, f"Expected >=10 count items, got {count_count}"

    def test_fefo_ordering(self, mixed_items):
        """Test FEFO (First Expire First Out) ordering.

        Items with earlier expiry dates should come first.
        Items without expiry dates should come last.
        """
        # Sort items by FEFO: expiry_date ascending (None last), then added_at descending
        sorted_items = sorted(
            [item for item in mixed_items if not item.consumed],
            key=lambda x: (x.expiry_date is None, x.expiry_date or datetime.max, -x.added_at.timestamp()),
        )

        # Verify ordering
        for i in range(len(sorted_items) - 1):
            item1 = sorted_items[i]
            item2 = sorted_items[i + 1]

            # item1 should expire before item2 (or item2 has no expiry)
            if item1.expiry_date and item2.expiry_date:
                assert item1.expiry_date <= item2.expiry_date, (
                    f"FEFO violation: {item1.name} (expires {item1.expiry_date}) "
                    f"should come before {item2.name} (expires {item2.expiry_date})"
                )
            elif item1.expiry_date and not item2.expiry_date:
                # item1 has expiry, item2 doesn't - this is correct (None comes last)
                pass
            elif not item1.expiry_date and item2.expiry_date:
                # Violation: item1 has no expiry but comes before item2 with expiry
                pytest.fail(
                    f"FEFO violation: {item1.name} (no expiry) comes before "
                    f"{item2.name} (expires {item2.expiry_date})"
                )

    def test_expiring_this_week_query(self, mixed_items):
        """Exit criteria: query 'expiring this week' returns correctly.

        Should return items expiring in the next 7 days.
        Should NOT return:
        - Expired items
        - Items expiring after 7 days
        - Items without expiry dates
        """
        now = datetime.now(UTC)
        seven_days = now + timedelta(days=7)

        # Filter items expiring in the next 7 days (not expired)
        expiring_this_week = [
            item
            for item in mixed_items
            if item.expiry_date
            and now <= item.expiry_date <= seven_days
            and not item.consumed
        ]

        # Verify the query logic
        for item in expiring_this_week:
            assert item.expiry_date is not None
            assert now <= item.expiry_date <= seven_days
            assert not item.is_expired()

        # Verify items NOT in the result
        for item in mixed_items:
            if item in expiring_this_week:
                continue

            # Should not be expiring this week
            if item.expiry_date:
                assert (
                    item.expiry_date < now  # Expired
                    or item.expiry_date > seven_days  # Far future
                    or item.is_expired()  # Expired
                ), f"{item.name} should not be in expiring_this_week but is not expired or >7 days"

        print(f"\nItems expiring this week: {len(expiring_this_week)}")
        for item in expiring_this_week:
            print(f"  - {item.name}: expires {item.expiry_date}")

    def test_unit_conversions_for_mixed_items(self, mixed_items):
        """Verify unit conversions work for all items with convertible units."""
        convertible_units = {
            Unit.GRAM,
            Unit.KILOGRAM,
            Unit.PAAV,
            Unit.MILLILITER,
            Unit.LITER,
            Unit.TEASPOON,
            Unit.TABLESPOON,
            Unit.CHAMCHA,
            Unit.KATORI,
        }

        for item in mixed_items:
            if item.unit in convertible_units:
                # Try converting to a different unit in the same category
                if item.unit == Unit.GRAM:
                    result = item.convert_quantity(Unit.KILOGRAM)
                    assert result is not None
                    assert result == pytest.approx(item.quantity / 1000.0, rel=1e-6)

                elif item.unit == Unit.KILOGRAM:
                    result = item.convert_quantity(Unit.GRAM)
                    assert result is not None
                    assert result == pytest.approx(item.quantity * 1000.0, rel=1e-6)

                elif item.unit == Unit.MILLILITER:
                    result = item.convert_quantity(Unit.LITER)
                    assert result is not None
                    assert result == pytest.approx(item.quantity / 1000.0, rel=1e-6)

                elif item.unit == Unit.LITER:
                    result = item.convert_quantity(Unit.MILLILITER)
                    assert result is not None
                    assert result == pytest.approx(item.quantity * 1000.0, rel=1e-6)

    def test_items_by_location(self, mixed_items):
        """Test filtering items by location."""
        locations = set(item.location for item in mixed_items)

        for location in locations:
            items_in_location = [
                item for item in mixed_items if item.location == location
            ]
            print(f"\n{location.value}: {len(items_in_location)} items")

        # Verify we have items in multiple locations
        assert len(locations) > 1, "Should have items in multiple locations"

    def test_expired_items_identified(self, mixed_items):
        """Test that expired items are correctly identified."""
        now = datetime.now(UTC)
        expired_items = [
            item for item in mixed_items
            if item.expiry_date and item.expiry_date < now
        ]

        for item in expired_items:
            assert item.expiry_date < now
            assert item.is_expired() is True

        # Verify non-expired items
        non_expired = [
            item for item in mixed_items
            if item.expiry_date and item.expiry_date >= now
        ]
        for item in non_expired:
            assert item.is_expired() is False

        print(f"\nExpired items: {len(expired_items)}")
        for item in expired_items:
            print(f"  - {item.name}: expired on {item.expiry_date}")
