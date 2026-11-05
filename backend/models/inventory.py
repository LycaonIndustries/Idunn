"""Inventory models for Iðunn - Indian kitchen inventory tracking.

Supports FEFO (First Expire First Out) ordering, Indian units
(chamcha, katori, paav, etc.), and location tracking.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


# Use string enum to capture discrete household storage zones.
class Location(StrEnum):
    """Storage locations in an Indian household kitchen."""

    FRIDGE = "fridge"
    FREEZER = "freezer"
    PANTRY = "pantry"
    DRY_STORE = "dry_store"
    CABINET = "cabinet"
    COUNTER = "counter"
    SPICE_BOX = "spice_box"
    WINDOWSILL = "windowsill"


# Support traditional Indian volumetric measures alongside metric units.
class Unit(StrEnum):
    """Units of measurement with Indian-specific units.

    Categories:
    - Mass: g, kg, paav (250g traditional)
    - Volume: ml, l, tsp, tbsp, chamcha (Indian tsp), katori (cup ~150ml)
    - Count: piece, bunch, packet, box
    """

    # Mass
    GRAM = "g"
    KILOGRAM = "kg"
    PAAV = "paav"  # ~250g traditional Indian measure

    # Volume
    MILLILITER = "ml"
    LITER = "l"
    TEASPOON = "tsp"
    TABLESPOON = "tbsp"
    CHAMCHA = "chamcha"  # Indian teaspoon
    KATORI = "katori"  # ~150ml cup

    # Count
    PIECE = "piece"
    BUNCH = "bunch"
    PACKET = "packet"
    BOX = "box"


# Classify units to validate that conversion between incompatible dimensions is blocked.
class UnitCategory(StrEnum):
    """Category of unit for conversion graph."""

    MASS = "mass"
    VOLUME = "volume"
    COUNT = "count"


# Graph maps unit pairs to multiplication factors for automatic recipe deduction.
UNIT_CONVERSIONS: dict[tuple[Unit, Unit], float] = {
    # Mass
    (Unit.GRAM, Unit.KILOGRAM): 0.001,
    (Unit.KILOGRAM, Unit.GRAM): 1000.0,
    (Unit.PAAV, Unit.GRAM): 250.0,
    (Unit.GRAM, Unit.PAAV): 1.0 / 250.0,
    (Unit.PAAV, Unit.KILOGRAM): 0.25,
    (Unit.KILOGRAM, Unit.PAAV): 4.0,
    # Volume
    (Unit.MILLILITER, Unit.LITER): 0.001,
    (Unit.LITER, Unit.MILLILITER): 1000.0,
    (Unit.TEASPOON, Unit.MILLILITER): 5.0,
    (Unit.MILLILITER, Unit.TEASPOON): 1.0 / 5.0,
    (Unit.TABLESPOON, Unit.MILLILITER): 15.0,
    (Unit.MILLILITER, Unit.TABLESPOON): 1.0 / 15.0,
    (Unit.CHAMCHA, Unit.MILLILITER): 5.0,
    (Unit.MILLILITER, Unit.CHAMCHA): 1.0 / 5.0,
    (Unit.KATORI, Unit.MILLILITER): 150.0,
    (Unit.MILLILITER, Unit.KATORI): 1.0 / 150.0,
    # Cross-volume
    (Unit.TABLESPOON, Unit.TEASPOON): 3.0,
    (Unit.TEASPOON, Unit.TABLESPOON): 1.0 / 3.0,
    (Unit.CHAMCHA, Unit.TEASPOON): 1.0,  # chamcha matches standard teaspoon
    (Unit.KATORI, Unit.TABLESPOON): 10.0,  # 150ml / 15ml
    # Mass-Volume water equivalence (approximate for water-dense liquid groceries)
    (Unit.GRAM, Unit.MILLILITER): 1.0,
    (Unit.MILLILITER, Unit.GRAM): 1.0,
    (Unit.KILOGRAM, Unit.LITER): 1.0,
    (Unit.LITER, Unit.KILOGRAM): 1.0,
}


# Model explicit conversion factors for custom or regional overrides.
class UnitConversion(BaseModel):
    """Unit conversion with factor and optional region tag."""

    model_config = ConfigDict(frozen=True)

    from_unit: Unit
    to_unit: Unit
    factor: float
    region: str | None = None  # e.g., "north_india", "south_india"


# Base schema defines common inventory tracking fields.
class ItemBase(BaseModel):
    """Base item fields."""

    model_config = ConfigDict(use_attribute_docstrings=True)

    name: str = Field(..., min_length=1, max_length=200, description="Item name")
    quantity: float = Field(..., gt=0, description="Quantity")
    unit: Unit = Field(..., description="Unit of measurement")
    location: Location = Field(..., description="Storage location")
    expiry_date: datetime | None = Field(None, description="Expiry date (for FEFO ordering)")
    notes: str | None = Field(None, max_length=500, description="Optional notes")
    barcode: str | None = Field(None, max_length=50, description="Barcode for quick add")
    owner_id: str = Field(
        default="dev_user_local",
        description="Owner user identifier for tenant isolation",
    )


# New item creation records current UTC time.
class ItemCreate(ItemBase):
    """Item creation payload."""

    added_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


# Update schema permits partial modification of item quantities and dates.
class ItemUpdate(BaseModel):
    """Item update payload - all fields optional."""

    name: str | None = Field(None, min_length=1, max_length=200)
    quantity: float | None = Field(None, gt=0)
    unit: Unit | None = None
    location: Location | None = None
    expiry_date: datetime | None = None
    notes: str | None = Field(None, max_length=500)
    barcode: str | None = Field(None, max_length=50)


# Persistent database item with consumed flag and lifecycle methods.
class Item(ItemBase):
    """Item document as stored in database."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., alias="_id")
    quantity: float = Field(..., ge=0, description="Remaining quantity")
    added_at: datetime
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    consumed: bool = Field(False, description="Marked as consumed/discarded")

    @model_validator(mode="after")
    def zero_requires_consumed(self) -> Item:
        """Enforce that items with zero quantity are flagged as consumed.

        Returns:
            Validated Item instance.

        Raises:
            ValueError: If quantity is zero but item is not marked consumed.
        """
        # Ensure zero-quantity rows do not appear as active stock in the pantry.
        if self.quantity == 0 and not self.consumed:
            raise ValueError("An item with zero quantity must be marked consumed")
        return self

    def is_expiring_soon(self, days: int = 3) -> bool:
        """Check if item expires within given threshold days.

        Args:
            days: Days ahead to test against expiry timestamp.

        Returns:
            True if item has an expiry date within the target window, otherwise False.
        """
        # Undated pantry staples like dry pulses do not expire within fixed windows.
        if not self.expiry_date:
            return False
        return self.expiry_date <= datetime.now(UTC) + timedelta(days=days)

    def is_expired(self) -> bool:
        """Check if item timestamp has passed current UTC time.

        Returns:
            True if item expiry date is in the past, otherwise False.
        """
        if not self.expiry_date:
            return False
        return self.expiry_date < datetime.now(UTC)

    def convert_quantity(self, target_unit: Unit) -> float | None:
        """Convert quantity to target unit if conversion factor is defined.

        Args:
            target_unit: Unit dimension to convert quantity towards.

        Returns:
            Converted quantity float, or None if no valid conversion path exists.
        """
        # Lookup precomputed multipliers to perform rapid unit translation.
        conversion = UNIT_CONVERSIONS.get((self.unit, target_unit))
        if conversion is not None:
            return self.quantity * conversion
        return None
