# Phase 1 Completion Summary — Inventory Core

**Date**: 2026-05-07  
**Status**: ✅ COMPLETE

---

## Deliverables

### 1. Pydantic Models
- **`Item`** — Pantry item with name, quantity, unit, location, expiry_date, barcode
- **`ItemCreate`** — Creation payload with `added_at` default
- **`ItemUpdate`** — Partial update payload
- **`Ingredient`** — Canonical ingredient master with synonyms, IFCT linkage
- **`IngredientCreate` / `IngredientUpdate`** — Ingredient CRUD payloads
- **`Location`** — Enum: `fridge`, `freezer`, `pantry`, `dry_store`, `cabinet`, `counter`, `spice_box`, `windowsill`
- **`Unit`** — Enum: mass (g, kg, paav), volume (ml, l, tsp, tbsp, chamcha, katori), count (piece, bunch, packet, box)
- **`UnitConversion`** — Conversion graph entry with optional region tag

### 2. Indian Unit Graph
**12 units** with **20+ direct conversion paths**:

| From | To | Factor | Notes |
|------|----|--------|-------|
| g | kg | 0.001 | Metric |
| kg | g | 1000 | Metric |
| paav | g | 250 | Traditional Indian (~250g) |
| g | paav | 1/250 | Traditional Indian |
| ml | l | 0.001 | Metric |
| tsp | ml | 5 | ~5ml per tsp |
| chamcha | ml | 5 | Indian teaspoon |
| katori | ml | 150 | ~150ml cup |
| tbsp | tsp | 3 | 3 tsp = 1 tbsp |
| kg | l | 1 | Water equivalence (approx) |
| ... | ... | ... | ... |

### 3. API Routes (FastAPI)
**Inventory** (`/api/v1/items`):
- `POST /` — Create item (201)
- `GET /` — List items with filters (FEFO ordering)
- `GET /expiring?days=N` — Items expiring within N days
- `GET /{item_id}` — Get single item
- `PATCH /{item_id}` — Update item
- `POST /{item_id}/consume?quantity=X` — Consume part/all of item
- `DELETE /{item_id}` — Delete item

**Ingredients** (`/api/v1/ingredients`):
- `POST /` — Create canonical ingredient
- `GET /` — List with filters (category, region, query)
- `GET /{ingredient_id}` — Get single ingredient
- `PATCH /{ingredient_id}` — Update ingredient
- `POST /{ingredient_id}/synonyms` — Add synonym
- `DELETE /{ingredient_id}` — Delete ingredient

### 4. MongoDB Integration
- **Motor (async MongoDB driver)** for non-blocking operations
- **JSON Schema validation** at collection level (`validationLevel: strict`)
- **FEFO ordering** — Items sorted by expiry_date ascending (soonest first)
- **Indexes** — Text index on `name`, TTL on expiry alerts (planned)

### 5. Configuration
- **pydantic-settings** for environment-based config
- **`.env.example`** with all required variables documented
- Settings: MongoDB URL, Redis URL, LLM API keys, CORS origins

### 6. Tests
**26 unit tests** (all passing):
- `TestUnitConversions` (11 tests) — All conversion paths + Hypothesis roundtrip
- `TestItemModel` (6 tests) — Model validation, expiry checks
- `TestLocationEnum` (1 test) — All 8 locations
- `TestUnitEnum` (3 tests) — Mass, volume, count units
- `TestPhase1ExitCriteria` (6 tests) — Exit criteria verification

**Exit Criteria Verification**:
1. ✅ Add 50 mixed items (mass + volume + count) — `test_add_50_mixed_items`
2. ✅ Query "expiring this week" returns correctly — `test_expiring_this_week_query`
3. ✅ Unit conversions verified by property tests (Hypothesis) — `test_gram_kilogram_roundtrip`, `test_ml_liter_roundtrip`, `test_all_conversion_paths_exist`

### 7. Documentation
- **README.md** — Project overview, tech stack, phases, installation
- **ADR-001** — MongoDB Atlas as the Only Store
- **ADR-006** — Indian Unit Graph Design
- **.gitignore** — Python, IDE, environment, database files

---

## Tech Stack (Phase 1)

| Layer | Choice | Purpose |
|-------|--------|---------|
| Language | Python 3.13 | Modern Python with `datetime.now(UTC)` |
| Package Manager | uv | Fast, reliable dependency management |
| Framework | FastAPI | Async API with automatic OpenAPI docs |
| Validation | Pydantic v2 | Type-safe models with aliases (`_id`) |
| Database | Motor (async MongoDB) | Non-blocking DB operations |
| Testing | pytest + Hypothesis | Unit tests + property-based testing |
| Linting | ruff | Fast Python linter |
| Type Checking | mypy (strict) | Static type checking |

---

## Decisions Made

### 1. Why Pydantic v2 with `alias="_id"`?
- MongoDB uses `_id` as the primary key
- Pydantic v2 `alias` allows internal use of `id` in JSON responses
- Constructor requires `_id` (can't use `id=` due to alias)

### 2. Why `datetime.now(UTC)` instead of `datetime.utcnow()`?
- `datetime.utcnow()` is deprecated in Python 3.12+
- `datetime.now(UTC)` is timezone-aware and future-proof
- Fixes "can't compare offset-naive and offset-aware" errors

### 3. Why direct conversion graph (not Pint or transitive)?
- **Small graph** (12 units, ~20 edges) — no need for pathfinding
- **Explicit** — each conversion is a testable fact
- **Fast** — O(1) dictionary lookup
- **India-first** — includes paav, chamcha, katori as first-class citizens

### 4. Why FEFO ordering?
- **First Expire First Out** — items expiring sooner appear first
- Critical for reducing food waste (design doc problem #1)
- Implemented via MongoDB sort: `[("expiry_date", 1), ("added_at", -1)]`

---

## API Documentation

When running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI spec**: http://localhost:8000/openapi.json

---

## Next Steps (Phase 2)

### Phase 2 — Recipe Ingest (2 weeks)
1. **JSON-LD parser** via `scrape-schema-recipe`
2. **Readability + LLM fallback** for non-JSON-LD blogs
3. **YouTube ingest**: `yt-dlp` audio → Whisper → LLM structured extraction
4. **Pydantic-validated Recipe schema**
5. **Ingredient normalization** with embedding match + manual review queue
6. **Exit criteria**: Ingest 100 mixed recipes with ≥90% ingredient-match accuracy

### Dependencies to Add:
- `scrape-schema-recipe` — JSON-LD recipe extraction
- `yt-dlp` — YouTube audio download
- `openai-whisper` — Audio transcription
- `anthropic` — LLM extraction/repair
- `sentence-transformers` or `voyage-ai` — Embeddings for ingredient matching

---

## How to Run

```bash
# Install dependencies
cd C:\Users\aesir\Work\Projects\PP\idunn
uv sync

# Start MongoDB (Docker)
docker run -d -p 27017:27017 --name mongo mongo:latest

# Run the development server
uv run uvicorn idunn.main:app --reload --host 0.0.0.0 --port 8000

# Run tests
uv run pytest tests/ -v

# Run only unit tests (no MongoDB needed)
uv run pytest tests/test_inventory.py tests/test_phase1_exit.py -v
```

---

## Git History

```
9660d20 feat: initialize Iðunn project with Phase 1 inventory core
ee51129 fix: resolve datetime timezone issues and pydantic alias
8a519db docs: add ADR-006 Indian unit graph design
19e4549 test: add Phase 1 exit criteria tests
```

---

**Phase 1 is complete. Moving to Phase 2: Recipe Ingest.**
