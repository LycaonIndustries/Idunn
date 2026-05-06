"""Iðunn - Kitchen Inventory & Meal Planning.

Main FastAPI application entry point.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import ingredients, inventory
from .config import settings
from .db import MongoClient


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    print(f"Starting {settings.app_name} v{settings.app_version}")
    print(f"MongoDB: {settings.mongodb_url}")
    is_connected = await MongoClient.ping()
    print(f"MongoDB connected: {is_connected}")

    yield

    # Shutdown
    print("Shutting down...")
    await MongoClient.close()
    print("Closed MongoDB connection")


app = FastAPI(
    title=settings.app_name,
    description=(
        "India-aware kitchen OS — pantry tracking, recipe library, "
        "'what can I cook?' hybrid retrieval, receipt OCR, macro-aware meal planner."
    ),
    version=settings.app_version,
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(inventory.router)
app.include_router(ingredients.router)
app.include_router(recipes.router)


@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint."""
    mongo_ok = await MongoClient.ping()
    return {
        "status": "healthy" if mongo_ok else "degraded",
        "app": settings.app_name,
        "version": settings.app_version,
        "mongodb": "connected" if mongo_ok else "disconnected",
    }


@app.get("/", tags=["root"])
async def root():
    """Root endpoint with API info."""
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "openapi": "/openapi.json",
        "phase": "Phase 1 - Inventory Core",
    }
