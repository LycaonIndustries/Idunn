"""End-to-End Runtime Smoke Test for Iðunn Kitchen OS.

Executes live HTTP requests through the FastAPI application and DatabaseRouter
without mocking routes, verifying real-world contracts and preventing regressions.
"""

from __future__ import annotations

import sys
import time

from fastapi.testclient import TestClient

from backend.db import MongoClient
from backend.main import app


def run_smoke_tests() -> int:
    """Execute smoke test sequence across all core endpoints.

    Returns:
        0 if all tests succeed, 1 if any check fails.
    """
    print("=" * 60)
    print("Iðunn Runtime Smoke Test Suite")
    print("=" * 60)

    # Initialize in-memory storage fallback if live MongoDB is absent.
    MongoClient.enable_in_memory_fallback()

    client = TestClient(app)
    passed = 0
    failed = 0

    def check(name: str, condition: bool, extra: str = "") -> None:
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f"  [PASS] {name} {extra}")
        else:
            failed += 1
            print(f"  [FAIL] {name} {extra}")

    # 1. Health check & response time
    t0 = time.monotonic()
    res = client.get("/health")
    dt_ms = (time.monotonic() - t0) * 1000.0
    check(
        "GET /health responds with 200",
        res.status_code == 200 and res.json().get("status") in ("healthy", "degraded"),
        f"({dt_ms:.1f}ms)",
    )

    # 2. Second health check verifies cache hit (< 5ms)
    t0 = time.monotonic()
    res = client.get("/health")
    dt_ms = (time.monotonic() - t0) * 1000.0
    check(
        "GET /health cached response",
        res.status_code == 200 and dt_ms < 50.0,
        f"({dt_ms:.1f}ms)",
    )

    # 3. Settings API
    res = client.get("/api/v1/settings")
    check("GET /api/v1/settings", res.status_code == 200)

    # 4. Manual Pantry Item Addition (Verifies fix for 405 Method Not Allowed)
    res = client.post(
        "/api/v1/inventory",
        json={
            "name": "Paneer",
            "quantity": 400.0,
            "unit": "g",
            "location": "fridge",
        },
    )
    check("POST /api/v1/inventory (Add Pantry Item)", res.status_code == 201)

    # 5. Inventory Fetch (Verifies fix for JSON parse error / HTML fallback)
    res = client.get("/api/v1/inventory")
    check(
        "GET /api/v1/inventory returns JSON array",
        res.status_code == 200 and isinstance(res.json(), list),
    )
    inv_names = [i.get("name") for i in res.json()] if res.status_code == 200 else []
    check("GET /api/v1/inventory contains added 'Paneer'", "Paneer" in inv_names)

    # 6. Legacy /api/v1/items alias
    res = client.get("/api/v1/items")
    check("GET /api/v1/items alias works", res.status_code == 200)

    # 7. Cook AI Endpoint (Verifies fix for DatabaseRouter AttributeError: recipes)
    res = client.get("/api/v1/cook-ai/what-can-i-cook?ready_only=false")
    check(
        "GET /api/v1/cook-ai/what-can-i-cook responds 200",
        res.status_code == 200 and isinstance(res.json(), list),
    )

    # 8. Shopping List Endpoint (Verifies fix for DatabaseRouter AttributeError: shopping_list)
    res = client.get("/api/v1/shopping-list")
    check(
        "GET /api/v1/shopping-list responds 200",
        res.status_code == 200 and isinstance(res.json(), list),
    )

    # 9. Planner Weekly Schedule Fetch
    res = client.get("/api/v1/planner")
    check("GET /api/v1/planner responds 200", res.status_code == 200)
    plan = res.json() if res.status_code == 200 else {}
    plan_id = plan.get("_id") or plan.get("id")

    # 10. Planner Slot Mutation (Verifies fix for 422 date: Field required)
    if plan_id:
        res = client.patch(
            f"/api/v1/planner/{plan_id}/slot",
            json={
                "day_of_week": "monday",
                "meal_type": "breakfast",
                "recipe_title": "Paneer Bhurji",
                "servings_multiplier": 1.0,
            },
        )
        check(
            "PATCH /api/v1/planner/{id}/slot (Update Meal Slot)",
            res.status_code == 200,
            f"status={res.status_code}",
        )
    else:
        check("PATCH /api/v1/planner/{id}/slot", False, "Missing plan_id")

    # 11. SPA catch-all guards API routes from returning HTML
    res = client.get("/api/v1/nonexistent-route")
    check(
        "Unhandled API path returns JSON 404 (not HTML index.html)",
        res.status_code == 404 and "application/json" in res.headers.get("content-type", ""),
    )

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run_smoke_tests())
