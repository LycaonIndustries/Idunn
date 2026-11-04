"""Cooking pantry deduction service implementing First-Expire-First-Out (FEFO) logic."""

from __future__ import annotations

from collections import deque
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from ..db import COLLECTION_ITEMS
from ..models.inventory import UNIT_CONVERSIONS, Unit

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

    from ..models.recipe import Recipe


# Build conversion graph adjacency list from predefined Indian unit conversion pairs.
def _build_conversion_graph() -> dict[Unit, dict[Unit, float]]:
    """Build graph of unit conversions for multi-step path search.

    Returns:
        Adjacency dictionary mapping units to neighbors with conversion factors.
    """
    graph: dict[Unit, dict[Unit, float]] = {}
    for (src, dst), factor in UNIT_CONVERSIONS.items():
        if src not in graph:
            graph[src] = {}
        graph[src][dst] = factor
    return graph


CONVERSION_GRAPH = _build_conversion_graph()


def get_unit_conversion_factor(from_unit: Unit, to_unit: Unit) -> float | None:
    """Find conversion multiplier using breadth-first search across unit graph.

    Args:
        from_unit: Starting measurement unit.
        to_unit: Target measurement unit.

    Returns:
        Float multiplier if a path exists, None otherwise.
    """
    # Identical units require no conversion factor.
    if from_unit == to_unit:
        return 1.0

    # Search shortest conversion path using BFS to avoid circular conversion loops.
    queue: deque[tuple[Unit, float]] = deque([(from_unit, 1.0)])
    visited: set[Unit] = {from_unit}

    while queue:
        curr, factor = queue.popleft()
        neighbors = CONVERSION_GRAPH.get(curr, {})
        for nxt, mult in neighbors.items():
            if nxt == to_unit:
                return factor * mult
            if nxt not in visited:
                visited.add(nxt)
                queue.append((nxt, factor * mult))

    return None


class DeductionItem(BaseModel):
    """Details of a single deducted pantry inventory batch."""

    item_id: str = Field(..., description="Database item identifier")
    item_name: str = Field(..., description="Pantry item label")
    deducted_quantity: float = Field(..., ge=0, description="Deducted quantity amount")
    unit: str = Field(..., description="Item measurement unit")
    depleted: bool = Field(False, description="True if stock became zero")
    remaining_quantity: float = Field(..., ge=0, description="Remaining stock quantity")


class IngredientShortage(BaseModel):
    """Shortage report for recipe ingredients with insufficient pantry stock."""

    ingredient_name: str = Field(..., description="Missing ingredient name")
    required_quantity: float = Field(..., ge=0, description="Required quantity for recipe")
    available_quantity: float = Field(..., ge=0, description="Available stock quantity")
    missing_quantity: float = Field(..., ge=0, description="Deficit quantity amount")
    unit: str = Field(..., description="Recipe ingredient unit")


class DeductionReport(BaseModel):
    """Summary of all deductions and deficits following cooking execution."""

    recipe_id: str = Field(..., description="Executed recipe identifier")
    servings_multiplier: float = Field(1.0, ge=0.1, description="Servings scale factor")
    deductions: list[DeductionItem] = Field(default_factory=list)
    shortages: list[IngredientShortage] = Field(default_factory=list)
    fully_satisfied: bool = Field(True, description="True if all ingredients were satisfied")


