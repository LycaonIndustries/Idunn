"""User compliance, data portability, and account deletion cascade router.

Implements GDPR and DPDP 'Right to Erasure' (cascade deletion) and 'Right to Data
Portability' (complete machine-readable JSON archive export).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from ..db import (
    COLLECTION_AI_USAGE,
    COLLECTION_ITEMS,
    COLLECTION_MEAL_PLANS,
    COLLECTION_RECEIPTS,
    COLLECTION_RECIPES,
    COLLECTION_SHOPPING_LISTS,
    get_db,
)
from .deps import AuthenticatedUser, get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/users", tags=["users"])
Database = Annotated[AsyncIOMotorDatabase, Depends(get_db)]
CurrentUser = Annotated[AuthenticatedUser, Depends(get_current_user)]


class UserDeletionReport(BaseModel):
    """Audit report detailing records removed during account deletion cascade."""

    status: str = Field(..., description="Deletion execution status")
    user_id: str = Field(..., description="Purged tenant user identifier")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    deleted_counts: dict[str, int] = Field(
        default_factory=dict,
        description="Counts of purged documents per collection",
    )


class UserDataExport(BaseModel):
    """Machine-readable data portability export containing all user entities."""

    export_version: str = Field(default="1.0")
    user_id: str = Field(..., description="Exported tenant user identifier")
    exported_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    inventory_items: list[dict[str, Any]] = Field(default_factory=list)
    recipes: list[dict[str, Any]] = Field(default_factory=list)
    receipts: list[dict[str, Any]] = Field(default_factory=list)
    meal_plans: list[dict[str, Any]] = Field(default_factory=list)
    shopping_list: list[dict[str, Any]] = Field(default_factory=list)


def sanitize_doc(doc: dict[str, Any]) -> dict[str, Any]:
    """Convert non-serializable BSON types to standard JSON values.

    Args:
        doc: Raw database dictionary document.

    Returns:
        Sanitized serializable dictionary.
    """
    clean = dict(doc)
    if "_id" in clean:
        clean["_id"] = str(clean["_id"])
    return clean


@router.delete("/me", response_model=UserDeletionReport)
async def delete_user_account_cascade(
    db: Database,
    user: CurrentUser,
) -> UserDeletionReport:
    """Execute complete cascade deletion across all collections for active user.

    Satisfies GDPR Article 17 and DPDP Right to Erasure mandates.

    Args:
        db: Database session injected via dependency.
        user: Authenticated caller identity.

    Returns:
        UserDeletionReport summarizing all purged database records.
    """
    # Track purged records count across all tenant-isolated storage tables.
    counts: dict[str, int] = {}
    uid = user.id

    logger.warning("Initiating GDPR/DPDP cascade account erasure for user %s", uid)

    # Delete pantry inventory stock.
    res_items = await db[COLLECTION_ITEMS].delete_many({"owner_id": uid})
    counts["inventory_items"] = getattr(res_items, "deleted_count", 0)

    # Delete custom and saved vault recipes.
    res_recipes = await db[COLLECTION_RECIPES].delete_many({"owner_id": uid})
    counts["recipes"] = getattr(res_recipes, "deleted_count", 0)

    # Delete scanned store receipts and OCR records.
    res_receipts = await db[COLLECTION_RECEIPTS].delete_many({"owner_id": uid})
    counts["receipts"] = getattr(res_receipts, "deleted_count", 0)

    # Delete scheduled weekly meal plans.
    res_plans = await db[COLLECTION_MEAL_PLANS].delete_many({"owner_id": uid})
    counts["meal_plans"] = getattr(res_plans, "deleted_count", 0)

    # Delete shopping list entries.
    res_shopping = await db[COLLECTION_SHOPPING_LISTS].delete_many({"owner_id": uid})
    counts["shopping_lists"] = getattr(res_shopping, "deleted_count", 0)

    # Delete AI token usage logs.
    res_ai = await db[COLLECTION_AI_USAGE].delete_many({"user_id": uid})
    counts["ai_usage"] = getattr(res_ai, "deleted_count", 0)

    return UserDeletionReport(
        status="erased",
        user_id=uid,
        deleted_counts=counts,
    )


@router.get("/me/export", response_model=UserDataExport)
async def export_user_data_archive(
    db: Database,
    user: CurrentUser,
) -> UserDataExport:
    """Generate comprehensive JSON export of all personal kitchen data.

    Satisfies GDPR Article 20 and DPDP Right to Data Portability mandates.

    Args:
        db: Database session injected via dependency.
        user: Authenticated caller identity.

    Returns:
        UserDataExport model containing raw items, recipes, receipts, and plans.
    """
    uid = user.id

    # Retrieve all user entities across tenant collections.
    items_cur = db[COLLECTION_ITEMS].find({"owner_id": uid})
    items = [sanitize_doc(d) async for d in items_cur]

    recipes_cur = db[COLLECTION_RECIPES].find({"owner_id": uid})
    recipes = [sanitize_doc(d) async for d in recipes_cur]

    receipts_cur = db[COLLECTION_RECEIPTS].find({"owner_id": uid})
    receipts = [sanitize_doc(d) async for d in receipts_cur]

    plans_cur = db[COLLECTION_MEAL_PLANS].find({"owner_id": uid})
    plans = [sanitize_doc(d) async for d in plans_cur]

    shopping_cur = db[COLLECTION_SHOPPING_LISTS].find({"owner_id": uid})
    shopping = [sanitize_doc(d) async for d in shopping_cur]

    return UserDataExport(
        user_id=uid,
        inventory_items=items,
        recipes=recipes,
        receipts=receipts,
        meal_plans=plans,
        shopping_list=shopping,
    )
