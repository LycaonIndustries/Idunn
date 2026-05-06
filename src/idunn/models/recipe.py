"""Recipe models for Iðunn - Recipe library with multi-source ingest.

Supports JSON-LD, blog scraping, YouTube transcript extraction,
and ingredient normalization with embedding match.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class Region(str, Enum):
    """Indian regional cuisines."""

    NORTH = "north_india"
    SOUTH = "south_india"
    EAST = "east_india"
    WEST = "west_india"
    CENTRAL = "central_india"
    NORTHEAST = "northeast_india"
    PAN_INDIA = "pan_india"


class CuisineType(str, Enum):
    """Cuisine categories."""

    VEG = "veg"
    NON_VEG = "non_veg"
    EGG = "egg"
    VEGAN = "vegan"


class Difficulty(str, Enum):
    """Recipe difficulty levels."""

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class IngredientItem(BaseModel):
    """Ingredient in a recipe with quantity and unit."""

    model_config = ConfigDict(use_attribute_docstrings=True)

    name: str = Field(..., min_length=1, max_length=200, description="Ingredient name")
    quantity: Optional[float] = Field(None, gt=0, description="Quantity")
    unit: Optional[str] = Field(None, max_length=50, description="Unit of measurement")
    optional: bool = Field(False, description="Is this ingredient optional?")
    group: Optional[str] = Field(
        None, max_length=100, description="Ingredient group (e.g., 'For gravy')"
    )
    notes: Optional[str] = Field(None, max_length=200, description="Additional notes")


class Step(BaseModel):
    """Recipe step with optional time."""

    model_config = ConfigDict(use_attribute_docstrings=True)

    step_number: int = Field(..., ge=1, description="Step number")
    instruction: str = Field(..., min_length=1, description="Instruction text")
    time_minutes: Optional[int] = Field(
        None, ge=0, description="Time for this step in minutes"
    )


class NutritionInfo(BaseModel):
    """Nutrition information per serving."""

    model_config = ConfigDict(use_attribute_docstrings=True)

    calories: Optional[float] = Field(None, ge=0, description="Calories per serving")
    protein: Optional[float] = Field(None, ge=0, description="Protein in grams")
    carbs: Optional[float] = Field(None, ge=0, description="Carbohydrates in grams")
    fat: Optional[float] = Field(None, ge=0, description="Fat in grams")
    fiber: Optional[float] = Field(None, ge=0, description="Fiber in grams")


class RecipeBase(BaseModel):
    """Base recipe fields."""

    model_config = ConfigDict(use_attribute_docstrings=True)

    title: str = Field(..., min_length=1, max_length=300, description="Recipe title")
    description: Optional[str] = Field(
        None, max_length=2000, description="Recipe description"
    )
    ingredients: list[IngredientItem] = Field(
        default_factory=list, description="Recipe ingredients"
    )
    steps: list[Step] = Field(default_factory=list, description="Recipe steps")
    region: Optional[Region] = Field(None, description="Regional cuisine")
    cuisine_type: Optional[CuisineType] = Field(None, description="Veg/Non-veg")
    difficulty: Optional[Difficulty] = Field(None, description="Difficulty level")
    prep_time_minutes: Optional[int] = Field(
        None, ge=0, description="Preparation time in minutes"
    )
    cook_time_minutes: Optional[int] = Field(
        None, ge=0, description="Cooking time in minutes"
    )
    servings: Optional[int] = Field(None, ge=1, description="Number of servings")
    source_url: Optional[str] = Field(
        None, max_length=500, description="Original source URL"
    )
    source_name: Optional[str] = Field(
        None, max_length=100, description="Source name (e.g., 'Hebbar's Kitchen')"
    )
    image_url: Optional[str] = Field(None, max_length=500, description="Recipe image URL")
    video_url: Optional[str] = Field(None, max_length=500, description="Video URL (YouTube)")
    tags: list[str] = Field(default_factory=list, description="Tags (e.g., 'lunch', 'dinner')")
    nutrition: Optional[NutritionInfo] = Field(None, description="Nutrition per serving")


class RecipeCreate(RecipeBase):
    """Recipe creation payload."""

    pass


class RecipeUpdate(BaseModel):
    """Recipe update payload - all fields optional."""

    title: Optional[str] = Field(None, min_length=1, max_length=300)
    description: Optional[str] = Field(None, max_length=2000)
    ingredients: Optional[list[IngredientItem]] = None
    steps: Optional[list[Step]] = None
    region: Optional[Region] = None
    cuisine_type: Optional[CuisineType] = None
    difficulty: Optional[Difficulty] = None
    prep_time_minutes: Optional[int] = Field(None, ge=0)
    cook_time_minutes: Optional[int] = Field(None, ge=0)
    servings: Optional[int] = Field(None, ge=1)
    source_url: Optional[str] = Field(None, max_length=500)
    source_name: Optional[str] = Field(None, max_length=100)
    image_url: Optional[str] = Field(None, max_length=500)
    video_url: Optional[str] = Field(None, max_length=500)
    tags: Optional[list[str]] = None
    nutrition: Optional[NutritionInfo] = None


class Recipe(RecipeBase):
    """Recipe document as stored in MongoDB."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    embedding: Optional[list[float]] = Field(
        None, description="Recipe embedding vector for semantic search"
    )
    normalized_ingredients: list[str] = Field(
        default_factory=list,
        description="Normalized ingredient IDs linked to ingredients collection",
    )
    ingest_source: Optional[str] = Field(
        None, max_length=50, description="Source type: json-ld, blog, youtube, manual"
    )
    ingest_confidence: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Confidence score of ingestion (0-1)"
    )
