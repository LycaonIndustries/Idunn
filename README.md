# Iðunn — Kitchen Inventory & Meal Planning

> *In Norse myth, Iðunn guards the golden apples that keep the Æsir fresh. This app does the same for an Indian household kitchen — pantry known, fresh, regional, and useful.*

## Overview

Iðunn is an India-aware kitchen operating system that solves five frictions Western pantry apps don't address:

1. **Invisible inventory** — vegetables rot unseen; dals and atta run out mid-cooking
2. **Recipe–reality gap** — recipes live on YouTube, Instagram, notebooks, WhatsApp; bridging is manual
3. **Western recipe corpus mismatch** — global apps don't index aloo-gobi or bisi-bele-bath
4. **Macro/nutrition for Indian food is broken** — USDA-based DBs miss ghar-ka-khaana
5. **Multi-cook households** — cooks, maids, and family members share the kitchen

## Current status — 2026-10-07

Inventory APIs and the Phase 2 recipe-import backend are built. Recipe imports support structured website data, blog/text extraction, a YouTube transcription path, ingredient matching, and a review API. The local suite has 107 passing tests. Live MongoDB/Atlas, model-service, audio and 100-recipe accuracy checks are still pending. See [Phase 2 progress](docs/PHASE2_PROGRESS.md) for verified results, configuration and remaining work.

## Product scope

- **Pantry tracking** with FEFO (First Expire First Out) ordering
- **Indian unit conversions** (paav, katori, chamcha, tsp, kg, g)
- **Recipe library** with multi-source ingest (YouTube, blogs, WhatsApp, family heirlooms)
- **"What can I cook?"** — hybrid retrieval (vector + BM25 + reranking)
- **Receipt OCR** with PaddleOCR + LLM parsing
- **Macro-aware meal planner** using IFCT (Indian Food Composition Tables)
- **Quick-commerce hand-off** — gap lists → Blinkit/Zepto deep links
- **Family sharing** — export meal plans as images/PDFs for WhatsApp

## Tech Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Language | Python 3.13 + uv | Fastest-growing AI stack |
| Framework | FastAPI | Canonical Python API framework |
| Validation | Pydantic v2 | Type-safe contracts end-to-end |
| Agents | Pydantic AI | Type-safe tools, Anthropic integration |
| Database | MongoDB Atlas (Vector + Search) | Single store for docs + embeddings + BM25 |
| Hybrid search | `$scoreFusion` (RRF) | Native Atlas, no extra infra |
| Reranker | Cohere Rerank 3 / BGE-reranker-large | Highest-ROI improvement |
| Embeddings | Voyage AI / BGE-M3 | Multilingual (English + Hindi/regional) |
| LLMs | Anthropic (Haiku 4.5, Sonnet 4.6) | Cost-aware, prompt caching |
| OCR | PaddleOCR + Claude Vision | Cost-aware, accuracy-tuned |
| ASR | Whisper (large-v3) | Multilingual cooking videos |
| Async jobs | Arq + Redis | Lightweight, async-native |
| Object store | MinIO / Cloudflare R2 | S3-compatible |
| Frontend | Next.js 15 + React 19 | Reuses Frigg design system |
| Evals | RAGAS, Promptfoo, Inspect AI | 2026 RAG-engineer baseline |

## Project Structure

```
idunn/
├── src/idunn/
│   ├── models/          # Pydantic models (Item, Ingredient, Recipe, etc.)
│   ├── api/             # FastAPI route handlers
│   ├── db/              # Database connection & schemas
│   ├── services/        # Business logic (retrieval, OCR, planning)
│   ├── config.py        # Configuration from environment
│   └── main.py         # FastAPI application entry point
├── tests/               # pytest test suite
├── docs/
│   └── adr/             # Architecture Decision Records
├── config/              # Configuration files
└── pyproject.toml       # Project metadata & dependencies
```

## Development Phases

