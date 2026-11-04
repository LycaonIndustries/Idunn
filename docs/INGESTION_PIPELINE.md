# Multimodal Ingestion Pipeline

Iðunn features a multi-source ingestion pipeline tailored to real-world Indian household cooking workflows, where recipes exist across YouTube videos, Instagram reels, WhatsApp text forwards, printed books, and websites.

---

## Ingest Channels

```
                           ┌────────────────────────┐
                           │   Input Recipe Data    │
                           └───────────┬────────────┘
                                       │
     ┌──────────────┬──────────────────┼──────────────────┬──────────────┐
     ▼              ▼                  ▼                  ▼              ▼
┌─────────┐   ┌───────────┐      ┌───────────┐      ┌───────────┐  ┌───────────┐
│ YouTube │   │ Web / Blog│      │ Cookbook  │      │ Audio /   │  │ Silent    │
│ URL     │   │ URL       │      │ Photo     │      │ Memo      │  │ Video Reel│
└────┬────┘   └─────┬─────┘      └─────┬─────┘      └─────┬─────┘  └─────┬─────┘
     │              │                  │                  │              │
     │ yt-dlp       │ Schema.org       │ base64 JPEG      │ Whisper /    │ ffmpeg 1fps
     │ ASR          │ + Readability    │ vision           │ Gemini ASR   │ keyframes
     ▼              ▼                  ▼                  ▼              ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                    Structured JSON Extraction & Normalization                │
│                                                                              │
│  - Extraction Schema: title, ingredients, steps, servings, cuisine, tags     │
│  - Photo Extraction: meta og:image, twitter:image, yt-thumbnail, data URIs   │
│  - Nutritional Macro Calculation: calories, protein, carbs, fat, fiber       │
│  - Indian Unit Graph: katori, chamcha, paav, pinch                           │
│  - Ingredient Embedding Match: Voyage AI / string synonym lookup             │
└──────────────────────────────────────┬───────────────────────────────────────┘
                                       │
                                       ▼
                     ┌───────────────────────────────────┐
                     │ Saved to Vault (Supabase / Mongo) │
                     └───────────────────────────────────┘
```

---

## 1. Web & Blog Ingest
- **Structured Schema.org Recipes**: Evaluated first via `scrape-schema-recipe` to extract title, ingredients, prep/cook times, servings, and Schema.org `nutrition`.
- **OpenGraph & Twitter Cards**: If the recipe markup lacks an explicit photo, `extract_meta_image` parses `<meta property="og:image">` or `<meta name="twitter:image">`.
- **Readability + LLM Fallback**: Non-standard recipe pages are distilled with `readability-lxml` and passed to Google Gemini / Claude with strict JSON schema enforcement.

## 2. YouTube Video Ingest
- Audio tracks are extracted via `yt-dlp` and transcribed using Whisper.
- Video thumbnail is automatically resolved from the 11-character video ID (`https://img.youtube.com/vi/{id}/hqdefault.jpg`).

## 3. Multimodal Vision & Image Ingest
- Direct camera captures or screenshots of cookbook pages and notes are converted to inline base64 and analyzed with Gemini Vision.
- The captured image is preserved as a high-fidelity image URI stored directly with the recipe document.

## 4. Silent Video Reels
- Video files (Instagram/YouTube shorts) without audible narration are sampled at 1 fps using `ffmpeg` to extract keyframes.
- Keyframes are fed to Gemini Multimodal Vision to reconstruct step-by-step cooking procedures and capture initial dish presentation.

## 5. Nutritional Information Engine
- Each ingested recipe captures:
  - **Calories** (kcal per serving)
  - **Protein** (grams)
  - **Carbohydrates** (grams)
  - **Total Fat** (grams)
  - **Dietary Fiber** (grams)
- The React UI dynamically recalculates macro values according to the active serving scaler (`0.5×`, `1×`, `2×`, `4×`).
