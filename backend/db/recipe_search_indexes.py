"""Explicit setup for Atlas recipe search and the canonical ingredient vectors.

Run with --create-indexes and/or --embed-ingredients. The latter calls Voyage.
Nothing in this module runs automatically on application startup.
"""

from __future__ import annotations

import argparse
import asyncio
from typing import TYPE_CHECKING

from pymongo.operations import SearchIndexModel

from ..config import settings
from ..services.recipe_providers import VoyageEmbedder
from . import COLLECTION_INGREDIENTS, COLLECTION_RECIPES, MongoClient

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

    from ..config import Settings


def vector_definition(dimensions: int) -> dict:
    return {"fields": [
        {
            "type": "vector", "path": "embedding",
            "numDimensions": dimensions, "similarity": "cosine",
        },
        {"type": "filter", "path": "embedding_model"},
    ]}


async def create_search_indexes(db: AsyncIOMotorDatabase, config: Settings) -> None:
    specs = [
        (COLLECTION_INGREDIENTS, config.ingredient_vector_index, "vectorSearch",
         vector_definition(config.embedding_dimensions)),
        (COLLECTION_RECIPES, "recipe_embeddings", "vectorSearch",
         vector_definition(config.embedding_dimensions)),
        (COLLECTION_RECIPES, "recipe_text", "search", {"mappings": {"dynamic": False, "fields": {
            "title": {"type": "string"}, "description": {"type": "string"},
            "ingredients": {"type": "document", "fields": {"name": {"type": "string"}}},
            "steps": {"type": "document", "fields": {"instruction": {"type": "string"}}},
        }}}),
    ]
    for collection_name, name, kind, definition in specs:
        collection = db[collection_name]
        existing = await collection.list_search_indexes(name).to_list(length=1)
        if existing:
            if existing[0].get("latestDefinition") != definition:
                await collection.update_search_index(name, definition)
        else:
            await collection.create_search_index(SearchIndexModel(
                name=name, type=kind, definition=definition,
            ))


async def embed_ingredients(db: AsyncIOMotorDatabase, embedder: VoyageEmbedder) -> int:
    count = 0
    collection = db[COLLECTION_INGREDIENTS]
    async for doc in collection.find({}):
        text = "; ".join([doc["name"], *[s["name"] for s in doc.get("synonyms", [])]])
        if (doc.get("embedding_model") == embedder.name
                and doc.get("embedding_text") == text
                and len(doc.get("embedding", [])) == embedder.dimensions):
            continue
        vector = (await embedder.embed([text]))[0]
        # Don't attach an old vector if someone edited the ingredient while the API ran.
        snapshot = {
            "_id": doc["_id"], "name": doc["name"],
            "synonyms": doc.get("synonyms", {"$exists": False}),
        }
        result = await collection.update_one(
            snapshot,
            {"$set": {
                "embedding": vector, "embedding_model": embedder.name, "embedding_text": text,
            }},
        )
        count += result.modified_count
    return count


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--create-indexes", action="store_true")
    parser.add_argument("--embed-ingredients", action="store_true")
    args = parser.parse_args()
    if not (args.create_indexes or args.embed_ingredients):
        parser.print_help()
        return
    try:
        db = MongoClient.get_db()
        if args.create_indexes:
            await create_search_indexes(db, settings)
            print("Atlas indexes requested; wait until they report READY before vector matching.")
        if args.embed_ingredients:
            count = await embed_ingredients(db, VoyageEmbedder(settings))
            print(f"Updated vectors for {count} ingredients.")
    finally:
        await MongoClient.close()


if __name__ == "__main__":
    asyncio.run(main())
