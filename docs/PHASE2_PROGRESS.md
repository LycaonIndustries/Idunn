# Phase 2 Progress Summary — Recipe Ingest

**Date**: 2026-05-07  
**Status**: 🚧 IN PROGRESS

---

## Completed (Phase 2 Start)

### 1. Recipe Pydantic Models
- **`Recipe`** — Complete recipe document with title, ingredients, steps, nutrition
- **`RecipeCreate`** — Creation payload
- **`RecipeUpdate`** — Partial update payload
- **`IngredientItem`** — Ingredient in recipe with quantity, unit, optional flag
- **`Step`** — Recipe step with step number, instruction, time
- **`NutritionInfo`** — Per-serving nutrition (calories, protein, carbs, fat)
- **Enums**: `Region`, `CuisineType`, `Difficulty`

### 2. Recipe API Routes (FastAPI)
**Recipes** (`/api/v1/recipes`):
- `POST /` — Create recipe (201)
- `GET /` — List recipes with filters (query, region, cuisine_type, tags)
- `GET /{recipe_id}` — Get single recipe
- `PATCH /{recipe_id}` — Update recipe
- `DELETE /{recipe_id}` — Delete recipe
- `POST /ingest?url=X` — Ingest recipe from URL (202 Accepted)

### 3. Recipe JSON Schema (MongoDB Validation)
- Added `RECIPES_SCHEMA` to `db/schemas.py`
- Includes validation for all recipe fields
- Supports nested ingredients and steps arrays
- Embedding field for vector search

### 4. RecipeIngestService Skeleton
- **`RecipeIngestService`** class with methods:
  - `ingest_from_url(url)` — Main entry point
  - `_try_json_ld(url)` — JSON-LD extraction (scrape-schema-recipe)
  - `_try_blog_scrape(url)` — Blog scraping + LLM fallback
  - `_try_youtube(url)` — YouTube transcript (yt-dlp + Whisper)
  - `_normalize_ingredients(ingredients)` — Embedding match against ingredients collection
  - `_generate_embedding(recipe)` — Generate recipe embedding
  - `_store_recipe(recipe)` — Store in MongoDB

### 5. Dependencies Added
- `scrape-schema-recipe` — JSON-LD recipe extraction
- `yt-dlp` — YouTube audio download
- `faster-whisper` — Local Whisper for transcription
- `anthropic` — LLM for extraction/repair

---

## Remaining (Phase 2 Implementation)

### High Priority
1. **Implement JSON-LD parsing** (`_try_json_ld`)
   - Use `scrape_schema_recipe.scrape_url()`
   - Handle missing fields with LLM repair

2. **Implement blog scraping** (`_try_blog_scrape`)
   - Fetch HTML with `httpx`
   - Extract main content with `readability-lxml`
   - Use Anthropic LLM to structure recipe

3. **Implement YouTube ingest** (`_try_youtube`)
   - Download audio with `yt-dlp`
   - Transcribe with `faster-whisper` (local, free)
   - Extract recipe with LLM

4. **Implement ingredient normalization** (`_normalize_ingredients`)
   - Generate embedding for each ingredient name
   - Vector search in `ingredients` collection
   - Return normalized IDs + confidence scores

5. **Generate recipe embeddings** (`_generate_embedding`)
   - Combine title + ingredients + steps into text
   - Use Voyage AI or local BGE-M3
   - Store in `embedding` field

### Medium Priority
6. **Add MongoDB Atlas Vector + Search indices** for recipes
7. **Create manual review queue** for low-confidence ingests
8. **Add tests for Phase 2**:
   - Test JSON-LD parsing with sample URLs
   - Test ingredient normalization accuracy
   - Test ingest API endpoint

### Exit Criteria (from Design Doc)
- ✅ Ingest 100 mixed recipes
- ✅ Sources: Hebbar's Kitchen, NDTV Food, Sanjeev Kapoor blog, Nisha Madhulika YouTube
- ✅ ≥90% ingredient-match accuracy

---

## Tech Stack (Phase 2)

| Layer | Choice | Purpose |
|-------|--------|---------|
| JSON-LD Parsing | scrape-schema-recipe | Extract from modern recipe sites |
| Blog Scraping | httpx + readability-lxml | Extract main content |
| YouTube | yt-dlp + faster-whisper | Download audio + transcribe |
| LLM Extraction | Anthropic (Haiku 4.5) | Structure unstructured text |
| Embeddings | Voyage AI or BGE-M3 | Recipe + ingredient vectors |
| Vector Search | MongoDB Atlas Vector Search | Semantic recipe retrieval |

---

## Decisions Made (Phase 2)

### 1. Why JSON-LD First?
- **~70% success rate** for modern recipe sites
- **Zero LLM cost** — deterministic parsing
- **Fast** — no API calls needed

### 2. Why `faster-whisper` over `openai-whisper`?
- **Local** — no API costs
- **Fast** — optimized with CTranslate2
- **Multilingual** — supports Hindi/Tamil/Telugu

### 3. Why Anthropic Haiku 4.5 for extraction?
- **Cost-effective** — cheap for high-volume parsing
- **Structured output** — Pydantic-compatible
- **Prompt caching** — reduces costs for repeated patterns

---

## Next Steps (Phase 2 Continuation)

### Immediate
1. Implement `_try_json_ld` with `scrape_schema_recipe`
2. Add sample recipe URLs for testing
3. Implement `_try_blog_scrape` with `readability-lxml` + Anthropic
4. Test with Hebbar's Kitchen URL

### After Basic Ingest Works
5. Implement `_try_youtube` with `yt-dlp` + `faster-whisper`
6. Implement `_normalize_ingredients` with vector search
7. Implement `_generate_embedding` with Voyage AI
8. Create manual review queue for low-confidence ingests

### Testing
9. Create `test_recipe_api.py` — Test CRUD operations
10. Create `test_recipe_ingest.py` — Test ingest pipeline
11. Ingest 100 recipes and verify ≥90% ingredient-match accuracy

---

## Git History (Phase 2)

```
934a65f feat: add Recipe model and API routes (Phase 2 start)
16884e8 feat: add RecipeIngestService skeleton (Phase 2)
```

---

**Phase 2 is in progress. Continuing implementation...**
