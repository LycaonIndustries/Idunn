"""Source parsing and download limits without live websites or model calls."""

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from backend.models.recipe import RecipeCreate
from backend.services import recipe_sources as sources
from backend.services.ingest_errors import ProviderNotConfiguredError, SourceError
from backend.services.recipe_providers import ExtractedRecipe
from backend.services.recipe_sources import (
    PageFetcher,
    RecipeSourceReader,
    SourcePage,
    duration_minutes,
    parse_ingredient,
    public_address,
    structured_recipe,
    validate_source_url,
    youtube_url,
)


def test_structured_recipe_preserves_steps_quantities_and_credit(recipe_html):
    recipe = structured_recipe(SourcePage(recipe_html, "https://example.org/curry"))
    assert recipe.title == "Aloo Gobi"
    assert recipe.ingredients[0].name == "aloo"
    assert recipe.ingredients[0].quantity == 2
    assert recipe.ingredients[1].quantity == 0.5
    assert recipe.ingredients[1].unit == "tsp"
    assert [s.step_number for s in recipe.steps] == [1, 2]
    assert recipe.prep_time_minutes == 75
    assert recipe.cook_time_minutes == 31
    assert recipe.servings == 4
    assert recipe.image_url == "https://example.org/curry.jpg"


def test_graph_recipe_is_found():
    data = {"@context": "https://schema.org", "@graph": [
        {"@type": "WebPage", "name": "Index"},
        {"@type": "Recipe", "name": "Rice", "recipeIngredient": ["1 cup rice"],
         "recipeInstructions": "Rinse rice.\nCook in water."},
    ]}
    html = '<script type="application/ld+json">' + json.dumps(data) + '</script>'
    recipe = structured_recipe(SourcePage(html, "https://example.org/rice"))
    assert recipe.title == "Rice"
    assert len(recipe.steps) == 2


@pytest.mark.parametrize(("line", "name", "quantity", "unit"), [
    ("1½ cups rice", "rice", 1.5, "cup"),
    ("1 1/2 katori paneer", "paneer", 1.5, "katori"),
    ("¼ tsp haldi", "haldi", 0.25, "tsp"),
    ("2 onions, chopped", "onions", 2, None),
    ("salt to taste", "salt to taste", None, None),
    ("1-2 chillies", "1-2 chillies", None, None),
    ("1/0 cups rice", "1/0 cups rice", None, None),
])
def test_ingredient_quantities(line, name, quantity, unit):
    item = parse_ingredient(line)
    assert (item.name, item.quantity, item.unit) == (name, quantity, unit)


@pytest.mark.parametrize(("value", "expected"), [
    ("PT2H", 120), ("P1D", 1440), ("PT0M", 0), ("bad", None), (None, None),
])
def test_durations(value, expected):
    assert duration_minutes(value) == expected


async def test_blog_fallback_uses_text_and_overrides_invented_source(
    config, recipe_data, monkeypatch
):
    recipe = RecipeCreate(**recipe_data, source_url="https://invented.example/")
    extractor = SimpleNamespace(extract=AsyncMock(return_value=ExtractedRecipe(
        recipe=recipe, confidence=0.8,
    )))
    reader = RecipeSourceReader(config, extractor)
    monkeypatch.setattr(reader.fetcher, "fetch", AsyncMock(return_value=SourcePage(
        "<html><article><h1>Curry</h1><p>Take aloo and cook until tender.</p></article></html>",
        "https://example.org/curry",
    )))
    result, source = await reader.from_url("https://example.org/curry")
    assert source == "blog"
    assert "Take aloo" in extractor.extract.call_args.args[0]
    assert result.recipe.source_url == "https://example.org/curry"


async def test_text_credit_is_not_invented(config, recipe_data):
    recipe = RecipeCreate(
        **recipe_data, source_url="https://invented.example/", video_url="https://invented.example/v"
    )
    reader = RecipeSourceReader(config, SimpleNamespace(extract=AsyncMock(
        return_value=ExtractedRecipe(recipe=recipe, confidence=1),
    )))
    result, source = await reader.from_text("Family curry recipe", "Dadi's notebook")
    assert source == "manual"
    assert result.recipe.source_url is None
    assert result.recipe.video_url is None
    assert result.recipe.source_name == "Dadi's notebook"


@pytest.mark.parametrize("url", [
    "file:///etc/passwd", "ftp://example.org/a",
    "https://user:password@example.org", "https://example.org:8000",
])
def test_invalid_urls(url):
    with pytest.raises(SourceError):
        validate_source_url(url)


