"""Ingredient models for Iðunn - canonical ingredient master.

Supports ingredient normalization, synonym matching, regional names,
unit conversions, and IFCT (Indian Food Composition Tables) linkage.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


# Use string enum so values serialize directly to JSON strings.
class Region(StrEnum):
    """Indian regional cuisines for ingredient context."""

    NORTH = "north_india"
    SOUTH = "south_india"
    EAST = "east_india"
    WEST = "west_india"
    CENTRAL = "central_india"
    NORTHEAST = "northeast_india"
    PAN_INDIA = "pan_india"


# Categorize items to enable category-specific pantry logic and storage rules.
class IngredientCategory(StrEnum):
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


# Synonyms resolve regional nomenclature like 'haldi', 'manjal', 'pasupu' to turmeric.
class Synonym(BaseModel):
    """Alternative name for an ingredient across regional Indian languages."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(..., min_length=1, max_length=100)
    region: Region | None = None
    language: str | None = Field(
        None, min_length=2, max_length=20, description="ISO 639-1 code or language name"
    )


# Base schema defines common attributes for canonical ingredient definitions.
class IngredientBase(BaseModel):
    """Base ingredient fields."""

    model_config = ConfigDict(use_attribute_docstrings=True)

    name: str = Field(..., min_length=1, max_length=100, description="Canonical ingredient name")
    category: IngredientCategory = Field(..., description="Ingredient category")
    synonyms: list[Synonym] = Field(
        default_factory=list, description="Alternative names across regions/languages"
    )
    default_unit: str | None = Field(
        None, max_length=20, description="Default unit for this ingredient"
    )
    ifct_id: str | None = Field(
        None, max_length=50, description="IFCT (Indian Food Composition Tables) ID"
    )
    regions: list[Region] = Field(
        default_factory=list, description="Regions where this ingredient is commonly used"
    )
    nutrition_per_100g: dict | None = Field(
        None, description="Nutrition data per 100g (from IFCT or user)"
    )


# Create payload mirrors base fields for new records.
class IngredientCreate(IngredientBase):
    """Ingredient creation payload."""

    pass


# Update payload makes all fields optional to support partial PATCH operations.
class IngredientUpdate(BaseModel):
    """Ingredient update payload - all fields optional."""

    name: str | None = Field(None, min_length=1, max_length=100)
    category: IngredientCategory | None = None
    synonyms: list[Synonym] | None = None
    default_unit: str | None = Field(None, max_length=20)
    ifct_id: str | None = Field(None, max_length=50)
    regions: list[Region] | None = None
    nutrition_per_100g: dict | None = None


# Persistent entity represents stored database document with identifier and timestamps.
class Ingredient(IngredientBase):
    """Ingredient document as stored in database."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., alias="_id")
    created_at: str = Field(default_factory=lambda: str(int(__import__("time").time())))
    updated_at: str = Field(default_factory=lambda: str(int(__import__("time").time())))

    def add_synonym(
        self,
        name: str,
        region: Region | None = None,
        language: str | None = None,
    ) -> None:
        """Add a synonym if it does not already exist.

        Args:
            name: Alternative name for ingredient.
            region: Optional Indian geographic region.
            language: Optional language name or code.

        Returns:
            None.
        """
        # Compare in lowercase so casing differences do not duplicate synonyms.
        existing = {s.name.lower() for s in self.synonyms}
        if name.lower() not in existing:
            self.synonyms.append(Synonym(name=name, region=region, language=language))

    def matches_name(self, query: str) -> bool:
        """Check if query matches canonical name or any synonym.

        Args:
            query: Name string to compare.

        Returns:
            True if exact match exists on name or synonym, otherwise False.
        """
        # Lowercase both target and candidate to make matching case-insensitive.
        query_lower = query.lower()
        if self.name.lower() == query_lower:
            return True
        return any(s.name.lower() == query_lower for s in self.synonyms)
