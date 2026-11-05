<div align="center">

# 🍏 Iðunn — Kitchen OS

**An India-aware, multimodal kitchen operating system and recipe vault.**  
*Track pantry inventory, ingest recipes from anywhere with photos and nutrition macros, and scale ingredients seamlessly.*

[![Python](https://img.shields.io/badge/Python-3.13+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=flat&logo=react&logoColor=black)](https://react.dev)
[![Supabase](https://img.shields.io/badge/Database-Supabase-3ECF8E?style=flat&logo=supabase&logoColor=white)](https://supabase.com)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-v4_Dark_Mode-06B6D4?style=flat&logo=tailwindcss&logoColor=white)](https://tailwindcss.com)
[![Tests](https://img.shields.io/badge/Tests-214_Passing-success?style=flat&logo=pytest&logoColor=white)](tests/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=flat&logo=docker&logoColor=white)](Dockerfile)

</div>

---

## Highlights

- **Multimodal AI Recipe Ingestion**: Import recipes directly from YouTube videos, food blogs, cookbook photos, WhatsApp forwards, or silent video reels.
- **Cook AI & "What Can I Cook?" Matching**: Real-time pantry-to-vault ranking scoring recipes by percentage of in-stock ingredients with missing item urgency badges.
- **Deterministic Culinary Substitution Engine**: Knowledge-graph based substitutions for Indian regional cooking (e.g. hung curd for sour cream, besan for chickpea flour, tamarind for kokum).
- **Multi-Platform Quick-Commerce Receipt Ingestion**: Scan receipts or delivery confirmations from Blinkit, Zepto, and Instamart with automatic line-item parsing and pantry replenishment.
- **Smart Shopping List with Quick-Commerce Links**: Automatically aggregates missing ingredients across planned meals with direct deep-links to Indian delivery platforms.
- **ICMR/NIN IFCT Indian Nutrition Intelligence**: Macro & micronutrient composition calculation using authoritative ICMR/NIN food composition tables.
- **Dedicated Recipe Pages with Source Photos**: Automatically captures YouTube thumbnails, OpenGraph/Twitter card images, and screenshot photos, paired with interactive serving scalers (`0.5×` to `4×`).
- **Nutritional Macro Intelligence**: Captures calories (kcal), protein, carbohydrates, fat, and fiber per serving.
- **Pantry Tracking with Indian Regional Units**: FEFO (First-Expire-First-Out) pantry tracking supporting *katori*, *chamcha*, *paav*, grams, and kilograms.
- **Zero-Friction Single-Command Launch**: Built-in in-memory fallback runs out of the box with zero external dependencies.
- **BYOK (Bring Your Own Key) Settings**: Configure Gemini, Anthropic, or OpenAI API keys directly in the UI.

---

## Quickstart (Single Command)

### Option A: Docker (Recommended)

Run everything (backend API + precompiled React SPA) in a single container:

```bash
docker compose up --build
```

Open [http://localhost:8000](http://localhost:8000) in your browser.

---

### Option B: Local Python Dev

Using [`uv`](https://docs.astral.sh/uv/) (fast Python package manager):

```bash
# 1. Install dependencies
uv sync

# 2. Run everything in one command
uv run main.py
```

*Or run uvicorn directly with hot reload:*
```bash
uv run uvicorn backend.main:app --reload --port 8000
```

The application automatically serves both the backend API and the frontend client at [http://127.0.0.1:8000](http://127.0.0.1:8000).

---

## Project Structure

```
idunn/
├── backend/                  # FastAPI backend application
│   ├── api/                  # REST route handlers (inventory, recipes, settings)
│   ├── db/                   # Database router (Supabase, Mongo, in-memory)
│   ├── models/               # Pydantic data schemas (Recipe, Item, Nutrition)
│   ├── services/             # Ingestion pipelines, vision extraction, matching
│   └── main.py               # Application entry point & SPA mount
├── frontend/                 # React 19 + Tailwind CSS single-page app
│   ├── src/components/       # CaptureZone, RecipeVault, RecipeDetailPage, etc.
│   └── vite.config.ts        # Builds directly to backend/web_dist
├── docs/                     # Technical documentation & architectural specs
│   ├── ARCHITECTURE.md       # Topology and design patterns
│   ├── API_REFERENCE.md      # REST endpoints and request/response payloads
│   ├── DATABASE_AND_STORAGE.md # Supabase PostgreSQL & MongoDB schemas
│   └── INGESTION_PIPELINE.md # Multi-source extraction architecture
├── db/                       # Supabase schema definitions (schema.sql)
├── tests/                    # Automated test suite (214 tests: Pytest + Bun)
├── Dockerfile                # Multi-stage production container
├── docker-compose.yml        # Orchestration configuration
├── pyproject.toml            # Python packaging & tool configs
└── main.py                   # Single-command runner
```

---

## Configuration & Environment Variables

Copy `.env.example` to `.env` to configure cloud storage and AI providers:

```bash
# Database (defaults to in-memory mock if unconfigured)
DATABASE_BACKEND=supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-key

# AI Vision & Extraction (or configure via in-app Settings)
GEMINI_API_KEY=AIzaSy...
```

---

## Developer Workflow (`Justfile`)

Iðunn includes a [`Justfile`](Justfile) task runner for unified developer ergonomics across backend and frontend:

| Command | Target | Description |
|---|---|---|
| `just dev` | Fullstack | Start development server with hot reload |
| `just test` | Fullstack | Run complete pytest (Python) and bun test (React) suites |
| `just lint` | Fullstack | Check backend with Ruff and frontend with Oxlint |
| `just format` | Fullstack | Auto-format Python backend code |
| `just check` | Fullstack | Pre-push quality gate running all linters and tests |
| `just audit` | Security | Dependency vulnerability audit via `pip-audit` & `bun audit` |
| `just review` | Review Lock | Audit uncommitted diff and update local `.review.lock` |
| `just review-verify` | Review Lock | Verify review lock integrity and diff limits (≤ 500 lines) |
| `just worker` | Background Tasks | Start ARQ Redis asynchronous background worker |

---

## Documentation

For technical specifications, refer to the documentation in [`docs/`](docs/):

- [Architecture & Topology](docs/ARCHITECTURE.md)
- [API Reference](docs/API_REFERENCE.md)
- [Database Schema & Storage](docs/DATABASE_AND_STORAGE.md)
- [Multimodal Ingestion Pipeline](docs/INGESTION_PIPELINE.md)

---

## License

LSAL-AI-1.0 © [Lycaon Industries](https://github.com/LycaonIndustries). See [LICENSE.md](LICENSE.md) for full terms.
