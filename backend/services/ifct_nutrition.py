"""ICMR/NIN IFCT (Indian Food Composition Tables) nutrition engine.

Provides accurate macronutrient calculations for Indian ghar-ka-khaana recipes
using the National Institute of Nutrition 2017 compositional dataset.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..models.recipe import NutritionInfo

if TYPE_CHECKING:
    from ..models.recipe import IngredientItem, Recipe, RecipeCreate


@dataclass(frozen=True)
class IFCTStaple:
    """Nutritional profile per 100 grams based on ICMR-NIN IFCT 2017."""

    food_code: str
    aliases: tuple[str, ...]
    energy_kcal: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: float


# Curated dataset of core Indian culinary ingredients across all major food groups.
# Values represent nutrients per 100g edible portion from ICMR/NIN IFCT 2017.
IFCT_DATASET: tuple[IFCTStaple, ...] = (
    # Cereals and Millets
    IFCTStaple(
        "A001", ("rice", "chawal", "arisi", "basmati", "white rice"), 356.0, 7.9, 78.2, 0.5, 2.8
    ),
    IFCTStaple(
        "A002", ("wheat flour", "atta", "gehun atta", "whole wheat"), 320.0, 10.6, 64.3, 1.5, 11.2
    ),
    IFCTStaple(
        "A003", ("maida", "all purpose flour", "refined flour"), 352.0, 11.0, 73.9, 0.9, 2.7
    ),
    IFCTStaple("A004", ("poha", "flattened rice", "aval"), 346.0, 6.6, 77.3, 1.2, 2.0),
    IFCTStaple("A005", ("sooji", "semolina", "rava"), 348.0, 10.2, 73.4, 0.8, 3.9),
    IFCTStaple("A006", ("oats", "rolled oats"), 374.0, 13.6, 62.8, 6.9, 10.6),
    IFCTStaple("A007", ("bajra", "pearl millet"), 348.0, 11.6, 61.8, 5.0, 11.5),
    IFCTStaple("A008", ("jowar", "sorghum"), 334.0, 10.4, 67.7, 1.9, 10.2),
    IFCTStaple("A009", ("ragi", "finger millet"), 328.0, 7.3, 72.0, 1.3, 11.5),
    # Grain Legumes and Pulses
    IFCTStaple(
        "B001", ("toor dal", "arhar dal", "tuvar dal", "pigeon pea"), 335.0, 22.3, 57.6, 1.7, 9.1
    ),
    IFCTStaple(
        "B002", ("moong dal", "mung dal", "yellow moong", "green gram"), 348.0, 24.5, 59.9, 1.2, 8.2
    ),
    IFCTStaple("B003", ("chana dal", "bengal gram split"), 372.0, 20.8, 59.8, 5.6, 15.3),
    IFCTStaple(
        "B004", ("chana", "kabuli chana", "chickpea", "chole"), 364.0, 19.3, 60.9, 6.0, 17.4
    ),
    IFCTStaple("B005", ("urad dal", "black gram dal", "urad"), 341.0, 24.0, 58.9, 1.4, 9.8),
    IFCTStaple("B006", ("masoor dal", "red lentil"), 343.0, 25.1, 59.0, 0.7, 7.9),
    IFCTStaple("B007", ("rajma", "kidney bean"), 333.0, 22.9, 60.0, 1.3, 15.2),
    IFCTStaple("B008", ("besan", "gram flour", "chickpea flour"), 387.0, 22.4, 57.8, 6.7, 10.8),
    # Dairy
    IFCTStaple("C001", ("paneer", "cottage cheese", "chenna"), 257.0, 18.3, 3.4, 20.8, 0.0),
    IFCTStaple("C002", ("milk", "doodh", "cow milk"), 67.0, 3.2, 4.7, 4.1, 0.0),
    IFCTStaple("C003", ("curd", "dahi", "yogurt"), 60.0, 3.1, 4.0, 4.0, 0.0),
    IFCTStaple("C004", ("ghee", "clarified butter", "desi ghee"), 900.0, 0.0, 0.0, 100.0, 0.0),
    IFCTStaple("C005", ("butter", "makhan"), 717.0, 0.9, 0.1, 81.1, 0.0),
    # Vegetables and Leafy Greens
    IFCTStaple("D001", ("palak", "spinach", "pasalai"), 23.0, 2.9, 2.9, 0.7, 2.2),
    IFCTStaple("D002", ("methi", "fenugreek leaves"), 49.0, 4.4, 6.0, 0.9, 3.9),
    IFCTStaple("D003", ("coriander leaves", "dhaniya patta", "cilantro"), 31.0, 3.3, 3.7, 0.6, 4.2),
    IFCTStaple("D004", ("curry leaves", "kadi patta", "karivepaku"), 108.0, 6.1, 18.7, 1.0, 6.4),
    IFCTStaple("D005", ("onion", "pyaz", "vengayam"), 50.0, 1.4, 11.1, 0.1, 1.7),
    IFCTStaple("D006", ("tomato", "tamatar", "thakkali"), 21.0, 0.9, 3.9, 0.2, 1.2),
    IFCTStaple("D007", ("potato", "aloo", "urulaikizhangu"), 97.0, 1.6, 22.6, 0.1, 1.7),
    IFCTStaple("D008", ("ginger", "adrak", "inji"), 67.0, 1.8, 12.3, 0.9, 2.0),
    IFCTStaple("D009", ("garlic", "lahsun", "poondu"), 145.0, 6.4, 29.8, 0.5, 2.1),
    IFCTStaple("D010", ("green chilli", "hari mirch", "chilli"), 40.0, 2.0, 8.8, 0.2, 1.5),
    IFCTStaple("D011", ("bhindi", "okra", "ladies finger"), 35.0, 1.9, 6.4, 0.2, 3.2),
    IFCTStaple("D012", ("baingan", "brinjal", "eggplant"), 25.0, 1.4, 4.0, 0.3, 3.4),
    IFCTStaple("D013", ("gobi", "cauliflower", "phool gobi"), 30.0, 2.5, 4.0, 0.4, 2.8),
    IFCTStaple("D014", ("shimla mirch", "capsicum", "bell pepper"), 24.0, 1.3, 4.3, 0.3, 1.7),
    IFCTStaple("D015", ("gajar", "carrot"), 48.0, 0.9, 10.6, 0.2, 4.4),
    IFCTStaple("D016", ("matar", "green peas", "peas"), 93.0, 7.2, 15.9, 0.1, 4.5),
    # Oils and Fats
    IFCTStaple("E001", ("mustard oil", "sarson tel"), 900.0, 0.0, 0.0, 100.0, 0.0),
    IFCTStaple("E002", ("groundnut oil", "peanut oil"), 900.0, 0.0, 0.0, 100.0, 0.0),
    IFCTStaple("E003", ("sunflower oil", "refined oil", "oil"), 900.0, 0.0, 0.0, 100.0, 0.0),
    IFCTStaple("E004", ("coconut oil", "nariyal tel"), 892.0, 0.0, 0.0, 99.1, 0.0),
    # Spices and Condiments
    IFCTStaple("F001", ("turmeric", "haldi"), 349.0, 7.8, 69.9, 9.9, 21.1),
    IFCTStaple("F002", ("cumin", "jeera"), 375.0, 17.8, 44.2, 22.3, 10.5),
    IFCTStaple("F003", ("coriander powder", "dhaniya powder"), 288.0, 12.4, 54.9, 17.8, 41.9),
    IFCTStaple("F004", ("red chilli powder", "lal mirch"), 318.0, 12.0, 56.6, 17.3, 27.2),
    IFCTStaple("F005", ("garam masala",), 379.0, 10.8, 56.8, 14.7, 24.0),
    IFCTStaple("F006", ("mustard seeds", "rai", "sarson"), 508.0, 26.1, 28.3, 42.0, 12.2),
    # Sugars and Sweeteners
    IFCTStaple("G001", ("sugar", "cheeni"), 398.0, 0.1, 99.4, 0.0, 0.0),
    IFCTStaple("G002", ("jaggery", "gur", "bellam"), 383.0, 0.4, 85.0, 0.1, 0.0),
    # Poultry, Meat, and Eggs
    IFCTStaple("H001", ("egg", "eggs", "anda"), 143.0, 12.6, 0.7, 9.5, 0.0),
    IFCTStaple("H002", ("chicken", "murgh"), 165.0, 31.0, 0.0, 3.6, 0.0),
    IFCTStaple("H003", ("mutton", "goat meat"), 143.0, 20.6, 0.0, 6.9, 0.0),
    IFCTStaple("H004", ("fish", "rohu", "katla"), 105.0, 18.0, 0.0, 3.0, 0.0),
)


# Approximate piece weights in grams for count-based ingredients.
PIECE_WEIGHT_GRAMS: dict[str, float] = {
    "egg": 50.0,
    "eggs": 50.0,
    "anda": 50.0,
    "onion": 80.0,
    "pyaz": 80.0,
    "tomato": 80.0,
    "tamatar": 80.0,
    "potato": 100.0,
    "aloo": 100.0,
    "green chilli": 5.0,
    "chilli": 5.0,
    "garlic": 5.0,
    "clove": 5.0,
    "carrot": 75.0,
    "gajar": 75.0,
}


def find_ifct_match(ingredient_name: str) -> IFCTStaple | None:
    """Match raw recipe ingredient name against IFCT staple aliases.

    Args:
        ingredient_name: Ingredient text string.

    Returns:
        Matched IFCTStaple record, or None if no match is identified.
    """
    # Normalize name to lower-case word tokens for keyword boundary lookup.
    norm = re.sub(r"[^\w\s]", " ", ingredient_name.lower())
    tokens = set(norm.split())

    # Check multi-word aliases first to prioritize specific matches.
    for staple in IFCT_DATASET:
        for alias in staple.aliases:
            if " " in alias and alias in norm:
                return staple

    # Check single-word aliases matching discrete word tokens.
    for staple in IFCT_DATASET:
        for alias in staple.aliases:
            if " " not in alias and alias in tokens:
                return staple

    return None


def convert_ingredient_to_grams(item: IngredientItem) -> float | None:
    """Translate recipe ingredient quantity and unit into gram mass.

    Args:
        item: Recipe ingredient item.

    Returns:
        Mass in grams, or None if quantity is undefined or cannot be estimated.
    """
    # Missing or zero quantities cannot produce valid nutrient weight.
    if item.quantity is None or item.quantity <= 0:
        return None

    qty = float(item.quantity)
    unit = (item.unit or "").strip().lower()

    # Direct mass units.
    if unit in ("g", "gram", "grams"):
        return qty
    if unit in ("kg", "kilogram", "kilograms"):
        return qty * 1000.0
    if unit in ("paav",):
        return qty * 250.0

    # Indian volumetric kitchen measures.
    if unit in ("tbsp", "tablespoon", "tablespoons"):
        return qty * 15.0
    if unit in ("tsp", "teaspoon", "teaspoons", "chamcha"):
        return qty * 5.0
    if unit in ("katori", "cup", "cups"):
        return qty * 150.0
    if unit in ("ml", "milliliter", "milliliters"):
        return qty * 1.0  # Approx 1g/ml density for liquid food
    if unit in ("l", "liter", "liters", "litre"):
        return qty * 1000.0

    # Count or piece estimation.
    if unit in ("piece", "pieces", "whole", "no", "nos", ""):
        name_lower = item.name.lower()
        for key, weight in PIECE_WEIGHT_GRAMS.items():
            if key in name_lower:
                return qty * weight
        return qty * 50.0  # Default piece weight fallback

    return qty


def calculate_recipe_nutrition(recipe: Recipe | RecipeCreate) -> NutritionInfo:
    """Calculate per-serving macronutrients using ICMR/NIN IFCT standards.

    Args:
        recipe: Target Recipe or RecipeCreate entity.

    Returns:
        Computed NutritionInfo model per serving.
    """
    # Track totals across all recognized ingredients.
    tot_kcal = 0.0
    tot_protein = 0.0
    tot_carbs = 0.0
    tot_fat = 0.0
    tot_fiber = 0.0
    matched_any = False

    # Sum nutrient masses across each recipe ingredient.
    for ing in recipe.ingredients:
        staple = find_ifct_match(ing.name)
        if not staple:
            continue

        grams = convert_ingredient_to_grams(ing)
        if grams is None or grams <= 0:
            continue

        matched_any = True
        ratio = grams / 100.0
        tot_kcal += staple.energy_kcal * ratio
        tot_protein += staple.protein_g * ratio
        tot_carbs += staple.carbs_g * ratio
        tot_fat += staple.fat_g * ratio
        tot_fiber += staple.fiber_g * ratio

    # Unmatched recipes return empty nutrition profile.
    if not matched_any:
        return NutritionInfo(is_ifct_verified=False)

    # Divide by serving count to provide per-serving values.
    servings = max(1, recipe.servings or 1)
    return NutritionInfo(
        calories=round(tot_kcal / servings, 1),
        protein=round(tot_protein / servings, 1),
        carbs=round(tot_carbs / servings, 1),
        fat=round(tot_fat / servings, 1),
        fiber=round(tot_fiber / servings, 1),
        is_ifct_verified=True,
    )
