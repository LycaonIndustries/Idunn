"""Iðunn - Kitchen Inventory & Meal Planning.

Main FastAPI application entry point.
Serves both the API and the built React frontend from a single process.
"""

from __future__ import annotations

import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pymongo.errors import PyMongoError

from .api import cook_ai, ingredients, inventory, receipts, recipes, shopping_list
from .api import settings as settings_api
from .config import settings
from .db import MongoClient
from .db.schemas import setup_database_validation
from .logging_config import setup_logging
from .services.ingest_errors import (
    ExtractionError,
    IngestError,
    ProviderError,
    ProviderNotConfiguredError,
    SourceError,
)

# Locate production build output of the web frontend.
WEB_DIST = Path(__file__).resolve().parent / "web_dist"


setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application startup connections and graceful shutdown cleanup.

    Args:
        app: Active FastAPI application instance.

    Yields:
        Control back to the web application runtime.
    """
    # Attempt connecting to live MongoDB database.
    print(f"Starting {settings.app_name} v{settings.app_version}")
    is_connected = await MongoClient.ping()
    if is_connected:
        print("MongoDB connected: True (Live MongoDB)")
        try:
            # Apply schema validation rules to prevent corrupt documents.
            await setup_database_validation(MongoClient.get_db())
        except Exception as exc:
            print(f"Warning during MongoDB schema setup: {exc}")
    else:
        # Fall back to in-memory mock client when developer does not run local daemon.
        print("MongoDB offline on localhost:27017 -> using in-memory mock storage (Dev Mode)")
        MongoClient.enable_in_memory_fallback()
    try:
        yield
    finally:
        # Close connection pools when server terminates.
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

# Allow cross-origin requests from development web dev servers.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger("backend.api")


# Record execution duration and status code for all API requests.
@app.middleware("http")
async def log_requests_middleware(request: Request, call_next):
    """Log incoming request method, path, response status, and duration.

    Args:
        request: Incoming HTTP request.
        call_next: Request handler chain.

    Returns:
        Generated Response object.
    """
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000.0
    logger.info(
        "%s %s - completed %s in %.2fms",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


# Mount primary sub-routers for inventory, master ingredients, and recipes.
app.include_router(inventory.router)
app.include_router(ingredients.router)
app.include_router(recipes.router)
app.include_router(receipts.router)
app.include_router(settings_api.router)
app.include_router(cook_ai.router)
app.include_router(shopping_list.router)


@app.exception_handler(IngestError)
async def ingest_error_handler(request: Request, exc: IngestError) -> JSONResponse:
    """Translate ingestion domain errors into HTTP status codes.

    Args:
        request: Incoming HTTP request.
        exc: Domain error raised during recipe extraction.

    Returns:
        JSON response with appropriate HTTP status code.
    """
    # Map ingestion failure types to explicit HTTP error statuses.
    codes = {
        SourceError: 400,
        ExtractionError: 422,
        ProviderNotConfiguredError: 503,
        ProviderError: 502,
    }
    return JSONResponse(status_code=codes.get(type(exc), 422), content={"detail": str(exc)})


@app.exception_handler(PyMongoError)
async def database_error_handler(request: Request, exc: PyMongoError) -> JSONResponse:
    """Catch unhandled database errors and return sanitized 503 error.

    Args:
        request: Incoming HTTP request.
        exc: Database driver error.

    Returns:
        JSON response indicating database unavailability.
    """
    # Return generic 503 so raw database internal credentials or traces are never leaked.
    return JSONResponse(
        status_code=503, content={"detail": "Database operation failed; try again later."}
    )


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """Perform health and connectivity diagnostics for the server.

    Returns:
        Dictionary reporting health status and database backend mode.
    """
    # Check if database is responding or operating in memory mode.
    mongo_ok = await MongoClient.ping()
    is_mock = MongoClient.is_mock()
    if mongo_ok and not is_mock:
        db_state = "connected"
    elif is_mock:
        db_state = "in-memory-dev"
    else:
        db_state = "disconnected"

    return {
        "status": "healthy" if (mongo_ok or is_mock) else "degraded",
        "app": settings.app_name,
        "version": settings.app_version,
        "mongodb": db_state,
    }


# Serve built single page application files when directory exists.
if WEB_DIST.is_dir():
    _assets = WEB_DIST / "assets"
    if _assets.is_dir():
        app.mount("/assets", StaticFiles(directory=str(_assets)), name="frontend-assets")

    @app.get("/favicon.svg", include_in_schema=False)
    async def favicon() -> Response:
        """Serve brand favicon graphic from static assets.

        Returns:
            FileResponse with SVG content, or 404 response if missing.
        """
        # Return local SVG file directly to satisfy browser icon requests.
        path = WEB_DIST / "favicon.svg"
        if path.is_file():
            return FileResponse(str(path), media_type="image/svg+xml")
        return JSONResponse(status_code=404, content={"detail": "Not found"})

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_catch_all(full_path: str) -> FileResponse:
        """Serve index.html for all non-API paths to support client routing.

        Args:
            full_path: Requested URL route path.

        Returns:
            FileResponse streaming the requested file or root index.html.
        """
        # Verify if an exact static file exists on disk before defaulting to index.html.
        file_path = WEB_DIST / full_path
        if full_path and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(WEB_DIST / "index.html"))
else:

    @app.get("/", tags=["root"])
    async def root() -> dict[str, str]:
        """Serve API metadata when web frontend distribution is not built.

        Returns:
            Dictionary with documentation URLs and build instructions.
        """
        # Guide developers on how to enable the graphical interface.
        return {
            "app": settings.app_name,
            "version": settings.app_version,
            "docs": "/docs",
            "openapi": "/openapi.json",
            "phase": "Phase 2 - Recipe Ingest",
            "hint": "Run 'cd frontend && npm run build' to enable the web UI.",
        }
