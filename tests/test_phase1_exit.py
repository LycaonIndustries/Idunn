"""Phase 1 exit criteria, exercised through the real FastAPI app.

Every test creates its data with the API and reads it back with the API, using
the isolated in-memory database from ``conftest.api_client``.

Criteria covered:
1. Add 50 mixed items (mass + volume + count).
2. Expiry dates relative to one captured ``now``: expired, within 7 days,
   after 7 days, no expiry, and one consumed item.
3. "Expiring this week" returns exactly the right items, in order.
4. FEFO ordering: earlier expiry first, no-expiry items last.
5. Unit conversions for the stored mixed units.
6. Items by location and expired-item detection.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from backend.models.inventory import (
    Item,
    Location,
    Unit,
)

MASS_UNITS = {Unit.GRAM, Unit.KILOGRAM, Unit.PAAV}
VOLUME_UNITS = {
    Unit.MILLILITER,
    Unit.LITER,
    Unit.TEASPOON,
    Unit.TABLESPOON,
    Unit.CHAMCHA,
    Unit.KATORI,
}
COUNT_UNITS = {Unit.PIECE, Unit.BUNCH, Unit.PACKET, Unit.BOX}


def _as_utc(value: datetime) -> datetime:
    """Attach UTC to the naive datetimes the database returns."""
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _parse_expiry(doc: dict) -> datetime | None:
    raw = doc.get("expiry_date")
    if raw is None:
        return None
    return _as_utc(datetime.fromisoformat(raw))


def _create(api_client, payload: dict) -> dict:
    response = api_client.post("/api/v1/items", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def _list_items(api_client) -> list[dict]:
    response = api_client.get("/api/v1/items")
    assert response.status_code == 200, response.text
    return response.json()


EXPIRED_OFFSETS = list(range(-15, 0))
WITHIN_WEEK_OFFSETS = [
    0.5,
    0.75,
    1.0,
    1.25,
    1.5,
    2.0,
    2.5,
    3.0,
    3.5,
    4.0,
    4.5,
    5.0,
    5.5,
    6.0,
    6.5,
]
LATER_OFFSETS = list(range(8, 23))
CONSUMED_ROW_INDEX = 25


@pytest.fixture
def mixed_inventory(api_client) -> dict:
    """50 items added through the API, carrying the full expiry variety.

    Returns the captured ``now`` plus one entry per created item, holding the
    final document, the intended expiry offset in days (``None`` for no
    expiry), the unit, the location, and whether the item was fully consumed.
    """
    now = datetime.now(UTC)

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
        ("Tamarind Paste", 1.0, Unit.KATORI, Location.SPICE_BOX),
        ("Ginger-Garlic Paste", 1.0, Unit.KATORI, Location.SPICE_BOX),
        ("Buttermilk", 200.0, Unit.MILLILITER, Location.FRIDGE),
        ("Yogurt", 1.0, Unit.KATORI, Location.FRIDGE),
    ]
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
    rows = mass_items + volume_items + count_items

    offsets = EXPIRED_OFFSETS + WITHIN_WEEK_OFFSETS + LATER_OFFSETS + [None] * 5
    assert len(rows) == 50
    assert len(offsets) == 50
    assert 0 < offsets[CONSUMED_ROW_INDEX] < 7

    created = []
    for index, ((name, quantity, unit, location), offset) in enumerate(
        zip(rows, offsets, strict=False)
    ):
        payload = {
            "name": name,
            "quantity": quantity,
            "unit": unit.value,
            "location": location.value,
        }
        if offset is not None:
            payload["expiry_date"] = (now + timedelta(days=offset)).isoformat()

        doc = _create(api_client, payload)
        consumed = index == CONSUMED_ROW_INDEX
        if consumed:
            response = api_client.post(
                f"/api/v1/items/{doc['_id']}/consume",
                params={"quantity": quantity},
            )
            assert response.status_code == 200, response.text
            doc = response.json()
            assert doc["consumed"] is True
            assert doc["quantity"] == 0

        created.append(
            {
                "doc": doc,
                "offset": offset,
                "unit": unit,
                "location": location,
                "consumed": consumed,
            }
        )

    return {"now": now, "items": created}


class TestPhase1ExitCriteria:
    def test_add_50_mixed_items(self, api_client, mixed_inventory):
        """50 mixed items are stored, with one consumed and the rest listed."""
        items = mixed_inventory["items"]
        assert len(items) == 50
        assert all(entry["doc"]["_id"] for entry in items)

        consumed = [entry for entry in items if entry["doc"]["consumed"]]
        not_consumed = [entry for entry in items if not entry["doc"]["consumed"]]
        assert len(consumed) == 1
        assert len(not_consumed) == 49
        assert all(entry["doc"]["consumed"] is entry["consumed"] for entry in items)

        units = [Unit(entry["doc"]["unit"]) for entry in items]
        mass_count = sum(1 for unit in units if unit in MASS_UNITS)
        volume_count = sum(1 for unit in units if unit in VOLUME_UNITS)
        count_count = sum(1 for unit in units if unit in COUNT_UNITS)

        assert (mass_count, volume_count, count_count) == (20, 15, 15)
        assert mass_count >= 15
        assert volume_count >= 10
        assert count_count >= 10
        assert mass_count + volume_count + count_count == 50

        listed = _list_items(api_client)
        assert len(listed) == 49
        assert {doc["_id"] for doc in listed} == {entry["doc"]["_id"] for entry in not_consumed}

    def test_expiring_this_week_query(self, api_client, mixed_inventory):
        now = mixed_inventory["now"]
        items = mixed_inventory["items"]

        expected = sorted(
            (entry["offset"], entry["doc"]["_id"])
            for entry in items
            if entry["offset"] is not None and not entry["consumed"] and 0 < entry["offset"] <= 7
        )
        expected_ids = [item_id for _, item_id in expected]
        assert len(expected_ids) == 14

        response = api_client.get("/api/v1/items/expiring", params={"days": 7})
        assert response.status_code == 200, response.text
        returned = response.json()

        returned_ids = [doc["_id"] for doc in returned]
        assert returned_ids == expected_ids

        window_end = now + timedelta(days=7)
        for doc in returned:
            assert doc["consumed"] is False
            expiry = _parse_expiry(doc)
            assert expiry is not None
            assert now <= expiry <= window_end

        consumed_id = next(entry["doc"]["_id"] for entry in items if entry["consumed"])
        assert consumed_id not in {doc["_id"] for doc in returned}

    def test_fefo_ordering(self, api_client, mixed_inventory):
        items = mixed_inventory["items"]
        expected_ids = {entry["doc"]["_id"] for entry in items if not entry["consumed"]}

        returned = _list_items(api_client)
        assert len(returned) == 49
        assert {doc["_id"] for doc in returned} == expected_ids

        expiries = [_parse_expiry(doc) for doc in returned]
        assert all(expiry is not None for expiry in expiries[:-5])
        assert expiries[-5:] == [None] * 5

        with_expiry = expiries[:-5]
        assert with_expiry == sorted(with_expiry)

    def test_unit_conversions_for_mixed_items(self, api_client, mixed_inventory):
        docs = _list_items(api_client)
        items = [Item.model_validate(doc) for doc in docs]

        by_unit: dict[Unit, list[Item]] = {}
        for item in items:
            by_unit.setdefault(item.unit, []).append(item)

        def items_in(unit: Unit) -> list[Item]:
            matching = by_unit.get(unit, [])
            assert matching, f"no stored item with unit {unit.value}"
            return matching

        for item in items_in(Unit.GRAM):
            assert item.convert_quantity(Unit.KILOGRAM) == pytest.approx(
                item.quantity / 1000, rel=1e-9, abs=1e-12
            )

        for item in items_in(Unit.KILOGRAM):
            assert item.convert_quantity(Unit.GRAM) == pytest.approx(
                item.quantity * 1000, rel=1e-9, abs=1e-12
            )

        for item in items_in(Unit.MILLILITER):
            assert item.convert_quantity(Unit.LITER) == pytest.approx(
                item.quantity / 1000, rel=1e-9, abs=1e-12
            )

        for item in items_in(Unit.LITER):
            assert item.convert_quantity(Unit.MILLILITER) == pytest.approx(
                item.quantity * 1000, rel=1e-9, abs=1e-12
            )

        for item in items_in(Unit.PAAV):
            assert item.convert_quantity(Unit.GRAM) == pytest.approx(
                item.quantity * 250, rel=1e-9, abs=1e-12
            )

        for item in items_in(Unit.CHAMCHA):
            assert item.convert_quantity(Unit.MILLILITER) == pytest.approx(
                item.quantity * 5, rel=1e-9, abs=1e-12
            )

        for item in items_in(Unit.KATORI):
            assert item.convert_quantity(Unit.MILLILITER) == pytest.approx(
                item.quantity * 150, rel=1e-9, abs=1e-12
            )
            assert item.convert_quantity(Unit.TABLESPOON) == pytest.approx(
                item.quantity * 10, rel=1e-9, abs=1e-12
            )

        for item in items_in(Unit.TEASPOON):
            assert item.convert_quantity(Unit.TABLESPOON) == pytest.approx(
                item.quantity / 3, rel=1e-9, abs=1e-12
            )

        count_items = [item for item in items if item.unit in COUNT_UNITS]
        assert count_items, "no stored count item"
        for item in count_items:
            assert item.convert_quantity(Unit.GRAM) is None

    def test_items_by_location(self, api_client, mixed_inventory):
        items = mixed_inventory["items"]
        returned = _list_items(api_client)

        returned_locations = {doc["location"] for doc in returned}
        expected_locations = {entry["location"].value for entry in items if not entry["consumed"]}
        assert returned_locations == expected_locations
        assert len(returned_locations) > 1

        for location in returned_locations:
            expected_ids = {
                entry["doc"]["_id"]
                for entry in items
                if entry["location"].value == location and not entry["consumed"]
            }
            response = api_client.get("/api/v1/items", params={"location": location})
            assert response.status_code == 200, response.text
            filtered = response.json()
            assert all(doc["location"] == location for doc in filtered)
            assert {doc["_id"] for doc in filtered} == expected_ids

    def test_expired_items_identified(self, api_client, mixed_inventory):
        now = mixed_inventory["now"]
        items = mixed_inventory["items"]
        expected_expired_ids = {
            entry["doc"]["_id"]
            for entry in items
            if entry["offset"] is not None and entry["offset"] < 0 and not entry["consumed"]
        }
        expected_not_expired_ids = {
            entry["doc"]["_id"]
            for entry in items
            if entry["offset"] is not None and entry["offset"] >= 0 and not entry["consumed"]
        }

        returned = _list_items(api_client)
        expired_ids = set()
        not_expired_ids = set()
        for doc in returned:
            expiry = _parse_expiry(doc)
            if expiry is None:
                continue
            if expiry < now:
                expired_ids.add(doc["_id"])
            else:
                not_expired_ids.add(doc["_id"])

        assert expired_ids == expected_expired_ids
        assert not_expired_ids == expected_not_expired_ids
        assert len(expired_ids) == 15
        assert len(not_expired_ids) == 29
        assert not (expired_ids & not_expired_ids)
