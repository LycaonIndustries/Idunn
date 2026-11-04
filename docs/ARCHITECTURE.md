# Architecture Overview

Iðunn is an India-aware kitchen operating system designed for pantry management, multimodal recipe ingestion, nutritional calculation, and meal planning.

---

## High-Level Topology

```
┌──────────────────────────────────────────────────────────────┐
│                    Client Browser                            │
│           React 19 + Tailwind CSS + Lucide Icons             │
└──────────────────────────────┬───────────────────────────────┘
                               │ HTTP / JSON
                               ▼
┌──────────────────────────────────────────────────────────────┐
│               FastAPI Application (`backend/`)               │
│                                                              │
│  ┌───────────────────────┐       ┌────────────────────────┐  │
│  │   SPA Static Mount    │       │     REST API (v1)      │  │
│  │   `backend/web_dist`  │       │  /recipes, /inventory  │  │
│  └───────────────────────┘       └───────────┬────────────┘  │
│                                              │               │
│  ┌───────────────────────────────────────────┴────────────┐  │
│  │                  Service Layer                         │  │
│  │  - Recipe Ingest (URL, Audio, Vision, Video Reel)      │  │
│  │  - Nutrition Extractor (Calories, Macros per serving)  │  │
│  │  - Ingredient Matcher & Normalizer                     │  │
│  │  - Unit Converter (Indian regional units)              │  │
│  └───────────────────────────┬────────────────────────────┘  │
│                              │                               │
│  ┌───────────────────────────┴────────────────────────────┐  │
│  │                  Database Router                       │  │
│  │  - Supabase PostgreSQL Client (Primary)                │  │
│  │  - MongoDB Motor Client (Atlas alternative)            │  │
│  │  - In-Memory Mongomock fallback (Zero config offline)  │  │
│  └───────────────────────────┬────────────────────────────┘  │
└──────────────────────────────┼───────────────────────────────┘
                               │
            ┌──────────────────┴──────────────────┐
            ▼                                     ▼
┌───────────────────────┐             ┌───────────────────────┐
│       Supabase        │             │   External AI APIs    │
│  PostgreSQL + RLS     │             │  Google Gemini (BYOK) │
│  Vector + JSONB Store │             │  Anthropic Claude     │
└───────────────────────┘             │  OpenAI / Whisper     │
                                      └───────────────────────┘
```

---

## Directory Organization

```
idunn/
├── backend/                   # FastAPI backend application
│   ├── api/                   # REST API routes (inventory, recipes, settings)
│   ├── db/                    # Database clients (Supabase, Mongo, in-memory)
│   ├── models/                # Pydantic schemas (Recipe, Item, Nutrition)
│   ├── services/              # Ingest engines, ASR, video sampling, matching
│   └── main.py                # FastAPI app initialization and SPA mount
├── frontend/                  # React 19 + Vite + Tailwind CSS frontend
│   ├── src/
│   │   ├── components/        # CaptureZone, RecipeVault, RecipeDetailPage, etc.
│   │   ├── api.ts             # Typed HTTP client with error parsing
│   │   └── types.ts           # Shared TypeScript interfaces
│   └── vite.config.ts         # Output builds to `../backend/web_dist`
├── docs/                      # Technical documentation
│   ├── ARCHITECTURE.md
│   ├── API_REFERENCE.md
│   ├── DATABASE_AND_STORAGE.md
│   └── INGESTION_PIPELINE.md
├── db/                        # PostgreSQL schema definitions & migrations
├── tests/                     # Automated pytest suite (131 tests)
├── Dockerfile                 # Multi-stage production container build
├── docker-compose.yml         # Single-command orchestration
├── pyproject.toml             # Python packaging configuration
└── main.py                    # Root single-command development launcher
```

---

## Key Design Principles

1. **Zero-Configuration Run**: The system defaults to in-memory mocks when cloud database credentials or LLM keys are absent, allowing instant exploration with a single command.
2. **Bring Your Own Keys (BYOK)**: API keys for Gemini, Anthropic, or OpenAI are managed securely via `/api/v1/settings` and stored in runtime environment or `.env`.
3. **Single-Port Architecture**: In production and local execution, FastAPI directly mounts and serves the precompiled React single-page app on `/`, eliminating cross-origin CORS complexity.
4. **Resilient Data Layer**: Supports modern serverless PostgreSQL via Supabase alongside MongoDB Atlas compatibility.
