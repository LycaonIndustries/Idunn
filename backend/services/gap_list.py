"""Pantry gap shopping list generator for planned weekly meals."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from ..db import COLLECTION_ITEMS, COLLECTION_MEAL_PLANS, COLLECTION_RECIPES
from ..models.inventory import Unit
from ..models.shopping import (
    AggregatedShoppingItem,
    AisleCategory,
    PantryGapResponse,
    generate_quick_commerce_links,
)
from .cooking_deduction import get_unit_conversion_factor

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

AISLE_KEYWORDS: dict[AisleCategory, str] = {
    AisleCategory.STAPLES: "oil sugar chini tea chai coffee vinegar",
    AisleCategory.PRODUCE: (
        "onion pyaz tomato tamatar potato aloo ginger adrak garlic lehsun "
        "coriander cilantro dhania curry chilli mirch spinach palak carrot "
        "gajar gobi peas matar capsicum lemon"
    ),
    AisleCategory.DAIRY: "milk doodh paneer curd dahi yogurt butter ghee cream cheese",
    AisleCategory.SPICES: (
        "turmeric haldi cumin jeera rai sarson mustard garam cardamom "
        "elaichi clove laung cinnamon dalchini salt namak hing"
    ),
    AisleCategory.GRAINS: "rice chawal atta flour maida sooji rava oats poha besan dal",
}


def categorize_aisle(name: str) -> AisleCategory:
    """Classify ingredient into standard retail grocery aisle.

    Args:
        name: Raw or normalized ingredient name.

    Returns:
        Mapped AisleCategory enum.
    """
    clean = name.lower().strip()
    # Check keyword patterns across aisles in priority order.
    for aisle, keywords in AISLE_KEYWORDS.items():
        if any(kw in clean for kw in keywords.split()):
            return aisle
    return AisleCategory.OTHER


def _to_id_query(val: str) -> dict:
    """Build query filter accepting string or BSON ObjectId.

    Args:
        val: Document identifier string.

    Returns:
        Mongo query dict matching by str or ObjectId.
    """
    try:
        from bson import ObjectId

        if ObjectId.is_valid(val):
            return {"$or": [{"_id": val}, {"_id": ObjectId(val)}]}
    except (ImportError, Exception):
        pass
    return {"_id": val}


def _try_convert_qty(qty: float, src_unit: str, dst_unit: str) -> float | None:
    """Attempt conversion between unit strings using unit graph.

    Args:
        qty: Magnitude to convert.
        src_unit: Source unit name.
        dst_unit: Destination unit name.

    Returns:
        Converted float value or None if incompatible.
    """
    try:
        factor = get_unit_conversion_factor(
            Unit(src_unit.lower().strip()), Unit(dst_unit.lower().strip())
        )
        return qty * factor if factor is not None else None
    except ValueError:
        return None


async def generate_pantry_gap_shopping_list(
    plan_id: str,
    owner_id: str,
    db: AsyncIOMotorDatabase,
    auto_add_to_list: bool = False,
) -> PantryGapResponse:
    """Aggregate required ingredients for meal plan and subtract in-stock inventory.

    Args:
        plan_id: Weekly meal plan document identifier.
        owner_id: Tenant user identifier.
        db: Database session.
        auto_add_to_list: Whether to persist gap items to shopping list.

    Returns:
        PantryGapResponse containing required and missing quantities.
    """
    # Fetch weekly plan to extract recipe assignments.
    plan = await db[COLLECTION_MEAL_PLANS].find_one(_to_id_query(plan_id))
    if not plan:
        raise ValueError(f"Meal plan {plan_id} not found.")

    # Aggregate required ingredients across all planned meals.
    required: dict[str, dict] = {}
    for day in plan.get("days", []):
        for slot in day.get("slots", []):
            rid = slot.get("recipe_id")
            if not rid:
                continue
            recipe = await db[COLLECTION_RECIPES].find_one(_to_id_query(rid))
            if not recipe:
                continue

            scale = float(slot.get("servings", 2.0)) / max(1.0, float(recipe.get("servings", 2.0)))
            rtitle = recipe.get("title", rid)

            for ing in recipe.get("ingredients", []):
                name = ing.get("name", "").strip().lower()
                if not name:
                    continue
                qty = float(ing.get("quantity", 1.0)) * scale
                unit = ing.get("unit", "piece").strip().lower()

                if name not in required:
                    required[name] = {"qty": qty, "unit": unit, "recipes": [rtitle]}
                else:
                    conv = _try_convert_qty(qty, unit, required[name]["unit"])
                    required[name]["qty"] += conv if conv is not None else qty
                    if rtitle not in required[name]["recipes"]:
                        required[name]["recipes"].append(rtitle)

    # Fetch active unconsumed pantry inventory to calculate gaps.
    pantry_docs = await db[COLLECTION_ITEMS].find({"consumed": False}).to_list(1000)
    pantry_stock: dict[str, dict] = {}
    for item in pantry_docs:
        name = item.get("name", "").strip().lower()
        qty = float(item.get("quantity", 0.0))
        unit = item.get("unit", "piece").strip().lower()
        if name not in pantry_stock:
            pantry_stock[name] = {"qty": qty, "unit": unit}
        else:
            conv = _try_convert_qty(qty, unit, pantry_stock[name]["unit"])
            pantry_stock[name]["qty"] += conv if conv is not None else qty

    # Subtract pantry stock from required ingredients to find shortage.
    gap_items: list[AggregatedShoppingItem] = []
    for name, req_info in required.items():
        req_qty = req_info["qty"]
        req_unit = req_info["unit"]
        stock_info = pantry_stock.get(name)
        in_stock = 0.0

        if stock_info:
            conv = _try_convert_qty(stock_info["qty"], stock_info["unit"], req_unit)
            in_stock = conv if conv is not None else stock_info["qty"]

        gap = max(0.0, req_qty - in_stock)
        if gap > 0:
            iname = name.title()
            gap_items.append(
                AggregatedShoppingItem(
                    name=iname,
                    required_quantity=round(req_qty, 2),
                    in_stock_quantity=round(in_stock, 2),
                    gap_quantity=round(gap, 2),
                    unit=req_unit,
                    aisle=categorize_aisle(name),
                    recipes=req_info["recipes"],
                    quick_links=generate_quick_commerce_links(iname),
                )
            )

    # Add missing items to shopping list if requested by caller.
    if auto_add_to_list and gap_items:
        now = datetime.now(UTC)
        for gi in gap_items:
            await db.shopping_list.insert_one(
                {
                    "_id": str(uuid4()),
                    "name": gi.name,
                    "quantity": gi.gap_quantity,
                    "unit": gi.unit,
                    "checked": False,
                    "created_at": now,
                    "updated_at": now,
                }
            )

    return PantryGapResponse(
        plan_id=plan_id,
        week_start_date=plan.get("week_start_date", ""),
        gap_items=gap_items,
        total_gap_count=len(gap_items),
        added_to_shopping_list=auto_add_to_list,
    )
