# Unified App UI, Single-Server Mount & MCP Server Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a complete React + Tailwind frontend for Iðunn, mount it directly into FastAPI so a single server serves both UI and API, provide a multi-stage Docker setup, and build an official Model Context Protocol (MCP) server for AI assistants.

**Architecture:** 
- A modern SPA built with Vite, React 19, Tailwind CSS, and Lucide icons in `frontend/`, providing the 4-stream capture zone, recipe vault, and pantry view.
- FastAPI mounts the compiled static distribution at `/` with SPA catch-all routing, allowing one command (`uv run uvicorn idunn.main:app`) or `docker compose up` to serve everything on port 8000.
- A Python MCP server in `src/idunn/mcp/` using the official `mcp` SDK exposing 6 core kitchen tools over stdio.

**Tech Stack:** React 19, Vite, Tailwind CSS, Lucide React, FastAPI, Python 3.13, Pydantic v2, Python `mcp` SDK, Docker.

**Spec:** `C:\Users\aesir\Work\Projects\Full\Mimir\300 - Work/310 - Personal/312 - Idunn/Idunn-design.md`

## Global Constraints
- Python 3.13 / 3.14 compatibility with `uv` package management.
- Backend API endpoints must remain strictly under `/api/v1/` and docs under `/docs`.
- Frontend must support direct drag-and-drop file uploads for photos, audio, and video reels to existing FastAPI endpoints.
- Single-port operation on `http://localhost:8000`.

## Review Focus
1. Large file upload progress & error handling (up to 100MB video, 50MB audio).
2. SPA client-side route fallback without breaking FastAPI `/api/` or `/docs` routes.
3. FastMCP / stdio transport resilience with async MongoDB calls.
4. Missing API keys handled gracefully in both UI notifications and MCP tool returns.
5. Multi-stage Docker build caching and minimal container image size.

---

### Task 1: Vite + React Frontend Interface (`frontend/`)

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/types.ts`
- Create: `frontend/src/api.ts`
- Create: `frontend/src/components/Navbar.tsx`
- Create: `frontend/src/components/CaptureZone.tsx`
- Create: `frontend/src/components/RecipeVault.tsx`
- Create: `frontend/src/components/PantryView.tsx`
- Create: `frontend/src/components/RecipeCard.tsx`

**Steps:**
- [ ] Initialize `frontend` directory with Vite, React, TypeScript, and Tailwind CSS.
- [ ] Install dependencies: `lucide-react`, `tailwindcss`, `@tailwindcss/vite` (or postcss).
- [ ] Implement `src/types.ts` mirroring Iðunn's Pydantic models (`Recipe`, `Ingredient`, `Step`, `InventoryItem`).
- [ ] Implement `src/api.ts` handling typed API calls to `/api/v1/recipes`, `/api/v1/recipes/ingest/*`, and `/api/v1/inventory`.
- [ ] Build `CaptureZone.tsx` with tabs:
  - Tab 1: Photos & Screenshots (drag-and-drop image upload).
  - Tab 2: Audio & Voice Notes (file drop / recording placeholder).
  - Tab 3: Silent Video Reels (file drop with 1 fps processing feedback).
  - Tab 4: Web URLs & Text (pasted URLs and WhatsApp text).
  - Extraction preview card with editable details and "Save to Vault" button.
- [ ] Build `RecipeVault.tsx` displaying cards with search, serving scaling (`×1`, `×2`, `×4`), tag filters, and step drawer.
- [ ] Build `PantryView.tsx` listing current stock, locations, and quick item additions.
- [ ] Verify frontend build completes cleanly (`npm run build`).
- [ ] Commit changes.

---

### Task 2: FastAPI Static Mount & SPA Routing

**Files:**
- Modify: `src/idunn/main.py`
- Modify: `pyproject.toml`
- Test: `tests/test_spa_mount.py`

**Steps:**
- [ ] Configure Vite in `frontend/vite.config.ts` to output build to `src/idunn/web_dist`.
- [ ] Build the frontend bundle into `src/idunn/web_dist`.
- [ ] In `src/idunn/main.py`, mount static assets under `/assets` and add a catch-all route `/` serving `index.html` when `web_dist` exists.
- [ ] Ensure `/api/v1/*` and `/docs` routes are unaffected.
- [ ] Write integration test `tests/test_spa_mount.py` verifying `GET /` returns HTML and `GET /api/v1/recipes` still returns JSON.
- [ ] Commit changes.

---

### Task 3: Multi-Stage Dockerfile & Docker Compose

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Create: `.dockerignore`

**Steps:**
- [ ] Create `Dockerfile` with multi-stage build:
  - Stage 1 (`node:22-alpine`): builds `frontend/` into `/app/src/idunn/web_dist`.
  - Stage 2 (`python:3.13-slim`): installs `uv`, system `ffmpeg`, copies backend + built frontend, runs `uvicorn`.
- [ ] Create `docker-compose.yml` exposing port 8000 and passing `.env` file.
- [ ] Create `.dockerignore` ignoring virtual environments, caches, and test artifacts.
- [ ] Test docker build syntax.
- [ ] Commit changes.

---

### Task 4: Iðunn MCP Server

**Files:**
- Modify: `pyproject.toml`
- Create: `src/idunn/mcp/__init__.py`
- Create: `src/idunn/mcp/server.py`
- Create: `src/idunn/mcp/tools.py`
- Test: `tests/test_mcp_server.py`

**Steps:**
- [ ] Add `mcp>=1.0.0` dependency to `pyproject.toml`.
- [ ] Implement `src/idunn/mcp/tools.py` wrapping core services:
  - `idunn_get_inventory`
  - `idunn_update_inventory`
  - `idunn_search_recipes`
  - `idunn_ingest_recipe`
  - `idunn_what_can_i_cook`
  - `idunn_shopping_list`
- [ ] Implement `src/idunn/mcp/server.py` with standard FastMCP/stdio transport and CLI runner.
- [ ] Add CLI entrypoint `idunn-mcp = "idunn.mcp.server:main"` in `pyproject.toml`.
- [ ] Write unit tests in `tests/test_mcp_server.py` mocking tool invocations and checking outputs.
- [ ] Run test suite with `uv run pytest tests/test_mcp_server.py`.
- [ ] Commit changes.

---

### Task 5: End-to-End Verification, Documentation & Vault Sync

**Files:**
- Modify: `README.md`
- Modify: `C:\Users\aesir\Work\Projects\Full\Mimir\300 - Work/310 - Personal/312 - Idunn/Idunn-design.md`
- Modify: `C:\Users\aesir\Work\Projects\Full\Mimir\Tools\log.md`

**Steps:**
- [ ] Run full backend test suite (`uv run pytest`).
- [ ] Verify FastAPI server starts and serves both UI on `http://localhost:8000/` and API on `http://localhost:8000/api/v1/recipes`.
- [ ] Update `README.md` with UI usage, Docker instructions, and MCP setup guide.
- [ ] Update `Idunn-design.md` and log changes in `Tools/log.md`.
- [ ] Commit all changes.
