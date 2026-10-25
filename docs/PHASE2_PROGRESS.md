# Phase 2 — Recipe import

Updated: 2026-10-07. Status: import and review implementation built; live service and corpus checks still open.

## Built

- URL imports fetch bounded HTML, parse schema.org recipes with `scrape-schema-recipe`, and handle sectioned steps, fractions, durations, serving lists, image objects and source credit.
- Non-structured blogs use Readability and Claude structured extraction. Pasted recipe text uses the same validated extraction path.
- YouTube videos use a separate, time-limited yt-dlp/Whisper process before Claude extraction. Playlists and live videos are rejected. Audio is temporary and is removed after success, failure, timeout or cancellation.
- Exact ingredient names and regional synonyms are matched first. Configured Voyage embeddings feed Atlas vector matching for unresolved names. Low scores and near-tied candidates remain suggestions for review.
- Every ingredient retains its row number, confirmed ID or suggestion, score and review state. Recipe and review data are stored together. Missing embedding configuration is reported and does not discard a usable recipe.
- Review endpoints support confirming, changing or ignoring matches and approving uncertain extraction. Revision checks reject stale reviews with HTTP 409. Editing a recipe's ingredients clears old links; changing recipe text clears the old embedding. Editing canonical ingredient names or synonyms clears their old vectors.
- Recipe create/update timestamps, explicit field clearing, stored-document validation, and database-error responses are fixed. Shared validation now includes recipes and a review-queue index.
- Atlas search setup and canonical ingredient embedding backfill have an explicit command. They do not run automatically on startup.
- The full API checks also found a pre-existing pantry bug: finishing an item stored zero but the model rejected it. Zero is now valid for consumed stored items; new items still require a positive quantity.

## API

| Method | Path | Result |
|---|---|---|
| POST | `/api/v1/recipes` | Create a recipe, HTTP 201 |
| GET | `/api/v1/recipes` | List/filter recipes |
| GET | `/api/v1/recipes/{id}` | Read a recipe |
| PATCH | `/api/v1/recipes/{id}` | Edit a recipe, invalidate stale derived data |
| DELETE | `/api/v1/recipes/{id}` | Delete a recipe |
| POST | `/api/v1/recipes/ingest?url=...` | Import and store a recipe, HTTP 201 |
| POST | `/api/v1/recipes/ingest/text` | Import `{ "text": "...", "source_name": "..." }`, HTTP 201 |
| GET | `/api/v1/recipes/review` | List recipes needing review |
| POST | `/api/v1/recipes/{id}/review` | Apply decisions at a given revision |

The URL endpoint now returns **201 after storage**, replacing the old misleading 202 response. It is a request/response operation, not an asynchronous job acknowledgment. Durable Arq dispatch and polling remain a follow-up, particularly before bulk video imports.

Example review payload:

```json
{
  "revision": 0,
  "decisions": [
    {"ingredient_index": 0, "ingredient_id": "<canonical ingredient ObjectId>"},
    {"ingredient_index": 1, "ignore": true}
  ],
  "approve_extraction": true
}
```

Row numbers start at zero. A partial review keeps remaining uncertain rows in the queue. Ignoring a row does not remove the ingredient from the recipe.

## Configuration and run steps

1. Install project dependencies with Python 3.13 (`uv sync --python 3.13`). Configure a development MongoDB database using `.env.example` as the field list.
2. Set `ANTHROPIC_API_KEY` for blog, pasted-text and video extraction. Structured website recipes do not require it.
3. Set `VOYAGE_API_KEY` for embeddings. Add canonical ingredients through the ingredient API before judging match accuracy.
4. On an Atlas cluster that supports vector search, run `uv run python -m idunn.db.recipe_search_indexes --create-indexes`, then wait for the indexes to be ready. Run `uv run python -m idunn.db.recipe_search_indexes --embed-ingredients` to create canonical vectors; this second command calls the paid embedding service. Re-run after changing the ingredient master or embedding model/dimensions.
5. For videos, use a cached multilingual Whisper model via `WHISPER_MODEL`. `WHISPER_LOCAL_FILES_ONLY=true` prevents an unexpected model download; set it false only when a download is intended.
6. Start the API with `uv run uvicorn idunn.main:app --reload`. Use `/docs` to import and review recipes.

Input limits are configurable: 2 MB HTML, 60,000 text characters, 30-second website timeout, 30-minute videos, 100 MB audio and a 15-minute video-worker timeout. Unsupported content and fetch errors return 400; invalid extraction returns 422; missing provider setup returns 503; model-service failure returns 502; database failure returns 503.

## Verification

- `pytest -q --tb=short`: **107 passed**. Includes the 26 existing inventory model/property tests, isolated API CRUD checks, real structured-data parsing, provider boundary checks, regional and vector matching, review conflicts, stale-vector invalidation and video timeout cleanup.
- API tests use an isolated in-memory MongoDB substitute. They do not connect to the configured application database. Atlas search and external providers are mocked at their boundaries.
- OpenAPI generation passes and includes all six recipe route paths. The Atlas setup command's help path loads successfully.
- Ruff passes on the changed recipe/config/schema/service modules and the new recipe tests. `git diff --check` passes.
- A read-only HTTPS fetch of `https://example.com` passed through the actual bounded fetcher, including checked-address connection and TLS hostname handling. This was not a recipe accuracy or model-service test.
- The test run still reports existing `datetime.utcnow()` deprecation warnings in the older inventory code.
- The old project `.venv` references a missing interpreter. This session verified with Python 3.13.5 in `C:\Users\aesir\AppData\Local\Temp\opencode\idunn-phase2-venv`; the old environment was left intact.

## Open gates

- A read-only setup check found no configured Anthropic key, no configured Voyage key, and no reachable configured MongoDB server. No paid model calls or application-database writes were made during this build.
- Real MongoDB validator and Atlas index checks are pending. Mock tests do not verify those server features.
- YouTube/Whisper is wired and its surrounding flow is tested with a transcript substitute; a real multilingual audio run is pending.
- The design's **100 mixed recipes with at least 90% ingredient-match accuracy** has not been run. It needs approved live-provider access, a populated canonical ingredient master, and human-labeled expected matches. The old May note incorrectly used checked boxes for these exit targets; they were not verified results.
- A frontend review screen, durable import jobs and the Phase 3 retrieval/meal-planning work remain later milestones.

Build plan: [Recipe import build plan](recipe-import-build-plan.md).
