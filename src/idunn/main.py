"""Iðunn - Kitchen Inventory & Meal Planning.

Main FastAPI application entry point.
Serves both the API and the built React frontend from a single process.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
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

# Frontend build output — produced by `npm run build` inside frontend/
WEB_DIST = Path(__file__).resolve().parent / "web_dist"


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


# ---------------------------------------------------------------------------
# SPA static mount — only when frontend/build exists
# ---------------------------------------------------------------------------
# Mount /assets for hashed JS/CSS bundles, then catch-all for SPA routing.
# API routes (/api/*, /docs, /health) are registered first and take priority.
# ---------------------------------------------------------------------------

if WEB_DIST.is_dir():
    _assets = WEB_DIST / "assets"
    if _assets.is_dir():
        app.mount("/assets", StaticFiles(directory=str(_assets)), name="frontend-assets")

    # Serve favicon and other root-level static files
    @app.get("/favicon.svg", include_in_schema=False)
    async def favicon():
        path = WEB_DIST / "favicon.svg"
        if path.is_file():
            return FileResponse(str(path), media_type="image/svg+xml")
        return JSONResponse(status_code=404, content={"detail": "Not found"})

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_catch_all(full_path: str):
        """Serve index.html for all non-API routes (SPA client-side routing)."""
        # First check if the path matches a real static file in web_dist
        file_path = WEB_DIST / full_path
        if full_path and file_path.is_file():
            return FileResponse(str(file_path))
        # Otherwise return index.html for client-side routing
        return FileResponse(str(WEB_DIST / "index.html"))
else:
    @app.get("/", tags=["root"])
    async def root():
        """Root endpoint with API info (no frontend build present)."""
        return {
            "app": settings.app_name,
            "version": settings.app_version,
            "docs": "/docs",
            "openapi": "/openapi.json",
            "phase": "Phase 2 - Recipe Ingest",
            "hint": "Run 'cd frontend && npm run build' to enable the web UI.",
        }
