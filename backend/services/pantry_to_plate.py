"""Generative pantry-to-plate chef service for Iðunn Kitchen OS.

Strictly user-triggered AI synthesis of custom recipes from active pantry inventory.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import httpx

from backend.models.cook_ai import PantryToPlateRecipe, PantryToPlateRequest
from backend.services.ingest_errors import (
    ExtractionError,
    ProviderError,
    ProviderNotConfiguredError,
)

if TYPE_CHECKING:
    from backend.config import Settings
    from backend.models.inventory import Item

BASIC_STAPLES = ["salt", "water", "cooking oil", "black pepper"]


class PantryToPlateService:
    """Synthesizes generative recipes tailored strictly to available pantry stock."""

    def __init__(self, config: Settings) -> None:
        """Initialize service with application settings.

        Args:
            config: Runtime application settings.
        """
        self.config = config

    async def generate_recipe(
        self,
        request: PantryToPlateRequest,
        inventory_items: list[Item],
    ) -> PantryToPlateRecipe:
        """Synthesize recipe from available pantry items on explicit user trigger.

        Args:
            request: User preferences and optional selected item IDs.
            inventory_items: Available pantry inventory documents.

        Returns:
            Validated PantryToPlateRecipe model.

        Raises:
            ProviderNotConfiguredError: If API key is not configured.
            ProviderError: If external LLM request fails.
            ExtractionError: If AI output fails parsing.
        """
        # Validate that API key exists before attempting external network request.
        if not self.config.gemini_api_key and not self.config.anthropic_api_key:
            raise ProviderNotConfiguredError(
                "Configure GEMINI_API_KEY or ANTHROPIC_API_KEY in settings to generate recipes."
            )

        # Extract display names of available pantry items.
        available_names = [item.name.strip() for item in inventory_items if item.name.strip()]
        if not available_names:
            raise ExtractionError("Pantry inventory is empty. Add ingredients to cook.")

        prompt = (
            "You are a professional chef. Create an inventive, delicious home recipe "
            f"for {request.servings} servings ({request.meal_type}).\n"
            "CRITICAL CONSTRAINT: You may ONLY use ingredients from this active pantry list:\n"
            f"{json.dumps(available_names)}\n"
            f"You may also assume standard basic kitchen staples: {json.dumps(BASIC_STAPLES)}.\n"
            "Do NOT require any other ingredients.\n"
            f"Dietary preference: {request.dietary_preference or 'None specified'}.\n"
            "Output must be valid JSON matching this schema:\n"
            "{\n"
            '  "title": "Recipe Title",\n'
            '  "description": "Short culinary summary",\n'
            '  "prep_time_minutes": 10,\n'
            '  "cook_time_minutes": 20,\n'
            f'  "servings": {request.servings},\n'
            '  "cuisine_type": "veg",\n'
            '  "ingredients": [{"name": "item", "quantity": 1.0, "unit": "piece"}],\n'
            '  "steps": [{"step_number": 1, "instruction": "Step instruction"}],\n'
            f'  "assumed_staples": {json.dumps(BASIC_STAPLES)}\n'
            "}"
        )

        return await self._call_gemini(prompt)

    async def _call_gemini(self, prompt: str) -> PantryToPlateRecipe:
        """Execute Gemini API call with structured JSON response mode.

        Args:
            prompt: Chef synthesis instructions and ingredient inventory.

        Returns:
            Validated PantryToPlateRecipe instance.
        """
        # Connect to Google Gemini generative language endpoint.
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.config.gemini_model}:generateContent?key={self.config.gemini_api_key}"
        )
        payload: dict[str, Any] = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"response_mime_type": "application/json"},
        }

        # Issue network call with strict timeout limit.
        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                res = await client.post(url, json=payload)
                if res.status_code != 200:
                    raise ProviderError(f"Gemini API returned error {res.status_code}: {res.text}")
                data = res.json()
        except httpx.RequestError as exc:
            raise ProviderError(f"Network error communicating with Gemini: {exc}") from exc

        # Parse and validate generated JSON object.
        try:
            raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
            parsed = json.loads(raw_text)
            return PantryToPlateRecipe.model_validate(parsed)
        except (KeyError, IndexError, json.JSONDecodeError, ValueError) as exc:
            raise ExtractionError(f"Failed to parse generated recipe: {exc}") from exc
