"""Check database setup commands; real MongoDB validation needs an integration run."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from idunn.db.recipe_search_indexes import vector_definition
from idunn.db.schemas import RECIPES_SCHEMA, setup_database_validation


async def test_schema_setup_includes_recipes_and_uses_supplied_database():
    db = MagicMock()
    db.list_collection_names = AsyncMock(return_value=["items", "ingredients", "recipes"])
    db.command = AsyncMock()
    db.__getitem__.return_value = SimpleNamespace(create_index=AsyncMock())
    await setup_database_validation(db)
    commands = [call.args[0] for call in db.command.call_args_list]
    recipe = next(cmd for cmd in commands if cmd["collMod"] == "recipes")
    assert recipe["validator"]["$jsonSchema"] == RECIPES_SCHEMA
    assert recipe["validationAction"] == "error"
    db.client.__getitem__.assert_not_called()


def test_optional_recipe_enums_allow_null():
    for name in ("region", "cuisine_type", "difficulty"):
        assert None in RECIPES_SCHEMA["properties"][name]["enum"]


def test_vector_index_matches_configured_model_dimensions():
    definition = vector_definition(1024)
    assert definition["fields"][0]["numDimensions"] == 1024
    assert {"type": "filter", "path": "embedding_model"} in definition["fields"]
