"""MongoDB JSON Schema validation for Iðunn collections.

Defines schema validation rules applied at the database level.
This provides "NoSQL-with-discipline" as mentioned in the design doc.
"""

from __future__ import annotations

from typing import Any


# JSON Schema for items collection (inventory)
ITEMS_SCHEMA: dict[str, Any] = {
    "bsonType": "object",
    "required": ["name", "quantity", "unit", "location", "added_at", "consumed"],
    "properties": {
        "_id": {"bsonType": "objectId"},
        "name": {
            "bsonType": "string",
            "minLength": 1,
            "maxLength": 200,
            "description": "Item name",
        },
        "quantity": {
            "bsonType": "double",
            "minimum": 0.0001,
            "description": "Quantity (must be positive)",
        },
        "unit": {
            "bsonType": "string",
            "enum": [
                "g",
                "kg",
                "paav",
                "ml",
                "l",
                "tsp",
                "tbsp",
                "chamcha",
                "katori",
                "piece",
                "bunch",
                "packet",
                "box",
            ],
            "description": "Unit of measurement",
        },
        "location": {
            "bsonType": "string",
            "enum": [
                "fridge",
                "freezer",
                "pantry",
                "dry_store",
                "cabinet",
                "counter",
                "spice_box",
                "windowsill",
            ],
            "description": "Storage location",
        },
        "expiry_date": {
            "bsonType": ["date", "null"],
            "description": "Expiry date (optional)",
        },
        "added_at": {"bsonType": "date", "description": "When item was added"},
        "updated_at": {"bsonType": "date", "description": "Last update time"},
        "consumed": {
            "bsonType": "bool",
            "description": "Marked as consumed/discarded",
        },
        "notes": {
            "bsonType": ["string", "null"],
            "maxLength": 500,
            "description": "Optional notes",
        },
        "barcode": {
            "bsonType": ["string", "null"],
            "maxLength": 50,
            "description": "Barcode for quick add",
        },
    },
}

# JSON Schema for ingredients collection (canonical ingredient master)
INGREDIENTS_SCHEMA: dict[str, Any] = {
    "bsonType": "object",
    "required": ["name", "category", "created_at", "updated_at"],
    "properties": {
        "_id": {"bsonType": "objectId"},
        "name": {
            "bsonType": "string",
            "minLength": 1,
            "maxLength": 100,
            "description": "Canonical ingredient name",
        },
        "category": {
            "bsonType": "string",
            "enum": [
                "cereal",
                "pulse",
                "vegetable",
                "fruit",
                "spice",
                "herb",
                "dairy",
                "oil",
                "flour",
                "sweetener",
                "nut",
                "seed",
                "condiment",
                "readymade",
            ],
            "description": "Ingredient category",
        },
        "synonyms": {
            "bsonType": "array",
            "items": {
                "bsonType": "object",
                "required": ["name"],
                "properties": {
                    "name": {"bsonType": "string", "minLength": 1, "maxLength": 100},
                    "region": {"bsonType": ["string", "null"]},
                    "language": {"bsonType": ["string", "null"], "maxLength": 20},
                },
            },
            "description": "Alternative names",
        },
        "default_unit": {
            "bsonType": ["string", "null"],
            "maxLength": 20,
            "description": "Default unit",
        },
        "ifct_id": {
            "bsonType": ["string", "null"],
            "maxLength": 50,
            "description": "IFCT ID",
        },
        "regions": {
            "bsonType": "array",
            "items": {
                "bsonType": "string",
                "enum": [
                    "north_india",
                    "south_india",
                    "east_india",
                    "west_india",
                    "central_india",
                    "northeast_india",
                    "pan_india",
                ],
            },
            "description": "Regions where ingredient is commonly used",
        },
        "nutrition_per_100g": {
            "bsonType": ["object", "null"],
            "description": "Nutrition data per 100g",
        },
        "created_at": {"bsonType": "string", "description": "Creation timestamp"},
        "updated_at": {"bsonType": "string", "description": "Last update timestamp"},
    },
}


async def create_collection_with_validation(
    db, collection_name: str, schema: dict
) -> None:
    """Create a collection with JSON schema validation."""
    from motor.motor_asyncio import AsyncIOMotorCollection

    # Check if collection exists
    existing = await db.list_collection_names()
    if collection_name in existing:
        # Update validation on existing collection
        await db.command(
            {
                "collMod": collection_name,
                "validator": {"$jsonSchema": schema},
                "validationLevel": "strict",
                "validationAction": "error",
            }
        )
    else:
        # Create new collection with validation
        await db.create_collection(
            collection_name,
            validator={"$jsonSchema": schema},
            validationLevel="strict",
            validationAction="error",
        )


async def setup_database_validation(db) -> None:
    """Set up JSON schema validation for all collections."""
    from ..config import settings

    # Import here to avoid circular imports
    collections = {
        settings.mongodb_db_name: {
            "items": ITEMS_SCHEMA,
            "ingredients": INGREDIENTS_SCHEMA,
        }
    }

    for db_name, schema_map in collections.items():
        target_db = db.client[db_name]
        for coll_name, schema in schema_map.items():
            await create_collection_with_validation(target_db, coll_name, schema)
