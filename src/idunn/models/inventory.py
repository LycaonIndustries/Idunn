"""Inventory models for Iðunn - Indian kitchen inventory tracking.

Supports FEFO (First Expire First Out) ordering, Indian units
(chamcha, katori, paav, etc.), and location tracking.
"""

from __future__ import annotations

from datetime import datetime, timedelta, UTC
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict, model_validator


class Location(str, Enum):
    """Storage locations in an Indian household kitchen."""

    FRIDGE = "fridge"
    FREEZER = "freezer"
    PANTRY = "pantry"
    DRY_STORE = "dry_store"
    CABINET = "cabinet"
    COUNTER = "counter"
    SPICE_BOX = "spice_box"
    WINDOWSILL = "windowsill"


class Unit(str, Enum):
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


class UnitCategory(str, Enum):
    """Category of unit for conversion graph."""

    MASS = "mass"
    VOLUME = "volume"
    COUNT = "count"


# Conversion graph: (from_unit, to_unit) -> multiplier
# chamcha ≈ tsp ≈ 5ml; katori ≈ 150ml ≈ 2/3 cup
UNIT_CONVERSIONS: dict[tuple[Unit, Unit], float] = {
    # Mass
    (Unit.GRAM, Unit.KILOGRAM): 0.001,
    (Unit.KILOGRAM, Unit.GRAM): 1000,
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
    # Cross-volume (approximate)
    (Unit.TABLESPOON, Unit.TEASPOON): 3.0,
    (Unit.TEASPOON, Unit.TABLESPOON): 1.0 / 3.0,
    (Unit.CHAMCHA, Unit.TEASPOON): 1.0,  # chamcha ≈ tsp
    (Unit.KATORI, Unit.TABLESPOON): 10.0,  # 150ml / 15ml
    # Mass-Volume water equivalence (approximate, for water-like substances)
    (Unit.GRAM, Unit.MILLILITER): 1.0,
    (Unit.MILLILITER, Unit.GRAM): 1.0,
    (Unit.KILOGRAM, Unit.LITER): 1.0,
    (Unit.LITER, Unit.KILOGRAM): 1.0,
}


class UnitConversion(BaseModel):
    """Unit conversion with factor and optional region tag."""

    model_config = ConfigDict(frozen=True)

    from_unit: Unit
    to_unit: Unit
    factor: float
    region: Optional[str] = None  # e.g., "north_india", "south_india"


class ItemBase(BaseModel):
    """Base item fields."""

    model_config = ConfigDict(use_attribute_docstrings=True)

    name: str = Field(..., min_length=1, max_length=200, description="Item name")
    quantity: float = Field(..., gt=0, description="Quantity")
    unit: Unit = Field(..., description="Unit of measurement")
    location: Location = Field(..., description="Storage location")
    expiry_date: Optional[datetime] = Field(
        None, description="Expiry date (for FEFO ordering)"
    )
    notes: Optional[str] = Field(None, max_length=500, description="Optional notes")
    barcode: Optional[str] = Field(
        None, max_length=50, description="Barcode for quick add"
    )


class ItemCreate(ItemBase):
    """Item creation payload."""

    added_at: datetime = Field(default_factory=datetime.utcnow)


class ItemUpdate(BaseModel):
    """Item update payload - all fields optional."""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    quantity: Optional[float] = Field(None, gt=0)
    unit: Optional[Unit] = None
    location: Optional[Location] = None
    expiry_date: Optional[datetime] = None
    notes: Optional[str] = Field(None, max_length=500)
    barcode: Optional[str] = Field(None, max_length=50)


class Item(ItemBase):
    """Item document as stored in MongoDB."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., alias="_id")
    quantity: float = Field(..., ge=0, description="Remaining quantity")
    added_at: datetime
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    consumed: bool = Field(False, description="Marked as consumed/discarded")

    @model_validator(mode="after")
    def zero_requires_consumed(self) -> Item:
        if self.quantity == 0 and not self.consumed:
            raise ValueError("An item with zero quantity must be marked consumed")
        return self

    def is_expiring_soon(self, days: int = 3) -> bool:
        """Check if item expires within given days."""
        if not self.expiry_date:
            return False
        return self.expiry_date <= datetime.now(UTC) + timedelta(days=days)

    def is_expired(self) -> bool:
        """Check if item is past expiry."""
        if not self.expiry_date:
            return False
        return self.expiry_date < datetime.now(UTC)

    def convert_quantity(self, target_unit: Unit) -> Optional[float]:
        """Convert quantity to target unit if conversion exists."""
        conversion = UNIT_CONVERSIONS.get((self.unit, target_unit))
        if conversion is not None:
            return self.quantity * conversion
        return None
