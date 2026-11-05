"""Weekly meal planner CRUD endpoints for scheduling recipe cooking and grocery forecasting."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..db import COLLECTION_MEAL_PLANS, get_db
from ..models.planner import (
    DayPlan,
    MealPlanCreateRequest,
    MealPlanUpdateRequest,
    MealSlot,
    MealSlotUpdateRequest,
    MealType,
    WeeklyMealPlan,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/planner", tags=["planner"])
Database = Annotated[AsyncIOMotorDatabase, Depends(get_db)]
DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


def get_current_monday_iso() -> str:
    """Calculate ISO date for Monday of current week.

    Returns:
        ISO formatted string (YYYY-MM-DD).
    """
    # Align active date to nearest Monday.
    today = datetime.now(UTC).date()
    return (today - timedelta(days=today.weekday())).isoformat()


def build_default_week_days(monday_iso: str) -> list[DayPlan]:
    """Construct empty 7-day calendar with standard meal slots.

    Args:
        monday_iso: Monday date string.

    Returns:
        Seven-day DayPlan list.
    """
    # Parse starting Monday to calculate sequential calendar dates.
    start = datetime.fromisoformat(monday_iso).date()
    return [
        DayPlan(
            date=(start + timedelta(days=i)).isoformat(),
            day_of_week=name,
            slots=[
                MealSlot(meal_type=MealType.BREAKFAST),
                MealSlot(meal_type=MealType.LUNCH),
                MealSlot(meal_type=MealType.DINNER),
            ],
        )
        for i, name in enumerate(DAYS)
    ]


@router.get("", response_model=WeeklyMealPlan, status_code=status.HTTP_200_OK)
async def get_weekly_meal_plan(
    db: Database,
    week_start_date: str | None = Query(default=None),
    owner_id: str = Query(default="default_user"),
) -> WeeklyMealPlan:
    """Retrieve weekly meal plan or initialize empty schedule.

    Args:
        db: Database session.
        week_start_date: Optional Monday start.
        owner_id: Tenant identifier.

    Returns:
        Active or initialized WeeklyMealPlan.
    """
    monday = week_start_date or get_current_monday_iso()
    query = {"week_start_date": monday, "owner_id": owner_id}
    doc = await db[COLLECTION_MEAL_PLANS].find_one(query)
    if doc:
        doc["_id"] = str(doc.get("_id", ""))
        return WeeklyMealPlan.model_validate(doc)

    # Initialize empty 7-day plan so frontend renders calendar grid.
    plan = WeeklyMealPlan(
        owner_id=owner_id,
        week_start_date=monday,
        days=build_default_week_days(monday),
    )
    await db[COLLECTION_MEAL_PLANS].insert_one(plan.model_dump(by_alias=True))
    return plan


@router.post("", response_model=WeeklyMealPlan, status_code=status.HTTP_201_CREATED)
async def create_weekly_meal_plan(
    db: Database,
    payload: MealPlanCreateRequest,
    owner_id: str = Query(default="default_user"),
) -> WeeklyMealPlan:
    """Create weekly meal schedule for specific starting Monday.

    Args:
        db: Database session.
        payload: MealPlanCreateRequest parameters.
        owner_id: Tenant identifier.

    Returns:
        Created WeeklyMealPlan.

    Raises:
        HTTPException: If plan for week already exists.
    """
    query = {"week_start_date": payload.week_start_date, "owner_id": owner_id}
    if await db[COLLECTION_MEAL_PLANS].find_one(query):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Meal plan for week starting {payload.week_start_date} already exists.",
        )

    # Use custom days if provided or generate default template.
    days = payload.days or build_default_week_days(payload.week_start_date)
    plan = WeeklyMealPlan(owner_id=owner_id, week_start_date=payload.week_start_date, days=days)
    await db[COLLECTION_MEAL_PLANS].insert_one(plan.model_dump(by_alias=True))
    return plan


@router.put("/{plan_id}", response_model=WeeklyMealPlan, status_code=status.HTTP_200_OK)
async def update_weekly_meal_plan(
    plan_id: str,
    payload: MealPlanUpdateRequest,
    db: Database,
    owner_id: str = Query(default="default_user"),
) -> WeeklyMealPlan:
    """Perform full update of days array for a weekly schedule.

    Args:
        plan_id: Meal plan identifier.
        payload: MealPlanUpdateRequest payload.
        db: Database session.
        owner_id: Tenant identifier.

    Returns:
        Updated WeeklyMealPlan entity.

    Raises:
        HTTPException: If target plan not found.
    """
    query = {"_id": plan_id, "owner_id": owner_id}
    if not await db[COLLECTION_MEAL_PLANS].find_one(query):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found.")

    # Convert days to dictionary representation and stamp modification time.
    days_data = [d.model_dump() for d in payload.days]
    now = datetime.now(UTC).isoformat()
    await db[COLLECTION_MEAL_PLANS].update_one(
        query, {"$set": {"days": days_data, "updated_at": now}}
    )
    doc = await db[COLLECTION_MEAL_PLANS].find_one(query)
    doc["_id"] = str(doc.get("_id", ""))
    return WeeklyMealPlan.model_validate(doc)


@router.patch("/{plan_id}/slot", response_model=WeeklyMealPlan, status_code=status.HTTP_200_OK)
async def update_meal_slot(
    plan_id: str,
    payload: MealSlotUpdateRequest,
    db: Database,
    owner_id: str = Query(default="default_user"),
) -> WeeklyMealPlan:
    """Assign or modify a specific meal slot in a weekly plan.

    Args:
        plan_id: Target plan identifier.
        payload: MealSlotUpdateRequest payload.
        db: Database session.
        owner_id: Tenant identifier.

    Returns:
        Updated WeeklyMealPlan entity.

    Raises:
        HTTPException: If plan or target date not found.
    """
    query = {"_id": plan_id, "owner_id": owner_id}
    doc = await db[COLLECTION_MEAL_PLANS].find_one(query)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found.")

    doc["_id"] = str(doc.get("_id", ""))
    plan = WeeklyMealPlan.model_validate(doc)
    day = next((d for d in plan.days if d.date == payload.date), None)
    if not day:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Date not in plan.")

    # Update matching slot attributes or append new slot.
    attrs = {
        "recipe_id": payload.recipe_id,
        "custom_title": payload.custom_title,
        "servings": payload.servings,
        "notes": payload.notes,
        "completed": payload.completed,
    }
    slot = next((s for s in day.slots if s.meal_type == payload.meal_type), None)
    if slot:
        for k, v in attrs.items():
            setattr(slot, k, v)
    else:
        day.slots.append(MealSlot(meal_type=payload.meal_type, **attrs))

    plan.updated_at = datetime.now(UTC)
    await db[COLLECTION_MEAL_PLANS].update_one(query, {"$set": plan.model_dump(by_alias=True)})
    return plan


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_weekly_meal_plan(
    plan_id: str,
    db: Database,
    owner_id: str = Query(default="default_user"),
) -> None:
    """Delete a weekly meal plan by identifier.

    Args:
        plan_id: Target plan identifier.
        db: Database session.
        owner_id: Tenant identifier.

    Raises:
        HTTPException: If target plan not found.
    """
    res = await db[COLLECTION_MEAL_PLANS].delete_one({"_id": plan_id, "owner_id": owner_id})
    if getattr(res, "deleted_count", 1) == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found.")
