"""Tests for automatic recipe cooking pantry deduction service with FEFO."""

from datetime import UTC, datetime, timedelta

import pytest
from mongomock_motor import AsyncMongoMockClient

from backend.db import COLLECTION_ITEMS
from backend.models.inventory import Location, Unit
from backend.models.recipe import IngredientItem, Recipe
from backend.services.cooking_deduction import CookingDeductionService


@pytest.fixture
def mock_db():
    """Create an isolated in-memory mock database for testing deduction logic."""
    return AsyncMongoMockClient()["idunn_test_deduction"]


@pytest.mark.asyncio
async def test_deduct_exact_matching_unit(mock_db) -> None:
    """Verify deducting 200g paneer from 500g paneer reduces stock to 300g."""
    now = datetime.now(UTC)
    item_res = await mock_db[COLLECTION_ITEMS].insert_one(
        {
            "name": "Fresh Paneer",
            "quantity": 500.0,
            "unit": Unit.GRAM.value,
            "location": Location.FRIDGE.value,
            "expiry_date": now + timedelta(days=4),
            "consumed": False,
            "added_at": now,
            "updated_at": now,
        }
    )

    recipe = Recipe(
        _id="rec_paneer_bhurji",
        title="Paneer Bhurji",
        ingredients=[IngredientItem(name="paneer", quantity=200.0, unit="g")],
        steps=[],
    )

    service = CookingDeductionService(mock_db)
    report = await service.deduct_recipe_ingredients(recipe)

    assert report.fully_satisfied is True
    assert len(report.shortages) == 0
    assert len(report.deductions) == 1

    deduction = report.deductions[0]
    assert deduction.item_id == str(item_res.inserted_id)
    assert deduction.deducted_quantity == 200.0
    assert deduction.remaining_quantity == 300.0
    assert deduction.depleted is False

    updated_db_item = await mock_db[COLLECTION_ITEMS].find_one({"_id": item_res.inserted_id})
    assert updated_db_item["quantity"] == 300.0
    assert updated_db_item["consumed"] is False


@pytest.mark.asyncio
async def test_deduct_with_unit_conversion(mock_db) -> None:
    """Verify 1 katori toor dal (= 150g) deducts 0.15kg from 1.0kg bag in pantry."""
    now = datetime.now(UTC)
    item_res = await mock_db[COLLECTION_ITEMS].insert_one(
        {
            "name": "Toor Dal",
            "quantity": 1.0,
            "unit": Unit.KILOGRAM.value,
            "location": Location.PANTRY.value,
            "expiry_date": now + timedelta(days=90),
            "consumed": False,
            "added_at": now,
            "updated_at": now,
        }
    )

    recipe = Recipe(
        _id="rec_dal_fry",
        title="Dal Tadka",
        ingredients=[IngredientItem(name="toor dal", quantity=1.0, unit="katori")],
        steps=[],
    )

    service = CookingDeductionService(mock_db)
    report = await service.deduct_recipe_ingredients(recipe)

    assert report.fully_satisfied is True
    assert len(report.deductions) == 1

    deduction = report.deductions[0]
    assert deduction.item_id == str(item_res.inserted_id)
    # 1 katori = 150ml = 150g = 0.15kg
    assert pytest.approx(deduction.deducted_quantity, 0.001) == 0.15
    assert pytest.approx(deduction.remaining_quantity, 0.001) == 0.85


