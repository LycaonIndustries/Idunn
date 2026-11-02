# Multimodal Recipe Vault (4 Streams & BYOK) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand Iðunn's Phase 1 Recipe Vault to support all 4 input capture streams (Text, Audio, Screenshots, Silent Video Reels) with zero-cost BYOK Google Gemini & OpenAI support alongside Anthropic, resolving settings validation conflicts.

**Architecture:** 
- Config settings updated with `extra="ignore"` and BYOK Gemini fields (`gemini_api_key`, `gemini_model`) so users can operate at zero cost without host API bills.
- Unified extraction provider abstraction in `recipe_providers.py` supporting Anthropic and Google Gemini (via async `httpx` with strict JSON schema mode).
- Four dedicated ingestion endpoints in `src/idunn/api/recipes.py`:
  1. `POST /api/v1/recipes/ingest?url=...` (Existing URL/JSON-LD)
  2. `POST /api/v1/recipes/ingest/text` (Existing text/WhatsApp paste)
  3. `POST /api/v1/recipes/ingest/image` (Screenshot/photo stream via multimodal vision)
  4. `POST /api/v1/recipes/ingest/audio` (Direct voice note/audio memo stream via Whisper/Gemini)
  5. `POST /api/v1/recipes/ingest/video` (Video reel stream with 1 fps `ffmpeg` frame extraction + multimodal vision)

**Tech Stack:** Python 3.13, FastAPI, Pydantic v2, `pydantic-settings`, `httpx`, `ffmpeg`, `faster-whisper`, MongoDB Atlas / mongomock-motor.

**Spec:** `C:\Users\aesir\Work\Projects\Full\Mimir\300 - Work\310 - Personal\312 - Idunn\Idunn-design.md` and `Phases.md`.

## Global Constraints

- Python >= 3.13 with strict type hints (`mypy strict`) and clean `ruff` formatting.
- Strict Pydantic JSON validation on all extracted recipe outputs (`title`, `prep_time`, `cook_time`, `ingredients`, `steps`).
- Zero unhandled extra environment variables crashing settings initialization (`extra="ignore"`).
- Temporary files (audio clips, extracted video frames) MUST be cleaned up in `finally` blocks.
- Bounded input sizes (max image 10 MB, max audio 50 MB, max video 100 MB).

## Review Focus

1. **Missing or invalid API keys:** If neither Gemini nor Anthropic key is configured, endpoints return HTTP 503 (`ProviderNotConfiguredError`).
2. **Corrupted or oversized media:** Oversized images, unsupported audio encodings, or invalid video containers return HTTP 400 with a clear error message.
3. **Silent videos:** Videos with no audio track gracefully route to visual frame sampling rather than failing with Whisper speech errors.
4. **Temporary file leakage:** Errors or cancellations during video frame extraction or audio transcription never leave abandoned files on disk.
5. **Optimistic review revision conflicts:** Recipe review updates maintain strict revision locking (HTTP 409 on stale revision).

---

### Task 1: Config Settings Resilience & Gemini BYOK Configuration

**Files:**
- Modify: `src/idunn/config.py`
- Modify: `.env.example`
- Test: `tests/test_config.py`

- [x] **Step 1: Write the failing test for settings loading with extra env vars and Gemini fields**
  - Create `tests/test_config.py` testing that `Settings` accepts `gemini_api_key`, `gemini_model`, `openai_api_key`, and ignores arbitrary external environment variables (like `extra_var="123"`).
- [x] **Step 2: Run test and verify failure**
  - Run `uv run pytest tests/test_config.py` and confirm failure.
- [x] **Step 3: Implement settings fixes in `config.py`**
  - In `src/idunn/config.py`: Add `extra="ignore"` to `SettingsConfigDict`.
  - Add `gemini_api_key: str | None = None`, `gemini_model: str = "gemini-2.5-flash"`, and `openai_api_key: str | None = None`.
  - Update `.env.example` with these fields.
- [x] **Step 4: Verify test passes**
  - Run `uv run pytest tests/test_config.py` and verify all tests pass.
- [x] **Step 5: Run existing test suite to verify baseline**
  - Run `uv run pytest tests/ -q` to confirm the full suite runs without `extra_forbidden` errors.
- [x] **Step 6: Git commit**
  - `git commit -am "feat: support Gemini BYOK config and ignore extra environment variables"`

---

### Task 2: Gemini Multimodal Recipe Extractor (Text & Vision)

**Files:**
- Modify: `src/idunn/services/recipe_providers.py`
- Modify: `src/idunn/services/ingest_errors.py`
- Test: `tests/test_gemini_provider.py`

- [x] **Step 1: Write unit tests for Gemini text & multimodal vision extraction**
  - Create `tests/test_gemini_provider.py` mocking `httpx.AsyncClient.post` for Gemini v1beta `generateContent`.
  - Test valid JSON recipe output parsing.
  - Test handling of API errors, rate limits (HTTP 429), and missing API keys.
- [x] **Step 2: Run tests and verify failure**
  - Run `uv run pytest tests/test_gemini_provider.py` and confirm failure.
- [x] **Step 3: Implement `GeminiRecipeExtractor` in `recipe_providers.py`**
  - Build `GeminiRecipeExtractor` using `httpx.AsyncClient`:
    - Endpoint: `https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}`
    - Configure `generationConfig`: `{"response_mime_type": "application/json"}`.
    - Support both plain text input and multimodal image parts (Base64 encoded with mime type).
  - Update `RecipeTextExtractor` to automatically use `GeminiRecipeExtractor` when `gemini_api_key` is present (defaulting to Anthropic if `gemini_api_key` is unset).
