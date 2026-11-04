"""Source extraction, ingredient matching, validation, and atomic recipe storage."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bson import ObjectId
from pydantic import BaseModel, Field, ValidationError

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

    from ..config import Settings

from ..config import settings
from ..db import COLLECTION_RECIPES
from ..models.recipe import IngredientMatch, Recipe
from .ingest_errors import ExtractionError, ProviderNotConfiguredError
from .ingredient_matching import IngredientMatcher
from .recipe_providers import ExtractedRecipe, GeminiRecipeExtractor, VoyageEmbedder
from .recipe_sources import RecipeSourceReader


class IngestResult(BaseModel):
    """Result payload returned upon recipe ingestion.

    Attributes:
        success: Whether the ingestion process completed successfully.
        recipe_id: ID of the persisted recipe document.
        confidence: Extraction confidence score between 0.0 and 1.0.
        needs_review: Whether the recipe requires user review.
        message: Human-readable status message.
        warnings: Non-fatal diagnostic warnings during ingestion.
    """

    success: bool = True
    recipe_id: str
    confidence: float
    needs_review: bool
    message: str = "Recipe imported"
    warnings: list[str] = Field(default_factory=list)


def confirmed_ids(matches: list[IngredientMatch]) -> list[str]:
    """Extract distinct canonical ingredient IDs from confirmed matches.

    Args:
        matches: List of ingredient match records.

    Returns:
        List of distinct confirmed ingredient IDs.
    """
    # Store only unique confirmed ingredient identifiers in the recipe document.
    # Remove duplicate keys so database indexes and inventory lookups stay fast and consistent.
    return list(
        dict.fromkeys(
            match.ingredient_id
            for match in matches
            if match.status == "confirmed" and match.ingredient_id is not None
        )
    )


class RecipeIngestService:
    """Service orchestrating recipe extraction, matching, and database persistence."""

    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        config: Settings | None = None,
        reader: RecipeSourceReader | None = None,
        embedder: VoyageEmbedder | None = None,
    ) -> None:
        """Initialize the recipe ingest service.

        Args:
            db: The async database handle.
            config: Runtime configuration settings.
            reader: Source reader for text, blogs, and videos.
            embedder: Embedding client for vector representations.
        """
        # Initialize dependencies with defaults to allow zero-config fallback when optional
        # services are absent.
        self.db = db
        self.config = config or settings
        self.reader = reader or RecipeSourceReader(self.config)
        self.embedder = embedder or VoyageEmbedder(self.config)
        self.matcher = IngredientMatcher(db, self.embedder, self.config)

    async def ingest_from_url(self, url: str) -> IngestResult:
        """Extract and persist a recipe from a web URL.

        Args:
            url: Web or YouTube URL to scrape or transcribe.

        Returns:
            The ingestion result including recipe ID and review status.
        """
        # Web recipes contain either structured schema data or unstructured blog text.
        # Fetch and parse the remote source first to extract recipe fields before database
        # persistence.
        extracted, source = await self.reader.from_url(url)
        return await self.store(extracted, source)

    async def ingest_from_text(self, text: str, source_name: str) -> IngestResult:
        """Extract and persist a recipe from raw text or WhatsApp notes.

        Args:
            text: Raw recipe text.
            source_name: Name or label for the source.

        Returns:
            The ingestion result including recipe ID and review status.
        """
        # Family recipes often arrive as unstructured text messages or notes.
        # Parse text into structured recipe format before saving to the database.
        extracted, source = await self.reader.from_text(text, source_name)
        return await self.store(extracted, source)

    async def ingest_from_image(
        self,
        image_bytes: bytes,
        mime_type: str,
        source_name: str,
    ) -> IngestResult:
        """Extract and persist a recipe from an image or screenshot.

        Args:
            image_bytes: Raw binary image payload.
            mime_type: MIME type of the uploaded image.
            source_name: User-provided name for the source.

        Returns:
            The ingestion result including recipe ID and review status.

        Raises:
            ProviderNotConfiguredError: If Gemini API key is missing.
        """
        # Physical cookbook pages and social media screenshots do not have text streams.
        # Verify provider configuration early to avoid processing unparseable binary data.
        if not self.config.gemini_api_key:
            raise ProviderNotConfiguredError("Set GEMINI_API_KEY to extract recipes from images.")

        # Extract structured recipe using multimodal vision.
        extractor = GeminiRecipeExtractor(self.config)
        extracted = await extractor.extract_image(image_bytes, mime_type)

        # Store image data in the recipe record if no remote image exists.
        # This allows the user to see the original source photo directly in the UI.
        if not extracted.recipe.image_url:
            import base64

            b64 = base64.b64encode(image_bytes).decode("ascii")
            extracted.recipe.image_url = f"data:{mime_type};base64,{b64}"
        return await self.store(extracted, source_name)

    async def ingest_from_audio(
        self,
        audio_bytes: bytes,
        mime_type: str,
        source_name: str,
    ) -> IngestResult:
        """Extract and persist a recipe from a voice recording or audio memo.

        Args:
            audio_bytes: Raw audio binary content.
            mime_type: MIME type of the uploaded audio.
            source_name: User-provided name for the source.

        Returns:
            The ingestion result including recipe ID and review status.

        Raises:
            ProviderNotConfiguredError: If no multimodal audio provider is configured.
            ExtractionError: If no speech could be extracted.
        """
        # Users frequently record voice notes while cooking instead of typing.
        # Use cloud Gemini if available to avoid heavy local CPU transcription load.
        if self.config.gemini_api_key:
            extractor = GeminiRecipeExtractor(self.config)
            extracted = await extractor.extract_audio(audio_bytes, mime_type)
            return await self.store(extracted, source_name)

        if not self.config.anthropic_api_key:
            raise ProviderNotConfiguredError(
                "Set GEMINI_API_KEY or ANTHROPIC_API_KEY to extract recipes from audio."
            )

        # Local Whisper requires a file path on disk to decode compressed audio containers.
        # Write bytes to a temporary file and ensure cleanup in the finally block.
        import asyncio
        import tempfile
        from pathlib import Path

        suffix = ".mp3"
        if "wav" in mime_type:
            suffix = ".wav"
        elif "m4a" in mime_type:
            suffix = ".m4a"
        elif "ogg" in mime_type:
            suffix = ".ogg"

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp_path = Path(tmp.name)
            tmp.write(audio_bytes)

        # Run transcription in a separate thread to prevent blocking the async event loop.
        try:
            from faster_whisper import WhisperModel

            def _transcribe() -> str:
                whisper = WhisperModel(
                    self.config.whisper_model,
                    device="cpu",
                    compute_type="int8",
                    local_files_only=self.config.whisper_local_files_only,
                )
                segments, _ = whisper.transcribe(str(tmp_path), vad_filter=True)
                return "\n".join(seg.text.strip() for seg in segments)

            text = await asyncio.to_thread(_transcribe)
            if not text.strip():
                raise ExtractionError("No speech was found in this audio file.")
            extracted = await self.reader.extractor.extract(text)
            return await self.store(extracted, source_name)
        finally:
            tmp_path.unlink(missing_ok=True)

    async def ingest_from_video(
        self,
        video_bytes: bytes,
        mime_type: str,
        source_name: str,
    ) -> IngestResult:
        """Extract and persist a recipe from a silent video reel by sampling frames.

        Args:
            video_bytes: Raw video file content.
            mime_type: MIME type of the uploaded video.
            source_name: User-provided name for the source.

        Returns:
            The ingestion result including recipe ID and review status.

        Raises:
            ProviderNotConfiguredError: If Gemini API key is missing.
        """
        # Video extraction requires multimodal vision capabilities.
        # Fail immediately if the required API credentials are not set.
        if not self.config.gemini_api_key:
            raise ProviderNotConfiguredError(
                "Set GEMINI_API_KEY to extract recipes from silent video frames."
            )
        from .video_frames import sample_video_keyframes

        # Sample keyframes at 1 frame per second to keep token counts small while capturing
        # visual steps.
        keyframes = await sample_video_keyframes(video_bytes, max_frames=15)
        extractor = GeminiRecipeExtractor(self.config)
        extracted = await extractor.extract_video_frames(keyframes)

        # Store the first keyframe as the cover thumbnail so the recipe card has a visual preview.
        if not extracted.recipe.image_url and keyframes:
            import base64

            b64 = base64.b64encode(keyframes[0]).decode("ascii")
            extracted.recipe.image_url = f"data:image/jpeg;base64,{b64}"
        return await self.store(extracted, source_name)

    async def store(self, extracted: ExtractedRecipe, source: str) -> IngestResult:
        """Validate, enrich, embed, and store an extracted recipe into the database.

        Args:
            extracted: Structured extraction output containing recipe and confidence.
            source: Source identifier or attribution string.

        Returns:
            IngestResult confirming persistence with generated recipe ID.

        Raises:
            ExtractionError: If the extracted recipe is incomplete or invalid.
        """
        recipe = extracted.recipe

        # Validate that the recipe contains core components before database insertion.
        # Prevent saving empty or malicious payloads that could corrupt the recipe vault.
        if not recipe.title.strip() or not recipe.ingredients or not recipe.steps:
            raise ExtractionError(
                "A recipe needs a title, at least one ingredient, and cooking steps."
            )
        if len(recipe.ingredients) > 200 or len(recipe.steps) > 500:
            raise ExtractionError("This recipe has too many ingredients or steps to import.")

        # Match recipe ingredients to canonical records to enable pantry tracking and macro
        # analysis.
        matches, warnings = await self.matcher.match(recipe)

        # Generate vector embeddings when Voyage AI is configured so semantic recipe search is
        # available.
        # Concatenate title, description, ingredients, and steps so the embedding captures full
        # culinary context.
        embedding = None
        if self.embedder.configured:
            text = "\n".join(
                [
                    recipe.title,
                    recipe.description or "",
                    *[item.name for item in recipe.ingredients],
                    *[step.instruction for step in recipe.steps],
                ]
            )
            embedding = (await self.embedder.embed([text]))[0]
        else:
            warnings.append("Embeddings skipped: VOYAGE_API_KEY is not configured.")

        # Flag low-confidence extractions for manual user review to maintain data quality.
        extraction_reviewed = extracted.confidence >= self.config.extraction_confidence_threshold
        try:
            document = Recipe(
                _id=str(ObjectId()),
                **recipe.model_dump(),
                embedding=embedding,
                embedding_model=self.embedder.name if embedding else None,
                normalized_ingredients=confirmed_ids(matches),
                ingredient_matches=matches,
                ingest_source=source,
                ingest_confidence=extracted.confidence,
                extraction_reviewed=extraction_reviewed,
                needs_review=not extraction_reviewed or any(m.status == "pending" for m in matches),
            )
        except ValidationError as exc:
            raise ExtractionError(
                "The imported recipe failed validation; nothing was saved."
            ) from exc

        # Store ingredient matches and review flags in the same document.
        # This prevents partial writes and eliminates orphaned review queue entries.
        data = document.model_dump(exclude={"id"})
        data["_id"] = ObjectId(document.id)
        await self.db[COLLECTION_RECIPES].insert_one(data)
        return IngestResult(
            recipe_id=document.id,
            confidence=extracted.confidence,
            needs_review=document.needs_review,
            warnings=warnings,
        )
