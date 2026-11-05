"""Integration tests for weekly meal planner REST API endpoints."""

from __future__ import annotations

import pytest


@pytest.fixture
def client(api_client):
    """Provide isolated API test client session.

    Args:
        api_client: Root test fixture client.

    Returns:
        Configured TestClient instance.
    """
    return api_client


class TestPlannerAPI:
    """Test suite verifying planner retrieval, creation, updating, and slot editing."""

    def test_get_or_initialize_default_plan(self, client) -> None:
        """Verify GET initializes empty 7-day schedule when no plan exists."""
        resp = client.get("/api/v1/planner?week_start_date=2026-12-07")
        assert resp.status_code == 200
        data = resp.json()
        assert data["week_start_date"] == "2026-12-07"
        assert len(data["days"]) == 7
        assert data["days"][0]["day_of_week"] == "monday"
        assert len(data["days"][0]["slots"]) == 3

    def test_create_weekly_plan_and_conflict_handling(self, client) -> None:
        """Verify POST creates new plan and blocks duplicates with 409 Conflict."""
        week = "2026-12-14"
        payload = {"week_start_date": week, "days": []}
        create_resp = client.post("/api/v1/planner", json=payload)
        assert create_resp.status_code == 201
        assert create_resp.json()["week_start_date"] == week

        # Attempt creating duplicate schedule for identical week.
        conflict_resp = client.post("/api/v1/planner", json=payload)
        assert conflict_resp.status_code == 409

    def test_update_weekly_meal_plan(self, client) -> None:
        """Verify PUT replaces entire days collection on existing schedule."""
        init_resp = client.get("/api/v1/planner?week_start_date=2026-12-21")
        plan = init_resp.json()
        plan_id = plan["_id"]
        days = plan["days"]
        days[0]["slots"][0]["notes"] = "Oatmeal with berries"

        update_resp = client.put(f"/api/v1/planner/{plan_id}", json={"days": days})
        assert update_resp.status_code == 200
        assert update_resp.json()["days"][0]["slots"][0]["notes"] == "Oatmeal with berries"

        missing_resp = client.put("/api/v1/planner/non-existent-id", json={"days": days})
        assert missing_resp.status_code == 404

    def test_patch_meal_slot_assignment(self, client) -> None:
        """Verify PATCH mutates specific meal slot attributes and completion."""
        init_resp = client.get("/api/v1/planner?week_start_date=2026-12-28")
        plan_id = init_resp.json()["_id"]

        slot_payload = {
            "date": "2026-12-28",
            "meal_type": "lunch",
            "recipe_id": "recipe_123",
            "custom_title": "Spicy Ramen",
            "servings": 3.0,
            "notes": "Extra chili oil",
            "completed": True,
        }
        patch_resp = client.patch(f"/api/v1/planner/{plan_id}/slot", json=slot_payload)
        assert patch_resp.status_code == 200
        patched = patch_resp.json()
        lunch_slot = next(s for s in patched["days"][0]["slots"] if s["meal_type"] == "lunch")
        assert lunch_slot["recipe_id"] == "recipe_123"
        assert lunch_slot["custom_title"] == "Spicy Ramen"
        assert lunch_slot["completed"] is True

        # Bad date returns 400; missing id returns 404.
        bad_resp = client.patch(
            f"/api/v1/planner/{plan_id}/slot", json=dict(slot_payload, date="2099-01-01")
        )
        assert bad_resp.status_code == 400
        assert client.patch("/api/v1/planner/missing/slot", json=slot_payload).status_code == 404

    def test_delete_weekly_meal_plan(self, client) -> None:
        """Verify DELETE removes weekly plan document from database."""
        init_resp = client.get("/api/v1/planner?week_start_date=2027-01-04")
        plan_id = init_resp.json()["_id"]
        assert client.delete(f"/api/v1/planner/{plan_id}").status_code == 204
        assert client.delete(f"/api/v1/planner/{plan_id}").status_code == 404
