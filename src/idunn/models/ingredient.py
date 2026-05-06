"""Ingredient models for Iðunn - canonical ingredient master.

Supports ingredient normalization, synonym matching, regional names,
unit conversions, and IFCT (Indian Food Composition Tables) linkage.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class Region(str, Enum):
    """Indian regional cuisines for ingredient context."""

    NORTH = "north_india"
    SOUTH = "south_india"
    EAST = "east_india"
    WEST = "west_india"
    CENTRAL = "central_india"
    NORTHEAST = "northeast_india"
    PAN_INDIA = "pan_india"


class IngredientCategory(str, Enum):
    """Broad ingredient categories for Indian cooking."""

    CEREAL = "cereal"
    PULSE = "pulse"  # dal, legumes
    VEGETABLE = "vegetable"
    FRUIT = "fruit"
    SPICE = "spice"
    HERB = "herb"
    DAIRY = "dairy"
    OIL = "oil"
    FLOUR = "flour"
    SWEETENER = "sweetener"
    NUT = "nut"
    SEED = "seed"
    CONDIMENT = "condiment"
    READYMADE = "readymade"  # pasta, noodles, etc.


class Synonym(BaseModel):
    """Alternative name for an ingredient."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(..., min_length=1, max_length=100)
    region: Optional[Region] = None
    language: Optional[str] = Field(
        None, min_length=2, max_length=20, description="ISO 639-1 code or name"
    )


class IngredientBase(BaseModel):
    """Base ingredient fields."""

    model_config = ConfigDict(use_attribute_docstrings=True)

    name: str = Field(
        ..., min_length=1, max_length=100, description="Canonical ingredient name"
    )
    category: IngredientCategory = Field(..., description="Ingredient category")
    synonyms: list[Synonym] = Field(
        default_factory=list, description="Alternative names across regions/languages"
    )
    default_unit: Optional[str] = Field(
        None, max_length=20, description="Default unit for this ingredient"
    )
    ifct_id: Optional[str] = Field(
        None, max_length=50, description="IFCT (Indian Food Composition Tables) ID"
    )
    regions: list[Region] = Field(
        default_factory=list, description="Regions where this ingredient is commonly used"
    )
    nutrition_per_100g: Optional[dict] = Field(
        None, description="Nutrition data per 100g (from IFCT or user)"
    )


class IngredientCreate(IngredientBase):
    """Ingredient creation payload."""

    pass


class IngredientUpdate(BaseModel):
    """Ingredient update payload - all fields optional."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    category: Optional[IngredientCategory] = None
    synonyms: Optional[list[Synonym]] = None
    default_unit: Optional[str] = Field(None, max_length=20)
    ifct_id: Optional[str] = Field(None, max_length=50)
    regions: Optional[list[Region]] = None
    nutrition_per_100g: Optional[dict] = None


class Ingredient(IngredientBase):
    """Ingredient document as stored in MongoDB."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., alias="_id")
    created_at: str = Field(default_factory=lambda: str(int(__import__("time").time())))
    updated_at: str = Field(default_factory=lambda: str(int(__import__("time").time())))

    def add_synonym(self, name: str, region: Optional[Region] = None,
                    language: Optional[str] = None) -> None:
        """Add a synonym if it doesn't already exist."""
        existing = {s.name.lower() for s in self.synonyms}
        if name.lower() not in existing:
            self.synonyms.append(Synonym(name=name, region=region, language=language))

    def matches_name(self, query: str) -> bool:
        """Check if query matches name or any synonym."""
        query_lower = query.lower()
        if self.name.lower() == query_lower:
            return True
        return any(s.name.lower() == query_lower for s in self.synonyms)
