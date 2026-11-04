"""Tests for receipt data models and shelf-life estimation."""

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from backend.models.inventory import Unit
from backend.models.receipt import (
    Receipt,
    ReceiptConfirmRequest,
    ReceiptItemCandidate,
    estimate_shelf_life,
)


class TestShelfLifeEstimation:
    """Test standard Indian kitchen shelf-life heuristics."""

    def test_dairy_shelf_life(self):
        """Milk and paneer should have short perishability (3-4 days)."""
        days = estimate_shelf_life("Amul Taaza Milk", "dairy")
        assert days <= 4
        assert days >= 2

    def test_leafy_greens_shelf_life(self):
        """Palak and coriander spoil rapidly (3 days)."""
        days = estimate_shelf_life("Fresh Palak (Spinach)", "vegetable")
        assert days == 3

    def test_root_vegetables_shelf_life(self):
        """Onions and potatoes store for weeks (21 days)."""
        days = estimate_shelf_life("Red Onions", "vegetable")
        assert days >= 14

    def test_staples_and_pulses_shelf_life(self):
        """Dal and rice store for months (180 days)."""
        days = estimate_shelf_life("Toor Dal", "pulse")
        assert days >= 90

    def test_spices_shelf_life(self):
        """Spices store for up to a year."""
        days = estimate_shelf_life("Turmeric Powder", "spice")
        assert days >= 180


class TestReceiptModels:
    """Test candidate extraction and confirmation models."""

    def test_candidate_valid(self):
        """Valid candidate with computed expiry date."""
        item = ReceiptItemCandidate(
            raw_text="Amul Malai Paneer 200g",
            name="Paneer",
            quantity=200.0,
            unit=Unit.GRAM,
            category="dairy",
            estimated_shelf_life_days=4,
            suggested_location="fridge",
        )
        assert item.name == "Paneer"
        assert item.quantity == 200.0
        assert item.unit == Unit.GRAM
        assert item.estimated_shelf_life_days == 4
        # Calculate expiry from reference date
        ref_date = datetime(2026, 11, 4, 12, 0, tzinfo=UTC)
        expiry = item.calculate_expiry_date(ref_date)
        assert expiry == ref_date + timedelta(days=4)

    def test_candidate_rejects_negative_or_zero_quantity(self):
        """Zero or negative quantity must raise validation error."""
        with pytest.raises(ValidationError):
            ReceiptItemCandidate(
                raw_text="Item",
                name="Item",
                quantity=0.0,
                unit=Unit.PIECE,
                category="other",
                estimated_shelf_life_days=7,
                suggested_location="pantry",
            )

    def test_confirm_request_validation(self):
        """Confirmation payload requires at least one item."""
        candidate = ReceiptItemCandidate(
            raw_text="Zepto Curd 400g",
            name="Curd",
            quantity=400.0,
            unit=Unit.GRAM,
            category="dairy",
            estimated_shelf_life_days=5,
            suggested_location="fridge",
        )
        req = ReceiptConfirmRequest(
            receipt_id="rcpt_123",
            items=[candidate],
            store_name="Zepto",
        )
        assert req.receipt_id == "rcpt_123"
        assert len(req.items) == 1

    def test_receipt_document_schema(self):
        """Receipt persistence schema with raw metadata and confidence."""
        now = datetime.now(UTC)
        receipt = Receipt(
            _id="rcpt_999",
            store_name="Blinkit",
            purchase_date=now,
            items=[
                ReceiptItemCandidate(
                    raw_text="Blinkit Fresh Coriander 1 bunch",
                    name="Coriander",
                    quantity=1.0,
                    unit=Unit.BUNCH,
                    category="vegetable",
                    estimated_shelf_life_days=3,
                    suggested_location="fridge",
                )
            ],
            confidence=0.92,
            raw_image_url="data:image/jpeg;base64,...",
        )
        assert receipt.id == "rcpt_999"
        assert receipt.store_name == "Blinkit"
        assert receipt.confidence == 0.92