- [x] **Step 4: Verify tests pass**
  - Run `uv run pytest tests/test_gemini_provider.py` and ensure 100% pass rate.
- [x] **Step 5: Git commit**
  - `git commit -am "feat: implement Gemini multimodal recipe extractor with structured JSON schema"`

---

### Task 3: Screenshot & Cookbook Photo Stream (`POST /api/v1/recipes/ingest/image`)

**Files:**
- Create: `src/idunn/services/image_extract.py`
- Modify: `src/idunn/services/recipe_ingest.py`
- Modify: `src/idunn/api/recipes.py`
- Test: `tests/test_recipe_image_ingest.py`

- [x] **Step 1: Write integration tests for image recipe ingestion**
  - Create `tests/test_recipe_image_ingest.py`:
    - Test upload of valid PNG/JPEG recipe image.
    - Test rejection of oversized image (> 10 MB) and invalid MIME types.
    - Test end-to-end recipe creation and ingredient matching.
- [x] **Step 2: Run tests and verify failure**
  - Run `uv run pytest tests/test_recipe_image_ingest.py` and confirm failure.
- [x] **Step 3: Implement image extraction service and API route**
  - In `src/idunn/services/recipe_ingest.py`: Add `ingest_from_image(image_bytes, mime_type, source_name)`.
  - In `src/idunn/api/recipes.py`: Add route `POST /api/v1/recipes/ingest/image` accepting `UploadFile` (multipart/form-data).
- [x] **Step 4: Verify tests pass**
  - Run `uv run pytest tests/test_recipe_image_ingest.py` and ensure all tests pass.
- [x] **Step 5: Git commit**
  - `git commit -am "feat: implement image and screenshot recipe ingestion stream"`

---

### Task 4: Direct Audio & Voice Note Stream (`POST /api/v1/recipes/ingest/audio`)

**Files:**
- Modify: `src/idunn/services/recipe_providers.py`
- Modify: `src/idunn/services/recipe_ingest.py`
- Modify: `src/idunn/api/recipes.py`
- Test: `tests/test_recipe_audio_ingest.py`

- [x] **Step 1: Write tests for audio file upload & transcription**
  - Create `tests/test_recipe_audio_ingest.py`:
    - Test upload of WAV/MP3 voice recording.
    - Test transcription pipeline with mocked Whisper/Gemini ASR.
    - Test file cleanup of temporary audio files on both success and error.
- [x] **Step 2: Run tests and verify failure**
  - Run `uv run pytest tests/test_recipe_audio_ingest.py` and confirm failure.
- [x] **Step 3: Implement direct audio ingestion service and API route**
  - In `src/idunn/services/recipe_providers.py`: Implement `extract_audio` in `GeminiRecipeExtractor`.
  - In `src/idunn/services/recipe_ingest.py`: Add `ingest_from_audio(file_bytes, filename, source_name)`.
  - In `src/idunn/api/recipes.py`: Add route `POST /api/v1/recipes/ingest/audio` accepting `UploadFile`.
- [x] **Step 4: Verify tests pass**
  - Run `uv run pytest tests/test_recipe_audio_ingest.py` and confirm all tests pass.
- [x] **Step 5: Git commit**
  - `git commit -am "feat: implement direct audio and voice note recipe ingestion stream"`

---

### Task 5: Silent Video Reel Frame Sampling & Vision Extraction (`POST /api/v1/recipes/ingest/video`)

**Files:**
- Create: `src/idunn/services/video_frames.py`
- Modify: `src/idunn/services/recipe_providers.py`
- Modify: `src/idunn/services/recipe_ingest.py`
- Modify: `src/idunn/api/recipes.py`
- Test: `tests/test_recipe_video_ingest.py`

- [x] **Step 1: Write tests for video frame extraction and fallback**
  - Create `tests/test_recipe_video_ingest.py`:
    - Test video file ingestion with mocked frame extraction.
    - Test frame sampling (1 fps), keyframe selection, and multimodal prompt packaging.
    - Test guaranteed cleanup of extracted frame directory on error/completion.
- [x] **Step 2: Run tests and verify failure**
  - Run `uv run pytest tests/test_recipe_video_ingest.py` and confirm failure.
- [x] **Step 3: Implement video frame extractor and API route**
  - In `src/idunn/services/video_frames.py`: Use `ffmpeg` to extract 1 frame per second into a temporary directory; select up to 15 evenly-spaced representative frames; send as multimodal image array to Gemini/Claude Vision.
  - In `src/idunn/services/recipe_ingest.py`: Add `ingest_from_video(file_bytes, filename, source_name)`.
  - In `src/idunn/api/recipes.py`: Add route `POST /api/v1/recipes/ingest/video` accepting `UploadFile`.
- [x] **Step 4: Verify tests pass**
  - Run `uv run pytest tests/test_recipe_video_ingest.py` and confirm all tests pass.
- [x] **Step 5: Git commit**
  - `git commit -am "feat: implement silent video reel frame extraction and recipe ingestion"`

---

### Task 6: Full Regression & Verification

**Files:**
- Modify: `docs/PHASE2_PROGRESS.md`
- Run: Full test suite

- [x] **Step 1: Run complete test suite**
  - Run `uv run pytest tests/ -q` across all existing and new test modules (124 passed).
- [x] **Step 2: Check formatting and types**
  - Run `uv run ruff check` on new/modified modules (all checks passed).
- [x] **Step 3: Update documentation with API usage examples**
  - Update `docs/PHASE2_PROGRESS.md` documenting the `/ingest/image`, `/ingest/audio`, and `/ingest/video` endpoints.
- [x] **Step 4: Git commit**
  - `git commit -am "docs: update progress and documentation for multimodal recipe streams"`
