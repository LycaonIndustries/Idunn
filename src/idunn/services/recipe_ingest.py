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
from .ingest_errors import ExtractionError
from .ingredient_matching import IngredientMatcher
from .recipe_providers import ExtractedRecipe, VoyageEmbedder
from .recipe_sources import RecipeSourceReader


class IngestResult(BaseModel):
    success: bool = True
    recipe_id: str
    confidence: float
    needs_review: bool
    message: str = "Recipe imported"
    warnings: list[str] = Field(default_factory=list)


def confirmed_ids(matches: list[IngredientMatch]) -> list[str]:
    return list(dict.fromkeys(
        match.ingredient_id for match in matches
        if match.status == "confirmed" and match.ingredient_id is not None
    ))


class RecipeIngestService:
    def __init__(self, db: AsyncIOMotorDatabase, config: Settings | None = None,
                 reader: RecipeSourceReader | None = None, embedder: VoyageEmbedder | None = None):
        self.db = db
        self.config = config or settings
        self.reader = reader or RecipeSourceReader(self.config)
        self.embedder = embedder or VoyageEmbedder(self.config)
        self.matcher = IngredientMatcher(db, self.embedder, self.config)

    async def ingest_from_url(self, url: str) -> IngestResult:
        extracted, source = await self.reader.from_url(url)
        return await self.store(extracted, source)

    async def ingest_from_text(self, text: str, source_name: str) -> IngestResult:
        extracted, source = await self.reader.from_text(text, source_name)
        return await self.store(extracted, source)

    async def store(self, extracted: ExtractedRecipe, source: str) -> IngestResult:
        recipe = extracted.recipe
        if not recipe.title.strip() or not recipe.ingredients or not recipe.steps:
            raise ExtractionError(
                "A recipe needs a title, at least one ingredient, and cooking steps."
            )
        if len(recipe.ingredients) > 200 or len(recipe.steps) > 500:
            raise ExtractionError("This recipe has too many ingredients or steps to import.")
        matches, warnings = await self.matcher.match(recipe)
        embedding = None
        if self.embedder.configured:
            text = "\n".join([
                recipe.title, recipe.description or "",
                *[item.name for item in recipe.ingredients],
                *[step.instruction for step in recipe.steps],
            ])
            embedding = (await self.embedder.embed([text]))[0]
        else:
            warnings.append("Embeddings skipped: VOYAGE_API_KEY is not configured.")
        extraction_reviewed = extracted.confidence >= self.config.extraction_confidence_threshold
        try:
            document = Recipe(
                _id=str(ObjectId()), **recipe.model_dump(),
                embedding=embedding,
                embedding_model=self.embedder.name if embedding else None,
                normalized_ingredients=confirmed_ids(matches), ingredient_matches=matches,
                ingest_source=source, ingest_confidence=extracted.confidence,
                extraction_reviewed=extraction_reviewed,
                needs_review=not extraction_reviewed or any(
                    m.status == "pending" for m in matches
                ),
            )
        except ValidationError as exc:
            raise ExtractionError(
                "The imported recipe failed validation; nothing was saved."
            ) from exc
        # Matches and review state live in the same document: no half-written review queue.
        data = document.model_dump(exclude={"id"})
        data["_id"] = ObjectId(document.id)
        await self.db[COLLECTION_RECIPES].insert_one(data)
        return IngestResult(
            recipe_id=document.id, confidence=extracted.confidence,
            needs_review=document.needs_review, warnings=warnings,
        )
