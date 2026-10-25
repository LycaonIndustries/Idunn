"""Iðunn - Kitchen Inventory & Meal Planning.

Main FastAPI application entry point.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pymongo.errors import PyMongoError

from .api import ingredients, inventory, recipes
from .config import settings
from .db import MongoClient
from .db.schemas import setup_database_validation
from .services.ingest_errors import (
    ExtractionError,
    IngestError,
    ProviderError,
    ProviderNotConfiguredError,
    SourceError,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    print(f"Starting {settings.app_name} v{settings.app_version}")
    is_connected = await MongoClient.ping()
    print(f"MongoDB connected: {is_connected}")
    try:
        if is_connected:
            await setup_database_validation(MongoClient.get_db())
        yield
    finally:
        await MongoClient.close()


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


@app.exception_handler(IngestError)
async def ingest_error_handler(request: Request, exc: IngestError):
    codes = {
        SourceError: 400, ExtractionError: 422,
        ProviderNotConfiguredError: 503, ProviderError: 502,
    }
    return JSONResponse(status_code=codes.get(type(exc), 422), content={"detail": str(exc)})


@app.exception_handler(PyMongoError)
async def database_error_handler(request: Request, exc: PyMongoError):
    return JSONResponse(
        status_code=503, content={"detail": "Database operation failed; try again later."}
    )


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
        "phase": "Phase 2 - Recipe Ingest",
    }
