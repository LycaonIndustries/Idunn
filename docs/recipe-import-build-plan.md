# Recipe import build plan

Date: 2026-10-07. Approved direction: resume the existing Idunn plan, starting with Phase 2 recipe import.

## Goal

Make a recipe import produce a valid, readable recipe with source credit, ingredient links, an embedding when configured, and a review state for uncertain matches. Follow the May design: structured website data first; Readability plus Claude for blogs; yt-dlp plus Whisper plus Claude for YouTube; Voyage embeddings as already configured in this repo.

## Flow

1. Restore a working Python 3.13 test environment in the approved temporary directory. The existing `.venv` refers to an interpreter that no longer exists. Keep the existing environment intact.
2. Repair recipe create/update timestamps and MongoDB validation. Validate imported recipes before writing and retain their source URL and name.
3. Extract website JSON-LD, falling back to readable article text and structured model output. Support pasted text and YouTube audio transcription. Bound source size, download duration, timeouts, and redirects. Return useful errors for inaccessible or unsupported sources.
4. Match ingredient names and regional synonyms first; use embeddings for unresolved names when configured. Retain a match for each recipe ingredient so quantities and uncertain suggestions do not lose their position. Embed the whole recipe when configured.
5. Save uncertain matches on the recipe itself. List recipes waiting for review and allow a person to confirm or replace matches. Derive the flat ingredient-ID list from confirmed matches in the same document update.
6. Test recipe CRUD, source parsing, matching, review decisions, schema setup, missing providers, and failed imports with isolated data and mocked external services. Update the build notes with actual results and open gates.

## Files and size

- `src/idunn/models/recipe.py`: recipe documents, ingredient matches, review input (about 100 added/changed lines).
- `src/idunn/services/recipe_ingest.py`: typed pipeline, storage, match/review results (about 200–300 lines).
- New source/provider/matching modules under `src/idunn/services/`: website parsing, blog/YouTube/text extraction, embeddings and name matching (about 500–700 lines total).
- `src/idunn/api/recipes.py`: CRUD repairs, imports and review endpoints (about 150–250 changed lines).
- `src/idunn/db/schemas.py`, `src/idunn/main.py`: enable recipe validation, add review index, surface database failures (about 80–120 changed lines).
- `src/idunn/api/ingredients.py`: invalidate cached vectors when canonical names or synonyms change; the explicit backfill command rebuilds them from a checked source snapshot.
- `src/idunn/config.py`, `.env.example`, `pyproject.toml`, `uv.lock`: provider settings, input limits and dependencies.
- `tests/`: isolated recipe API and pipeline regression tests (about 400–600 lines); reuse Phase 1 checks.
- `docs/recipe-import-build-plan.md`, `docs/PHASE2_PROGRESS.md`, `README.md`: plan, run steps, verified progress and remaining checks.

## Failure cases

- Invalid URL, non-public URL, unsupported content, oversized response, redirects, fetch timeout: reject without creating a recipe.
- Empty/malformed JSON-LD: try the blog extraction path; invalid model output never reaches storage.
- Missing extraction key: structured JSON-LD still works; text/blog/YouTube extraction returns a clear setup error.
- Missing embedding key: preserve the recipe and exact matches; mark uncertain rows for review and report that embeddings were skipped. Provider outages are reported separately from unconfigured providers.
- Missing ingredient master or ambiguous synonyms: retain the original ingredient text and queue review instead of silently guessing a canonical ID.
- Database failure: do not report a successful import or review. Review updates use a revision check to avoid overwriting someone else's decision.
- YouTube failure or timeout: report the failure and remove temporary audio files. Do not claim a language or accuracy result from mocked tests.

## Checks and completion gates

### Adjustment after the first full test run

The 26 original model/property tests pass. Isolated API tests exposed an existing pantry error: consuming an entire item stores zero, while `Item` and the shared items validator reject zero. Since this build enables the shared validators at startup, keep that existing API usable by allowing zero only for consumed stored items, retaining positive quantities for create/update requests. This adds a small change in `models/inventory.py`, the items JSON schema, and the consume endpoint's stored number type, plus a regression check. The first new recipe-test failures were mock-target errors; repair the test boundary before changing production behavior.

- Run existing inventory model/property tests, then isolated recipe API/pipeline tests and lint on changed Python files.
- Exercise MongoDB validators against a real disposable database when the database runtime is available. Mocked database tests do not prove MongoDB validation or Atlas search support.
- The 100-recipe, at-least-90% ingredient-match gate remains open until a labeled source set, running MongoDB, and paid-provider access are available and the live run is approved.
- Keep the current request/response import shape for this build and return success only after storage. Durable Arq job dispatch/polling, bulk crawling, and Phase 3 retrieval are separate follow-ups; do not label Phase 2 fully complete while its live gate is open.
