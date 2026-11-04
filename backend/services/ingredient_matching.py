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
                    # Only missing/unsupported search indexes degrade to manual review.
                    # Auth failures and unrelated database failures must reach the caller.
                    if exc.code not in {26, 27, 31082, 40324, 6047401}:
                        raise
                    warnings.append(
                        "Ingredient vector search is unavailable; review unmatched rows."
                    )
                    break
                if not rows:
                    continue
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