@pytest.mark.asyncio
async def test_deduct_fefo_order(mock_db) -> None:
    """Verify batch expiring sooner is depleted before batch expiring later."""
    now = datetime.now(UTC)
    # Batch A expires in 2 days (100g)
    batch_a = await mock_db[COLLECTION_ITEMS].insert_one(
        {
            "name": "Curd",
            "quantity": 100.0,
            "unit": Unit.GRAM.value,
            "location": Location.FRIDGE.value,
            "expiry_date": now + timedelta(days=2),
            "consumed": False,
            "added_at": now,
            "updated_at": now,
        }
    )
    # Batch B expires in 6 days (200g)
    batch_b = await mock_db[COLLECTION_ITEMS].insert_one(
        {
            "name": "Curd",
            "quantity": 200.0,
            "unit": Unit.GRAM.value,
            "location": Location.FRIDGE.value,
            "expiry_date": now + timedelta(days=6),
            "consumed": False,
            "added_at": now,
            "updated_at": now,
        }
    )

    recipe = Recipe(
        _id="rec_raita",
        title="Boondi Raita",
        ingredients=[IngredientItem(name="curd", quantity=150.0, unit="g")],
        steps=[],
    )

    service = CookingDeductionService(mock_db)
    report = await service.deduct_recipe_ingredients(recipe)

    assert report.fully_satisfied is True
    assert len(report.deductions) == 2

    # Batch A should be fully depleted (100g)
    ded_a = report.deductions[0]
    assert ded_a.item_id == str(batch_a.inserted_id)
    assert ded_a.deducted_quantity == 100.0
    assert ded_a.remaining_quantity == 0.0
    assert ded_a.depleted is True

    # Batch B should have 50g deducted, leaving 150g
    ded_b = report.deductions[1]
    assert ded_b.item_id == str(batch_b.inserted_id)
    assert ded_b.deducted_quantity == 50.0
    assert ded_b.remaining_quantity == 150.0
    assert ded_b.depleted is False

    # Check DB state
    db_a = await mock_db[COLLECTION_ITEMS].find_one({"_id": batch_a.inserted_id})
    assert db_a["quantity"] == 0.0
    assert db_a["consumed"] is True

    db_b = await mock_db[COLLECTION_ITEMS].find_one({"_id": batch_b.inserted_id})
    assert db_b["quantity"] == 150.0
    assert db_b["consumed"] is False


@pytest.mark.asyncio
async def test_depletion_marks_consumed_true(mock_db) -> None:
    """Verify that an item whose quantity reaches zero is marked consumed=True."""
    now = datetime.now(UTC)
    item_res = await mock_db[COLLECTION_ITEMS].insert_one(
        {
            "name": "Eggs",
            "quantity": 2.0,
            "unit": Unit.PIECE.value,
            "location": Location.FRIDGE.value,
            "expiry_date": now + timedelta(days=5),
            "consumed": False,
            "added_at": now,
            "updated_at": now,
        }
    )

    recipe = Recipe(
        _id="rec_omelette",
        title="Masala Omelette",
        ingredients=[IngredientItem(name="egg", quantity=2.0, unit="piece")],
        steps=[],
    )

    service = CookingDeductionService(mock_db)
    report = await service.deduct_recipe_ingredients(recipe)

    assert report.fully_satisfied is True
    assert report.deductions[0].depleted is True
    assert report.deductions[0].remaining_quantity == 0.0

    db_item = await mock_db[COLLECTION_ITEMS].find_one({"_id": item_res.inserted_id})
    assert db_item["quantity"] == 0.0
    assert db_item["consumed"] is True


@pytest.mark.asyncio
async def test_partial_shortage_records_deficit(mock_db) -> None:
    """Verify that when pantry has only 100g but recipe needs 250g, 100g is deducted and deficit is reported."""
    now = datetime.now(UTC)
    item_res = await mock_db[COLLECTION_ITEMS].insert_one(
        {
            "name": "Besan",
            "quantity": 100.0,
            "unit": Unit.GRAM.value,
            "location": Location.PANTRY.value,
            "expiry_date": now + timedelta(days=30),
            "consumed": False,
            "added_at": now,
            "updated_at": now,
        }
    )

    recipe = Recipe(
        _id="rec_dhokla",
        title="Khaman Dhokla",
        ingredients=[IngredientItem(name="besan", quantity=250.0, unit="g")],
        steps=[],
    )

    service = CookingDeductionService(mock_db)
    report = await service.deduct_recipe_ingredients(recipe)

    assert report.fully_satisfied is False
    assert len(report.shortages) == 1
    shortage = report.shortages[0]
    assert shortage.ingredient_name == "besan"
    assert shortage.required_quantity == 250.0
    assert shortage.available_quantity == 100.0
    assert shortage.missing_quantity == 150.0

    assert len(report.deductions) == 1
    assert report.deductions[0].depleted is True

    db_item = await mock_db[COLLECTION_ITEMS].find_one({"_id": item_res.inserted_id})
    assert db_item["quantity"] == 0.0
    assert db_item["consumed"] is True
