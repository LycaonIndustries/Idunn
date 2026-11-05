"""Recipe models for Iðunn - Recipe library with multi-source ingest.

Supports JSON-LD, blog scraping, YouTube transcript extraction,
and ingredient normalization with embedding match.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


# Classify Indian regional cuisines for recipe recommendations and filters.
class Region(StrEnum):
    """Indian regional cuisines."""

    NORTH = "north_india"
    SOUTH = "south_india"
    EAST = "east_india"
    WEST = "west_india"
    CENTRAL = "central_india"
    NORTHEAST = "northeast_india"
    PAN_INDIA = "pan_india"


# Distinguish dietary classifications so vegetarian users never see meat recipes.
class CuisineType(StrEnum):
    """Cuisine dietary categories."""

    VEG = "veg"
    NON_VEG = "non_veg"
    EGG = "egg"
    VEGAN = "vegan"


# Track recipe preparation complexity to help users pick quick weekday meals.
class Difficulty(StrEnum):
    """Recipe cooking difficulty levels."""

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


# Represent parsed ingredient items with associated quantities and preparation notes.
class IngredientItem(BaseModel):
    """Ingredient in a recipe with quantity and unit."""

    model_config = ConfigDict(use_attribute_docstrings=True)

    name: str = Field(..., min_length=1, max_length=200, description="Ingredient name")
    quantity: float | None = Field(None, gt=0, description="Quantity")
    unit: str | None = Field(None, max_length=50, description="Unit of measurement")
    optional: bool = Field(False, description="Is this ingredient optional?")
    group: str | None = Field(
        None, max_length=100, description="Ingredient group (e.g., 'For gravy')"
    )
    notes: str | None = Field(None, max_length=200, description="Additional notes")


# Individual cooking instructions numbered sequentially.
class Step(BaseModel):
    """Recipe step with optional execution duration."""

    model_config = ConfigDict(use_attribute_docstrings=True)

    step_number: int = Field(..., ge=1, description="Step number")
    instruction: str = Field(..., min_length=1, description="Instruction text")
    time_minutes: int | None = Field(None, ge=0, description="Time for this step in minutes")


# Dietary macronutrient and energy values per serving.
class NutritionInfo(BaseModel):
    """Nutrition information per serving."""

    model_config = ConfigDict(use_attribute_docstrings=True)

    calories: float | None = Field(None, ge=0, description="Calories per serving")
    protein: float | None = Field(None, ge=0, description="Protein in grams")
    carbs: float | None = Field(None, ge=0, description="Carbohydrates in grams")
    fat: float | None = Field(None, ge=0, description="Fat in grams")
    fiber: float | None = Field(None, ge=0, description="Fiber in grams")
    is_ifct_verified: bool = Field(
        False, description="Whether macronutrients are verified via ICMR/NIN IFCT tables"
    )


# Core recipe fields common to inputs and saved database entities.
class RecipeBase(BaseModel):
    """Base recipe fields."""

    model_config = ConfigDict(use_attribute_docstrings=True)

    title: str = Field(..., min_length=1, max_length=300, description="Recipe title")
    description: str | None = Field(None, max_length=2000, description="Recipe description")
    ingredients: list[IngredientItem] = Field(
        default_factory=list, description="Recipe ingredients"
    )
    steps: list[Step] = Field(default_factory=list, description="Recipe steps")
    region: Region | None = Field(None, description="Regional cuisine")
    cuisine_type: CuisineType | None = Field(None, description="Veg/Non-veg")
    difficulty: Difficulty | None = Field(None, description="Difficulty level")
    prep_time_minutes: int | None = Field(None, ge=0, description="Preparation time in minutes")
    cook_time_minutes: int | None = Field(None, ge=0, description="Cooking time in minutes")
    servings: int | None = Field(None, ge=1, description="Number of servings")
    source_url: str | None = Field(None, max_length=500, description="Original source URL")
    source_name: str | None = Field(
        None, max_length=100, description="Source name (e.g., 'Hebbar\\'s Kitchen')"
    )
    image_url: str | None = Field(
        None,
        max_length=5_000_000,
        description="Recipe image URL or data URI",
    )
    video_url: str | None = Field(None, max_length=500, description="Video URL (YouTube)")
    tags: list[str] = Field(default_factory=list, description="Tags (e.g., 'lunch', 'dinner')")
    nutrition: NutritionInfo | None = Field(None, description="Nutrition per serving")
    owner_id: str = Field(
        default="dev_user_local",
        description="Owner user identifier for tenant isolation",
    )


# Creation payload inherits all standard fields.
class RecipeCreate(RecipeBase):
    """Recipe creation payload."""

    pass


# Associate recipe ingredient lines with canonical master ingredient IDs.
class IngredientMatch(BaseModel):
    """A match stays tied to its row, including when no canonical name is known."""

    ingredient_index: int = Field(ge=0)
    ingredient_id: str | None = None
    suggested_id: str | None = None
    score: float = Field(0, ge=0, le=1)
    method: Literal["exact", "vector", "unmatched", "manual"] = "unmatched"
    status: Literal["confirmed", "pending", "ignored"] = "pending"


# Payload schema for raw text or clipboard recipe ingestion.
class RecipeTextInput(BaseModel):
    """Input payload for extracting recipes from pasted raw text."""

    text: str = Field(min_length=1, max_length=60_000)
    source_name: str = Field("Pasted recipe", min_length=1, max_length=100)


# Payload schema for web URL ingestion.
class RecipeUrlInput(BaseModel):
    """Input payload for extracting recipes from web URLs."""

    url: str = Field(min_length=1, max_length=500)


# Decision payload for reviewing an ambiguous ingredient link.
class MatchDecision(BaseModel):
    """User decision for linking an ingredient line to canonical database items."""

    ingredient_index: int = Field(ge=0)
    ingredient_id: str | None = None
    ignore: bool = False

    @model_validator(mode="after")
    def choose_one_action(self) -> MatchDecision:
        """Validate that exactly one review action was selected.

        Returns:
            Validated MatchDecision instance.

        Raises:
            ValueError: If neither or both an ingredient_id and ignore are specified.
        """
        # Review actions must either link to an ingredient or explicitly ignore the line.
        if bool(self.ingredient_id) == self.ignore:
            raise ValueError("Choose an ingredient_id or ignore this row")
        return self


# Submission payload for batch reviewing ambiguous ingredient matches.
class RecipeReview(BaseModel):
    """Batch review payload for recipe ingredient matching decisions."""

    revision: int = Field(ge=0)
    decisions: list[MatchDecision] = Field(default_factory=list)
    approve_extraction: bool = False


# Partial update schema for updating recipe metadata and contents.
class RecipeUpdate(BaseModel):
    """Recipe update payload - all fields optional."""

    title: str | None = Field(None, min_length=1, max_length=300)
    description: str | None = Field(None, max_length=2000)
    ingredients: list[IngredientItem] | None = None
    steps: list[Step] | None = None
    region: Region | None = None
    cuisine_type: CuisineType | None = None
    difficulty: Difficulty | None = None
    prep_time_minutes: int | None = Field(None, ge=0)
    cook_time_minutes: int | None = Field(None, ge=0)
    servings: int | None = Field(None, ge=1)
    source_url: str | None = Field(None, max_length=500)
    source_name: str | None = Field(None, max_length=100)
    image_url: str | None = Field(None, max_length=500)
    video_url: str | None = Field(None, max_length=500)
    tags: list[str] | None = None
    nutrition: NutritionInfo | None = None


# Persistent database recipe entity with vector embeddings and audit timestamps.
class Recipe(RecipeBase):
    """Recipe document as stored in database."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., alias="_id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    embedding: list[float] | None = Field(
        None, description="Recipe embedding vector for semantic search"
    )
    normalized_ingredients: list[str] = Field(
        default_factory=list,
        description="Normalized ingredient IDs linked to ingredients collection",
    )
    ingest_source: str | None = Field(
        None, max_length=50, description="Source type: json-ld, blog, youtube, manual"
    )
    ingest_confidence: float | None = Field(
        None, ge=0.0, le=1.0, description="Confidence score of ingestion (0-1)"
    )
    embedding_model: str | None = None
    ingredient_matches: list[IngredientMatch] = Field(default_factory=list)
    needs_review: bool = False
    extraction_reviewed: bool = True
    revision: int = Field(0, ge=0)