async def test_private_dns_addresses_are_rejected(monkeypatch):
    monkeypatch.setattr(
        sources.socket, "getaddrinfo", lambda *a, **k: [(2, 1, 6, "", ("127.0.0.1", 443))]
    )
    with pytest.raises(SourceError, match="public"):
        await public_address("local.example", 443)


def install_transport(monkeypatch, handler):
    original = httpx.AsyncClient
    monkeypatch.setattr(sources.httpx, "AsyncClient", lambda **kwargs: original(
        transport=httpx.MockTransport(handler), **kwargs,
    ))
    monkeypatch.setattr(sources, "public_address", AsyncMock(return_value="93.184.216.34"))


async def test_fetch_pins_checked_address_and_follows_redirect(config, monkeypatch):
    calls = []
    def handler(request):
        calls.append(request)
        assert request.url.host == "93.184.216.34"
        assert request.headers["host"] == "example.org"
        assert request.extensions["sni_hostname"] == "example.org"
        if len(calls) == 1:
            return httpx.Response(302, headers={"location": "/final"})
        return httpx.Response(
            200, text="<html>Recipe</html>", headers={"content-type": "text/html"}
        )
    install_transport(monkeypatch, handler)
    page = await PageFetcher(config).fetch("https://example.org/old")
    assert page.url == "https://example.org/final"
    assert len(calls) == 2


async def test_redirect_is_checked_before_connecting(config, monkeypatch):
    install_transport(monkeypatch, lambda request: httpx.Response(
        302, headers={"location": "http://127.0.0.1/"},
    ))
    resolver = AsyncMock(side_effect=["93.184.216.34", SourceError("private address")])
    monkeypatch.setattr(sources, "public_address", resolver)
    with pytest.raises(SourceError, match="private"):
        await PageFetcher(config).fetch("https://example.org/")
    assert resolver.call_count == 2


@pytest.mark.parametrize(("headers", "content", "message"), [
    ({"content-type": "application/octet-stream"}, b"abc", "HTML"),
    ({"content-type": "text/html"}, b"a" * 101, "too large"),
])
async def test_bad_or_large_sources(config, monkeypatch, headers, content, message):
    config.source_max_bytes = 100
    install_transport(monkeypatch, lambda request: httpx.Response(
        200, headers=headers, content=content,
    ))
    with pytest.raises(SourceError, match=message):
        await PageFetcher(config).fetch("https://example.org/r")


def test_youtube_classification_does_not_accept_lookalike_domains():
    assert youtube_url("https://youtu.be/abcdefghijk?t=2") == "https://www.youtube.com/watch?v=abcdefghijk"
    assert youtube_url("https://youtube.com.evil.example/watch?v=abcdefghijk") is None
    with pytest.raises(SourceError):
        youtube_url("https://www.youtube.com/playlist?list=abc")


async def test_video_missing_key_fails_before_download(config, monkeypatch):
    reader = RecipeSourceReader(config)
    download = AsyncMock()
    monkeypatch.setattr(reader, "_transcribe", download)
    with pytest.raises(ProviderNotConfiguredError):
        await reader.from_url("https://youtu.be/abcdefghijk")
    download.assert_not_called()


async def test_video_timeout_kills_worker_and_cleans_audio(config, monkeypatch):
    config.video_timeout_seconds = 0.01
    output_paths = []
    class Worker:
        returncode = None
        async def communicate(self):
            if self.returncode is None:
                await asyncio.sleep(10)
            return None, b""
        def kill(self):
            self.returncode = -9
    worker = Worker()
    async def spawn(*args, **kwargs):
        output_paths.append(Path(args[4]))
        return worker
    monkeypatch.setattr(sources.asyncio, "create_subprocess_exec", spawn)
    with pytest.raises(SourceError, match="timed out"):
        await RecipeSourceReader(config)._transcribe("https://www.youtube.com/watch?v=abcdefghijk")
    assert worker.returncode == -9
    assert not output_paths[0].parent.exists()


async def test_video_transcript_is_extracted_with_video_credit(config, recipe_data, monkeypatch):
    config.anthropic_api_key = "test-key"
    reader = RecipeSourceReader(config)
    monkeypatch.setattr(reader, "_transcribe", AsyncMock(return_value="आलू पकाएं"))
    extract = AsyncMock(return_value=ExtractedRecipe(
        recipe=RecipeCreate(**recipe_data), confidence=0.8,
    ))
    monkeypatch.setattr(reader.extractor, "extract", extract)
    result, source = await reader.from_url("https://youtu.be/abcdefghijk")
    extract.assert_awaited_once_with("आलू पकाएं")
    assert source == "youtube"
    assert result.recipe.video_url == "https://www.youtube.com/watch?v=abcdefghijk"
    assert result.recipe.source_name == "YouTube"
