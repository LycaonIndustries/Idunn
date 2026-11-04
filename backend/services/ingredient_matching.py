"""Exact regional names first, Atlas vector suggestions for unresolved ingredients."""

from __future__ import annotations

import re
import unicodedata
from typing import TYPE_CHECKING

from pymongo.errors import OperationFailure

from ..db import COLLECTION_INGREDIENTS
from ..models.recipe import IngredientMatch

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

    from ..config import Settings
    from ..models.recipe import RecipeCreate
    from .recipe_providers import VoyageEmbedder


def normalized_name(name: str) -> str:
    """Normalize an ingredient name using NFKC casefolding and whitespace stripping.

    Args:
        name: The raw ingredient name string.

    Returns:
        The normalized, lowercase, whitespace-collapsed name string.
    """
    # Users enter ingredient names with different casing, accents, and spacing.
    # Normalize to lowercase NFKC so that string comparisons do not fail because of formatting.
    return " ".join(unicodedata.normalize("NFKC", name).casefold().split())


class IngredientMatcher:
    """Matches recipe ingredients against canonical database records.

    Performs exact regional name matching first, with Atlas vector search fallback
    for unresolved ingredients when embeddings are available.
    """

    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        embedder: VoyageEmbedder,
        config: Settings,
    ) -> None:
        """Initialize the ingredient matcher service.

        Args:
            db: The async MongoDB database handle.
            embedder: Embedding client for semantic vector similarity.
            config: Application runtime settings.
        """
        # Store collection and embedder handles for database operations.
        self.collection = db[COLLECTION_INGREDIENTS]
        self.embedder = embedder
        self.config = config

    async def match(
        self,
        recipe: RecipeCreate,
    ) -> tuple[list[IngredientMatch], list[str]]:
        """Match ingredients of a recipe against canonical database ingredients.

        Args:
            recipe: The recipe creation payload containing raw ingredients.

        Returns:
            A tuple of (ingredient_matches, warnings) where ingredient_matches
            contains resolution status for each row and warnings reports non-fatal
            matching ambiguities.
        """
        matches = []
        unresolved = []
        warnings = []

        # Try exact matching first to avoid unnecessary vector search costs and latency.
        # Check canonical names and regional synonyms so local Indian terms resolve immediately.
        for index, item in enumerate(recipe.ingredients):
            name = normalized_name(item.name)
            pattern = "^" + re.escape(name).replace(r"\ ", r"\s+") + "$"
            cursor = self.collection.find(
                {
                    "$or": [
                        {"name": {"$regex": pattern, "$options": "i"}},
                        {"synonyms.name": {"$regex": pattern, "$options": "i"}},
                    ]
                }
            )
            candidates = []

            # An ingredient name can match multiple records if synonyms overlap across regions.
            # Filter by the recipe region when specified so that dialect-specific ingredients
            # resolve correctly.
            async for doc in cursor:
                canonical = normalized_name(doc["name"]) == name
                synonym = any(
                    normalized_name(s["name"]) == name
                    and (not recipe.region or not s.get("region") or s["region"] == recipe.region)
                    for s in doc.get("synonyms", [])
                )
                if canonical or synonym:
                    candidates.append(str(doc["_id"]))
                if len(candidates) > 1:
                    break

            # Confirm matching when exactly one ingredient candidate exists.
            # If multiple or zero candidates exist, mark for manual review or vector search.
            if len(candidates) == 1:
                matches.append(
                    IngredientMatch(
                        ingredient_index=index,
                        ingredient_id=candidates[0],
                        score=1,
                        method="exact",
                        status="confirmed",
                    )
                )
            else:
                matches.append(IngredientMatch(ingredient_index=index))
                if not candidates:
                    unresolved.append(index)
                else:
                    warnings.append(f"Ingredient {index + 1} has more than one exact match.")

        # Some ingredients use non-standard spelling or brand names that fail exact matching.
        # Use semantic vector search to find the closest database match for manual or automated
        # confirmation.
        if unresolved and self.embedder.configured:
            vectors = await self.embedder.embed(
                [recipe.ingredients[i].name for i in unresolved], input_type="query"
            )
            for index, vector in zip(unresolved, vectors, strict=True):
                try:
                    rows = await self.collection.aggregate(
                        [
                            {
                                "$vectorSearch": {
                                    "index": self.config.ingredient_vector_index,
                                    "path": "embedding",
                                    "queryVector": vector,
                                    "numCandidates": 100,
                                    "limit": 2,
                                    "filter": {"embedding_model": self.embedder.name},
                                }
                            },
                            {"$project": {"_id": 1, "score": {"$meta": "vectorSearchScore"}}},
                        ]
                    ).to_list(length=2)
                except OperationFailure as exc:
                    # The database can operate without vector search indexes in lightweight or
                    # offline environments.
                    # Catch index errors so the application continues to run and routes
                    # unmatched items to manual review.
                    # Re-raise connection and authentication errors because they require
                    # administrative action.
                    if exc.code not in {26, 27, 31082, 40324, 6047401}:
                        raise
                    warnings.append(
                        "Ingredient vector search is unavailable; review unmatched rows."
                    )
                    break
                if not rows:
                    continue

                # A high similarity score alone does not guarantee a correct match when two
                # ingredients are similar.
                # Require a minimum score margin between the top two candidates to prevent
                # false positive matches.
                score = float(rows[0]["score"])
                margin = score - float(rows[1]["score"]) if len(rows) > 1 else score
                confirmed = (
                    score >= self.config.ingredient_match_threshold
                    and margin >= self.config.ingredient_match_margin
                )
                candidate = str(rows[0]["_id"])
                matches[index] = IngredientMatch(
                    ingredient_index=index,
                    ingredient_id=candidate if confirmed else None,
                    suggested_id=candidate,
                    score=score,
                    method="vector",
                    status="confirmed" if confirmed else "pending",
                )
        return matches, warnings
