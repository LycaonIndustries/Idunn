"""Tests for Gemini multimodal recipe extraction."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from idunn.config import Settings
from idunn.services.ingest_errors import ExtractionError, ProviderError, ProviderNotConfiguredError
from idunn.services.recipe_providers import GeminiRecipeExtractor, RecipeTextExtractor


@pytest.mark.asyncio
async def test_gemini_missing_api_key_raises() -> None:
    config = Settings(gemini_api_key=None, anthropic_api_key=None)
    extractor = GeminiRecipeExtractor(config)
    with pytest.raises(ProviderNotConfiguredError):
        await extractor.extract_text("some recipe text")


@pytest.mark.asyncio
async def test_gemini_extract_text_success() -> None:
    config = Settings(gemini_api_key="fake-key", gemini_model="gemini-2.5-flash")
    extractor = GeminiRecipeExtractor(config)

    fake_response_data = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": (
                                '{"recipe": {"title": "Dal Tadka", "prep_time": 10, "cook_time": 20, '
                                '"servings": 4, "ingredients": [{"name": "toor dal", "quantity": 1, "unit": "katori"}], '
                                '"steps": [{"step_number": 1, "instruction": "Boil dal"}]}, "confidence": 0.95}'
                            )
                        }
                    ]
                }
            }
        ]
    }

    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = fake_response_data

    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=mock_response)):
        result = await extractor.extract_text("Boil 1 katori toor dal...")
        assert result.recipe.title == "Dal Tadka"
        assert len(result.recipe.ingredients) == 1
        assert result.recipe.ingredients[0].name == "toor dal"
        assert result.confidence == 0.95


@pytest.mark.asyncio
async def test_gemini_extract_image_success() -> None:
    config = Settings(gemini_api_key="fake-key", gemini_model="gemini-2.5-flash")
    extractor = GeminiRecipeExtractor(config)

    fake_response_data = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": (
                                '{"recipe": {"title": "Palak Paneer", "prep_time": 15, "cook_time": 25, '
                                '"servings": 3, "ingredients": [{"name": "paneer", "quantity": 200, "unit": "g"}], '
                                '"steps": [{"step_number": 1, "instruction": "Blanch palak"}]}, "confidence": 0.92}'
                            )
                        }
                    ]
                }
            }
        ]
    }

    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = fake_response_data

    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=mock_response)):
        result = await extractor.extract_image(b"fake_image_bytes", "image/png")
        assert result.recipe.title == "Palak Paneer"
        assert result.confidence == 0.92


@pytest.mark.asyncio
async def test_gemini_api_error_handling() -> None:
    config = Settings(gemini_api_key="fake-key", gemini_model="gemini-2.5-flash")
    extractor = GeminiRecipeExtractor(config)

    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.status_code = 429
    mock_response.text = "Quota exceeded"

    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=mock_response)):
        with pytest.raises(ProviderError):
            await extractor.extract_text("some text")


@pytest.mark.asyncio
async def test_recipe_text_extractor_prefers_gemini_when_set() -> None:
    config = Settings(gemini_api_key="fake-gemini-key", anthropic_api_key=None)
    extractor = RecipeTextExtractor(config)

    fake_response_data = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": (
                                '{"recipe": {"title": "Khichdi", "prep_time": 5, "cook_time": 15, '
                                '"servings": 2, "ingredients": [{"name": "rice", "quantity": 1, "unit": "cup"}], '
                                '"steps": [{"step_number": 1, "instruction": "Pressure cook"}]}, "confidence": 0.9}'
                            )
                        }
                    ]
                }
            }
        ]
    }

    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = fake_response_data

    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=mock_response)):
        result = await extractor.extract("Cook rice...")
        assert result.recipe.title == "Khichdi"
