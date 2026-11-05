"""Unit and integration tests for WhatsApp export formatting and share endpoints."""

from __future__ import annotations

from mongomock_motor import AsyncMongoMockClient
from starlette.testclient import TestClient

from backend.db import COLLECTION_MEAL_PLANS, get_db
from backend.main import app
from backend.models.planner import DayPlan, MealSlot, MealType, WeeklyMealPlan
from backend.models.shopping import ShoppingListItem
from backend.services.export_formatters import (
    categorize_ingredient,
    format_whatsapp_meal_plan,
    format_whatsapp_shopping_list,
    generate_whatsapp_share_url,
)


def test_categorize_ingredient() -> None:
    """Verify ingredients map into expected grocery categories."""
    assert categorize_ingredient("Fresh Onions") == "produce"
    assert categorize_ingredient("Dahi / Curd") == "dairy"
    assert categorize_ingredient("Turmeric / Haldi") == "spices"
    assert categorize_ingredient("Aashirvaad Atta") == "staples"
    assert categorize_ingredient("Paper Napkins") == "other"


def test_format_whatsapp_shopping_list_empty() -> None:
    """Verify empty shopping list returns formatted all-stocked message."""
    msg = format_whatsapp_shopping_list([])
    assert "🛒 *Iðunn Weekly Grocery List*" in msg
    assert "All items in stock" in msg


def test_format_whatsapp_shopping_list_grouped() -> None:
    """Verify items are bucketed into Produce, Dairy, and Staples with emojis."""
    items = [
        ShoppingListItem(_id="1", name="Onion", quantity=2.0, unit="kg"),
        ShoppingListItem(_id="2", name="Paneer", quantity=400.0, unit="g"),
        ShoppingListItem(_id="3", name="Basmati Rice", quantity=5.0, unit="kg"),
    ]
    msg = format_whatsapp_shopping_list(items)
    assert "🥬 *Produce:*" in msg
    assert "• Onion — 2 kg" in msg
    assert "🥛 *Dairy & Proteins:*" in msg
    assert "• Paneer — 400 g" in msg
    assert "🌾 *Staples & Grains:*" in msg
    assert "• Basmati Rice — 5 kg" in msg


def test_format_whatsapp_meal_plan() -> None:
    """Verify meal plan formats into clean day-by-day WhatsApp message."""
    plan = WeeklyMealPlan(
        _id="plan_123",
        week_start_date="2026-11-10",
        days=[
            DayPlan(
                date="2026-11-10",
                day_of_week="monday",
                slots=[
                    MealSlot(
                        meal_type=MealType.LUNCH,
                        custom_title="Dal Tadka & Rice",
                        servings=2.0,
                    ),
                    MealSlot(
                        meal_type=MealType.DINNER,
                        custom_title="Palak Paneer",
                        servings=1.0,
                    ),
                ],
            )
        ],
    )
    msg = format_whatsapp_meal_plan(plan)
    assert "📅 *Iðunn Weekly Meal Plan (2026-11-10)*" in msg
    assert "*Monday:*" in msg
    assert "• 🍲 Lunch: Dal Tadka & Rice (2.0 servings)" in msg
    assert "• 🍽️ Dinner: Palak Paneer" in msg


def test_generate_whatsapp_share_url() -> None:
    """Verify generated share URL contains valid percent-encoded text parameter."""
    url = generate_whatsapp_share_url("Hello World!")
    assert url == "https://api.whatsapp.com/send?text=Hello%20World%21"


def test_shopping_list_whatsapp_export_endpoint(api_client: TestClient) -> None:
    """Verify GET /api/v1/shopping-list/export/whatsapp returns formatted payload."""
    res = api_client.get("/api/v1/shopping-list/export/whatsapp")
    assert res.status_code == 200
    data = res.json()
    assert "text" in data
    assert "whatsapp_url" in data
    assert "https://api.whatsapp.com/send?text=" in data["whatsapp_url"]


def test_planner_whatsapp_export_endpoint(api_client: TestClient) -> None:
    """Verify GET /api/v1/planner/{plan_id}/export/whatsapp returns formatted schedule."""
    import asyncio

    mock_db = AsyncMongoMockClient()["test_planner_export"]
    app.dependency_overrides[get_db] = lambda: mock_db

    plan_doc = {
        "_id": "plan_share_abc",
        "owner_id": "default_user",
        "week_start_date": "2026-11-17",
        "days": [
            {
                "date": "2026-11-17",
                "day_of_week": "tuesday",
                "slots": [
                    {
                        "slot_id": "s1",
                        "meal_type": "lunch",
                        "custom_title": "Rajma Chawal",
                        "servings": 2.0,
                    }
                ],
            }
        ],
    }
    asyncio.run(mock_db[COLLECTION_MEAL_PLANS].insert_one(plan_doc))

    res = api_client.get("/api/v1/planner/plan_share_abc/export/whatsapp")
    assert res.status_code == 200
    data = res.json()
    assert "Rajma Chawal" in data["text"]
    assert "https://api.whatsapp.com/send?text=" in data["whatsapp_url"]
