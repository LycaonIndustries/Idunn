"""Pydantic models for Iðunn."""

from .cook_ai import (
    PantryMatchResult,
    PantryToPlateRecipe,
    PantryToPlateRequest,
    SubstitutionQueryRequest,
    SubstitutionSuggestion,
)
from .ingredient import Ingredient, IngredientCreate, IngredientUpdate
from .inventory import Item, ItemCreate, ItemUpdate, Location, Unit, UnitConversion
from .receipt import (
    CATEGORY_SHELF_LIFE_DAYS,
    Receipt,
    ReceiptConfirmRequest,
    ReceiptItemCandidate,
    estimate_shelf_life,
    estimate_storage_location,
)
from .recipe import CuisineType, Difficulty, Recipe, RecipeCreate, RecipeUpdate, Region
from .shopping import (
    ShoppingListBatchCreate,
    ShoppingListItem,
    ShoppingListItemCreate,
    ShoppingListItemUpdate,
    generate_quick_commerce_links,
)

__all__ = [
    "Item",
    "ItemCreate",
    "ItemUpdate",
    "Location",
    "Unit",
    "UnitConversion",
    "Ingredient",
    "IngredientCreate",
    "IngredientUpdate",
    "Recipe",
    "RecipeCreate",
    "RecipeUpdate",
    "Region",
    "CuisineType",
    "Difficulty",
    "PantryMatchResult",
    "SubstitutionSuggestion",
    "SubstitutionQueryRequest",
    "PantryToPlateRequest",
    "PantryToPlateRecipe",
    "ShoppingListItem",
    "ShoppingListItemCreate",
    "ShoppingListItemUpdate",
    "ShoppingListBatchCreate",
    "generate_quick_commerce_links",
    "Receipt",
    "ReceiptConfirmRequest",
    "ReceiptItemCandidate",
    "estimate_shelf_life",
    "estimate_storage_location",
    "CATEGORY_SHELF_LIFE_DAYS",
]
