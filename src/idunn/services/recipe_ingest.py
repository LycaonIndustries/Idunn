"""Recipe ingest service for Iðunn.

Handles multi-source recipe ingestion:
1. JSON-LD parsing (scrape-schema-recipe)
2. Blog scraping with Readability + LLM fallback
3. YouTube transcript extraction (yt-dlp + Whisper)
4. Ingredient normalization with embedding match
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class IngestSource(str, Enum):
    """Recipe source types."""

    JSON_LD = "json-ld"
    BLOG = "blog"
    YOUTUBE = "youtube"
    MANUAL = "manual"


class IngestResult(BaseModel):
    """Result of recipe ingestion."""

    model_config = {"arbitrary_types_allowed": True}

    success: bool
    recipe_id: Optional[str] = None
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    message: str = ""
    warnings: list[str] = Field(default_factory=list)


class RecipeIngestService:
    """Service for ingesting recipes from various sources."""

    def __init__(self, db, anthropic_client=None, embedding_model=None):
        self.db = db
        self.anthropic_client = anthropic_client
        self.embedding_model = embedding_model

    async def ingest_from_url(self, url: str) -> IngestResult:
        """Ingest a recipe from a URL.

        Tries in order:
        1. JSON-LD parsing (fastest, most reliable)
        2. Blog scraping with Readability
        3. YouTube transcript (if YouTube URL)
        4. LLM extraction fallback
        """
        warnings: list[str] = []

        # Try JSON-LD first (~70% success rate, zero LLM cost)
        recipe_data = await self._try_json_ld(url)
        if recipe_data:
            # Normalize ingredients
            normalized_ids, norm_warnings = await self._normalize_ingredients(
                recipe_data.get("ingredients", [])
            )
            recipe_data["normalized_ingredients"] = normalized_ids
            warnings.extend(norm_warnings)

            # Generate embedding
            embedding = await self._generate_embedding(recipe_data)
            recipe_data["embedding"] = embedding

            # Store in MongoDB
            recipe_data["ingest_source"] = IngestSource.JSON_LD.value
            recipe_data["ingest_confidence"] = recipe_data.get(
                "ingest_confidence", 0.9
            )

            recipe_id = await self._store_recipe(recipe_data)
            return IngestResult(
                success=True,
                recipe_id=recipe_id,
                confidence=recipe_data["ingest_confidence"],
                message="Recipe ingested via JSON-LD",
                warnings=warnings,
            )

        # TODO: Implement other methods
        warnings.append("JSON-LD extraction failed, other methods not yet implemented")

        return IngestResult(
            success=False,
            message="Recipe ingest failed. JSON-LD extraction failed.",
            warnings=warnings,
        )

    async def _try_json_ld(self, url: str) -> Optional[dict]:
        """Try to extract recipe using JSON-LD.

        Uses scrape-schema-recipe library.
        ~70% success rate for modern recipe sites.
        """
        try:
            from scrape_schema_recipe import scrape_url

            # scrape_url is synchronous, run in thread pool
            import asyncio

            loop = asyncio.get_event_loop()
            recipes = await loop.run_in_executor(None, scrape_url, url)

            if not recipes or len(recipes) == 0:
                return None

            # Take the first recipe found
            recipe = recipes[0]

            # Map to our schema
            return {
                "title": recipe.get("name", ""),
                "description": recipe.get("description"),
                "ingredients": [
                    {"name": ing, "quantity": None, "unit": None}
                    for ing in recipe.get("recipeIngredient", [])
                ],
                "steps": [
                    {
                        "step_number": i + 1,
                        "instruction": step.get("text", "")
                        if isinstance(step, dict)
                        else str(step),
                    }
                    for i, step in enumerate(recipe.get("recipeInstructions", []))
                ],
                "prep_time_minutes": self._parse_duration(
                    recipe.get("prepTime")
                ),
                "cook_time_minutes": self._parse_duration(
                    recipe.get("cookTime")
                ),
                "servings": self._extract_servings(recipe.get("recipeYield")),
                "image_url": recipe.get("image"),
                "source_url": url,
                "source_name": recipe.get("source"),
                "ingest_source": IngestSource.JSON_LD.value,
                "ingest_confidence": 1.0 if recipe.get("name") else 0.5,
            }

        except Exception as e:
            # Log error and return None
            print(f"JSON-LD extraction failed: {e}")
            return None

    def _parse_duration(self, duration_str: Optional[str]) -> Optional[int]:
        """Parse ISO 8601 duration (PT30M) to minutes."""
        if not duration_str:
            return None
        # Simple parser for PT{H}H{M}M format
        import re

        match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?", duration_str)
        if match:
            hours = int(match.group(1) or 0)
            minutes = int(match.group(2) or 0)
            return hours * 60 + minutes
        return None

    def _extract_servings(self, yield_str: Optional[str]) -> Optional[int]:
        """Extract servings from recipeYield (e.g., '4 servings' -> 4)."""
        if not yield_str:
            return None
        import re

        match = re.search(r"(\d+)", str(yield_str))
        if match:
            return int(match.group(1))
        return None

    async def _try_blog_scrape(self, url: str) -> Optional[dict]:
        """Scrape blog post and extract recipe.

        Uses Readability to extract main content,
        then LLM to structure the recipe.
        """
        # TODO: Implement blog scraping
        # 1. Fetch HTML with httpx
        # 2. Extract main content with readability
        # 3. Use LLM to extract structured recipe
        return None

    async def _try_youtube(self, url: str) -> Optional[dict]:
        """Extract recipe from YouTube video.

        Uses yt-dlp to download audio,
        Whisper to transcribe,
        LLM to extract structured recipe.
        """
        # TODO: Implement YouTube ingest
        # 1. Download audio with yt-dlp
        # 2. Transcribe with Whisper (faster-whisper)
        # 3. Extract recipe with LLM
        return None

    async def _normalize_ingredients(
        self, ingredients: list[dict]
    ) -> tuple[list[str], list[str]]:
        """Normalize ingredient names to canonical forms.

        Uses embedding match against ingredients collection.
        Falls back to fuzzy matching.
        Returns (normalized_ingredient_ids, warnings).
        """
        # TODO: Implement ingredient normalization
        # 1. For each ingredient, generate embedding
        # 2. Vector search in ingredients collection
        # 3. If match confidence > threshold, use it
        # 4. Otherwise, add to manual review queue
        return [], []

    async def _generate_embedding(self, recipe: dict) -> list[float]:
        """Generate embedding for recipe (title + ingredients + steps).

        Uses Voyage AI or local BGE-M3.
        """
        # TODO: Implement embedding generation
        # 1. Combine title, ingredients, steps into text
        # 2. Call embedding API (Voyage or local)
        # 3. Return vector
        return []

    async def _store_recipe(self, recipe: dict) -> str:
        """Store recipe in MongoDB.

        Returns the inserted recipe ID.
        """
        collection = self.db[COLLECTION_RECIPES]
        result = await collection.insert_one(recipe)
        return str(result.inserted_id)