### Phase 1 — Inventory Core
- Pydantic models: Item, Ingredient, Location, Unit, UnitConversion
- CRUD via FastAPI; Mongo schema validation enabled
- FEFO ordering + expiry alerts
- Indian unit graph: chamcha ↔ tsp ↔ ml; katori ↔ cup ↔ ml
- **Exit criteria:** add 50 mixed items; query "expiring this week" returns correctly

### Phase 2 — Recipe Ingest (Current)
- JSON-LD parser, Readability + LLM fallback, YouTube ingest
- Ingredient normalization with embedding match
- Review queue API with revision checks
- Live service and 100-recipe accuracy gate still open

### Phase 3 — Hybrid Retrieval
- Atlas Vector + Search indices, $scoreFusion, cross-encoder reranker
- Pydantic AI cook_advisor agent
- RAGAS eval suite

### Phase 4 — Receipt OCR
- PaddleOCR pipeline + LLM line-item parser
- Per-store extraction profiles

### Phase 5 — Meal Planner + Shopping List
- Weekly planner UI, auto-computed shopping lists
- Quick-commerce deep links

### Phase 6 — Indian Nutrition Layer
- IFCT data ingest, per-recipe macro computation

### Phase 7 — Eval, Ops, Polish
- Promptfoo + Inspect AI suites, OTel tracing, caching

## Getting Started

### Prerequisites
- Python 3.13+
- [uv](https://github.com/astral-sh/uv) package manager
- MongoDB 6.0+ (local or Atlas)
- Redis (for async jobs)

### Installation

```bash
# Clone the repository
cd idunn

# Create .env from example
cp .env.example .env
# Edit .env with your configuration

# Install dependencies
uv sync

# Start MongoDB and Redis (using Docker)
docker run -d -p 27017:27017 --name mongo mongo:latest
docker run -d -p 6379:6379 --name redis redis:latest

# Run the development server
uv run uvicorn idunn.main:app --reload
```

### API Documentation
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI spec: http://localhost:8000/openapi.json

## Architecture Decision Records

1. **[ADR-001](docs/adr/001-mongodb-atlas-as-only-store.md):** MongoDB Atlas as the only store
2. **ADR-002:** Hybrid retrieval with $scoreFusion + cross-encoder reranker (Phase 3)
3. **ADR-003:** Pydantic AI over LangGraph for V1 agents (Phase 3)
4. **ADR-004:** Deterministic-first ingest with LLM repair fallback (Phase 2)
5. **ADR-005:** Multi-cook household model (Phase 5)
6. **ADR-006:** Indian unit graph design (Phase 1)
7. **ADR-007:** RAGAS eval gate as release criterion (Phase 3)
8. **ADR-008:** Quick-commerce as deep-link hand-off (Phase 5)
9. **ADR-009:** Recipe crawl ethics (Phase 2)

## Testing

```bash
# Run isolated model, API and recipe-import tests (no database or model keys needed)
uv run pytest

# Run property-based tests (Hypothesis)
uv run pytest tests/test_inventory.py tests/test_phase1_exit.py -v
```

Provider calls and Atlas vector queries are replaced at their boundaries in these tests. A real-server and labeled-recipe evaluation is a separate gate; see [Phase 2 progress](docs/PHASE2_PROGRESS.md).

## Portfolio Highlights

This project demonstrates:
- **Python + FastAPI** — "Stack winning the AI race"
- **Pydantic AI agents** — Type-safe tools with structured outputs
- **Production RAG** — Hybrid retrieval, reranking, evals
- **MongoDB Atlas Vector + Search** — Single store with $scoreFusion
- **Multi-modal AI** — OCR, ASR, Vision LLM
- **Eval-driven dev** — RAGAS, Promptfoo, Inspect AI
- **Domain modeling** — Indian units, ingredients, regional taxonomy

## License

MIT

## Design Document

See the full design document at:
`C:\Users\aesir\Work\Projects\Full\Mimir\300 - Work\320 - Personal\322 - Idunn\Idunn-design.md`