class CookingDeductionService:
    """Manages automatic deduction of recipe ingredients from pantry stock."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        """Initialize the cooking deduction service.

        Args:
            db: Asynchronous database connection handle.
        """
        self.db = db

    async def deduct_recipe_ingredients(
        self,
        recipe: Recipe,
        servings_multiplier: float = 1.0,
    ) -> DeductionReport:
        """Deduct required ingredient quantities from pantry using FEFO ordering.

        Args:
            recipe: Recipe entity containing required ingredients.
            servings_multiplier: Portion scaling factor.

        Returns:
            DeductionReport documenting consumed pantry items and shortages.
        """
        # Initialize result report to collect all item adjustments.
        report = DeductionReport(
            recipe_id=str(recipe.id),
            servings_multiplier=servings_multiplier,
            deductions=[],
            shortages=[],
            fully_satisfied=True,
        )

        # Scale recipe requirements by user-selected serving multiplier.
        for ing in recipe.ingredients:
            if ing.optional or not ing.quantity or ing.quantity <= 0:
                continue

            needed_recipe_qty = ing.quantity * servings_multiplier
            ing_unit = self._resolve_unit(ing.unit)

            # Query available pantry candidates for this ingredient.
            candidates = await self._find_candidate_items(ing.name)

            # Sort candidate batches by FEFO to consume expiring food first.
            candidates.sort(key=self._fefo_sort_key)

            remaining_needed = needed_recipe_qty
            total_available = 0.0

            for item in candidates:
                if remaining_needed <= 0.0001:
                    break

                item_unit = self._resolve_unit(item.get("unit"))
                conv_factor = self._get_conversion(ing_unit, item_unit)
                if conv_factor is None:
                    continue

                item_qty = float(item.get("quantity", 0.0))
                if item_qty <= 0:
                    continue

                # Compute available portion in recipe unit terms.
                avail_in_recipe_unit = item_qty / conv_factor
                total_available += avail_in_recipe_unit

                # Deduct minimum of needed quantity and available stock.
                deduct_recipe_qty = min(remaining_needed, avail_in_recipe_unit)
                deduct_item_qty = deduct_recipe_qty * conv_factor

                new_item_qty = max(0.0, round(item_qty - deduct_item_qty, 4))
                depleted = new_item_qty <= 0.0001
                if depleted:
                    new_item_qty = 0.0

                # Update database record immediately to maintain inventory integrity.
                await self.db[COLLECTION_ITEMS].update_one(
                    {"_id": item["_id"]},
                    {
                        "$set": {
                            "quantity": new_item_qty,
                            "consumed": depleted,
                            "updated_at": datetime.now(UTC),
                        }
                    },
                )

                # Record successful deduction in final report.
                report.deductions.append(
                    DeductionItem(
                        item_id=str(item["_id"]),
                        item_name=item["name"],
                        deducted_quantity=round(deduct_item_qty, 4),
                        unit=str(item.get("unit", "")),
                        depleted=depleted,
                        remaining_quantity=new_item_qty,
                    )
                )

                remaining_needed -= deduct_recipe_qty

            # Record shortage if pantry lacked sufficient quantity.
            if remaining_needed > 0.0001:
                report.fully_satisfied = False
                report.shortages.append(
                    IngredientShortage(
                        ingredient_name=ing.name,
                        required_quantity=round(needed_recipe_qty, 4),
                        available_quantity=round(needed_recipe_qty - remaining_needed, 4),
                        missing_quantity=round(remaining_needed, 4),
                        unit=str(ing.unit or ""),
                    )
                )

        return report

    async def _find_candidate_items(self, ingredient_name: str) -> list[dict]:
        """Find active non-consumed pantry records matching ingredient name.

        Args:
            ingredient_name: Raw name of target ingredient.

        Returns:
            List of matching active item document dictionaries.
        """
        # Fetch active inventory items to avoid querying discarded records.
        cursor = self.db[COLLECTION_ITEMS].find({"consumed": False, "quantity": {"$gt": 0}})
        items = await cursor.to_list(length=500)

        clean_target = ingredient_name.strip().lower()
        target_words = set(clean_target.split())

        matched: list[dict] = []
        for item in items:
            item_name = str(item.get("name", "")).strip().lower()
            item_words = set(item_name.split())

            # Match exact match or substring or shared significant words.
            if (
                clean_target in item_name
                or item_name in clean_target
                or bool(target_words & item_words)
            ):
                matched.append(item)

        return matched

    def _fefo_sort_key(self, item: dict) -> tuple[int, datetime]:
        """Generate sort key prioritizing earlier expiration dates.

        Args:
            item: Item document dictionary.

        Returns:
            Tuple with presence flag and expiry date.
        """
        # Place items with known expiry dates before items lacking dates.
        exp = item.get("expiry_date")
        if exp is None:
            return (1, datetime(2099, 1, 1, tzinfo=UTC))
        return (0, exp)

    def _resolve_unit(self, unit_val: str | Unit | None) -> Unit:
        """Resolve unit string or enum into standardized Unit enum.

        Args:
            unit_val: Unit string or enum instance.

        Returns:
            Resolved Unit enum, defaulting to PIECE if unrecognized.
        """
        # Convert string to lowercase for case-insensitive enum resolution.
        if isinstance(unit_val, Unit):
            return unit_val
        if not unit_val:
            return Unit.PIECE

        clean = unit_val.strip().lower()
        for u in Unit:
            if u.value == clean:
                return u

        return Unit.PIECE

    def _get_conversion(self, from_unit: Unit, to_unit: Unit) -> float | None:
        """Calculate unit conversion multiplier between two units.

        Args:
            from_unit: Source unit.
            to_unit: Target unit.

        Returns:
            Conversion multiplier float or None if incompatible.
        """
        # Fast path returns unity multiplier when units match.
        if from_unit == to_unit:
            return 1.0

        return get_unit_conversion_factor(from_unit, to_unit)
