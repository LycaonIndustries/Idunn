"""Provider boundary tests: malformed output, request shape, and failure messages."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from backend.services import recipe_providers as providers
from backend.services.ingest_errors import ExtractionError, ProviderError
from backend.services.recipe_providers import RecipeTextExtractor, VoyageEmbedder


@pytest.mark.parametrize(
    "rows",
    [
        [],
        [{"index": 1, "embedding": [1, 0, 0]}],
        [{"index": 0, "embedding": [1, 0]}],
        [{"index": 0, "embedding": [0, 0, 0]}],
    ],
)
async def test_bad_embedding_responses_are_rejected(config, monkeypatch, rows):
    config.voyage_api_key = "test-key"
    original = httpx.AsyncClient
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"data": rows}))
    monkeypatch.setattr(
        providers.httpx, "AsyncClient", lambda **kwargs: original(transport=transport, **kwargs)
    )
    with pytest.raises(ProviderError):
        await VoyageEmbedder(config).embed(["rice"])


async def test_embedding_response_order_is_restored(config, monkeypatch):
    config.voyage_api_key = "test-key"
    original = httpx.AsyncClient
    rows = [{"index": 1, "embedding": [0, 1, 0]}, {"index": 0, "embedding": [1, 0, 0]}]
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"data": rows}))
    monkeypatch.setattr(
        providers.httpx, "AsyncClient", lambda **kwargs: original(transport=transport, **kwargs)
    )
    assert await VoyageEmbedder(config).embed(["rice", "aloo"]) == [[1, 0, 0], [0, 1, 0]]


@pytest.mark.parametrize("stop_reason", ["max_tokens", "end_turn"])
async def test_truncated_extraction_is_not_accepted(config, monkeypatch, stop_reason):
    config.anthropic_api_key = "test-key"

    class Client:
        messages = SimpleNamespace(
            create=AsyncMock(
                return_value=SimpleNamespace(
                    stop_reason=stop_reason,
                )
            )
        )

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

    monkeypatch.setattr(providers, "AsyncAnthropic", lambda **kwargs: Client())
    with pytest.raises(ExtractionError, match="incomplete"):
        await RecipeTextExtractor(config).extract("Cook rice")


async def test_model_output_is_validated(config, monkeypatch):
    config.anthropic_api_key = "test-key"

    class Client:
        messages = SimpleNamespace(
            create=AsyncMock(
                return_value=SimpleNamespace(
                    stop_reason="tool_use",
                    content=[
                        SimpleNamespace(
                            type="tool_use",
                            name="recipe",
                            input={"recipe": {"title": ""}, "confidence": 3},
                        )
                    ],
                )
            )
        )

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

    monkeypatch.setattr(providers, "AsyncAnthropic", lambda **kwargs: Client())
    with pytest.raises(ExtractionError, match="validation"):
        await RecipeTextExtractor(config).extract("Cook rice")
