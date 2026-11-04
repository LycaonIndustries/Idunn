"""Receipt models and shelf-life estimation heuristics for Iðunn.

Transforms raw purchase line items into actionable pantry records with
intelligent FEFO (First Expire First Out) shelf-life projections.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .inventory import Unit

# Default storage duration in days based on Indian food classification.
CATEGORY_SHELF_LIFE_DAYS: dict[str, int] = {
    "dairy": 4,
    "herb": 3,
    "vegetable": 7,
    "fruit": 5,
    "pulse": 180,
    "cereal": 180,
    "flour": 120,
    "spice": 365,
    "oil": 180,
    "condiment": 90,
    "sweetener": 365,
    "nut": 180,
    "seed": 180,
    "readymade": 60,
    "other": 14,
}

# Override shelf life for specific high-perishability or long-storing produce.
ITEM_SHELF_LIFE_OVERRIDES: dict[str, int] = {
    # Leafy greens spoil within 2-3 days
    "spinach": 3,
    "palak": 3,
    "coriander": 3,
    "dhania": 3,
    "methi": 3,
    "curry leaves": 5,
    "kadi patta": 5,
    # High-moisture dairy
    "milk": 3,
    "doodh": 3,
    "paneer": 4,
    "curd": 5,
    "dahi": 5,
    # Alliums and tubers store well in cool dry pantries
    "onion": 21,
    "pyaz": 21,
    "potato": 28,
    "aloo": 28,
    "garlic": 30,
    "lehsun": 30,
    "ginger": 21,
    "adrak": 21,
    # Common vegetables
    "tomato": 7,
    "tamatar": 7,
    "cucumber": 6,
    "kheera": 6,
    "capsicum": 7,
    "shimla mirch": 7,
    "cauliflower": 7,
    "gobhi": 7,
}


def estimate_shelf_life(name: str, category: str = "other") -> int:
    """Estimate pantry shelf-life in days based on item name and category.

    Args:
        name: Name of food or grocery item.
        category: Broad ingredient category.

    Returns:
        Estimated shelf life duration in days.
    """
    # Lowercase text to ensure matching is case insensitive.
    name_clean = name.strip().lower()

    # Check keyword overrides for specific items.
    for keyword, days in ITEM_SHELF_LIFE_OVERRIDES.items():
        if keyword in name_clean:
            return days

    # Fall back to category-level default shelf life.
    cat_clean = category.strip().lower()
    return CATEGORY_SHELF_LIFE_DAYS.get(cat_clean, 7)


def estimate_storage_location(category: str, name: str) -> str:
    """Recommend kitchen storage zone based on item perishability.

    Args:
        category: Broad food category.
        name: Food item name.

    Returns:
        Storage zone identifier (fridge, pantry, spice_box, or counter).
    """
    name_clean = name.strip().lower()
    cat_clean = category.strip().lower()

    if cat_clean in {"dairy", "herb"}:
        return "fridge"
    if any(k in name_clean for k in ("milk", "paneer", "curd", "palak", "coriander")):
        return "fridge"
    if cat_clean == "spice":
        return "spice_box"
    if cat_clean in {"pulse", "cereal", "flour", "oil", "sweetener"}:
        return "pantry"
    if any(k in name_clean for k in ("onion", "potato", "garlic")):
        return "pantry"

    return "fridge"


class ReceiptItemCandidate(BaseModel):
    """Candidate grocery item extracted from bill or delivery screenshot."""

    model_config = ConfigDict(use_attribute_docstrings=True)

    raw_text: str = Field(..., min_length=1, max_length=300, description="Raw OCR line text")
    name: str = Field(..., min_length=1, max_length=200, description="Cleaned grocery name")
    quantity: float = Field(..., gt=0, description="Extracted numerical quantity")
    unit: Unit = Field(default=Unit.PIECE, description="Standardized measurement unit")
    category: str = Field(default="other", description="Food category")
    estimated_shelf_life_days: int = Field(
        ..., ge=1, description="Estimated storage shelf life in days"
    )
    suggested_location: str = Field(default="fridge", description="Suggested storage zone")
    price: float | None = Field(None, ge=0.0, description="Item purchase price in INR")

    def calculate_expiry_date(self, reference_date: datetime | None = None) -> datetime:
        """Compute projected expiration date from reference timestamp.

        Args:
            reference_date: Reference purchase or ingestion date (defaults to UTC now).

        Returns:
            Projected expiry timestamp.
        """
        # Default to current UTC time if no purchase date was provided.
        base = reference_date or datetime.now(UTC)
        return base + timedelta(days=self.estimated_shelf_life_days)


class ReceiptConfirmRequest(BaseModel):
    """Payload to confirm extracted receipt items and add them to pantry stock."""

    receipt_id: str = Field(..., description="Unique receipt document identifier")
    items: list[ReceiptItemCandidate] = Field(
        ..., min_length=1, description="Confirmed candidate items to add"
    )
    store_name: str | None = Field(None, max_length=100, description="Store or platform name")


class Receipt(BaseModel):
    """Stored receipt record documenting visual ingestion run."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., alias="_id")
    store_name: str = Field(..., description="Store or delivery app name")
    purchase_date: datetime = Field(default_factory=lambda: datetime.now(UTC))
    items: list[ReceiptItemCandidate] = Field(default_factory=list)
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Extraction confidence score")
    raw_image_url: str | None = Field(None, description="Image reference or data URI")
    confirmed: bool = Field(False, description="Whether items were confirmed into pantry")
    status: Literal["pending", "confirmed", "failed"] = "pending"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
