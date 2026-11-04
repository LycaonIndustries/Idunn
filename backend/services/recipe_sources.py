"""Read bounded recipe sources, then parse structured data before using a model."""

from __future__ import annotations

import asyncio
import ipaddress
import math
import re
import socket
import sys
from dataclasses import dataclass
from datetime import timedelta
from fractions import Fraction
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qs, urljoin, urlsplit

import httpx
import isodate
from bs4 import BeautifulSoup
from pydantic import ValidationError
from readability import Document
from scrape_schema_recipe import loads

from ..models.recipe import IngredientItem, NutritionInfo, RecipeCreate, Step
from .ingest_errors import ProviderNotConfiguredError, SourceError
from .recipe_providers import ExtractedRecipe, RecipeTextExtractor

if TYPE_CHECKING:
    from ..config import Settings


@dataclass
class SourcePage:
    html: str
    url: str


def validate_source_url(url: str) -> httpx.URL:
    try:
        parsed = httpx.URL(url)
        if (
            parsed.scheme not in {"https", "http"}
            or not parsed.host
            or parsed.userinfo
            or parsed.port not in {None, 80, 443}
            or len(url) > 500
        ):
            raise ValueError
        return parsed
    except (ValueError, httpx.InvalidURL) as exc:
        raise SourceError("Use a public HTTP or HTTPS recipe URL on port 80 or 443.") from exc


async def public_address(host: str, port: int) -> str:
    try:
        addresses = await asyncio.to_thread(socket.getaddrinfo, host, port, type=socket.SOCK_STREAM)
        ips = [item[4][0] for item in addresses]
        if not ips or any(not ipaddress.ip_address(ip).is_global for ip in ips):
            raise SourceError("Recipe URLs must point to a public website.")
        return ips[0]
    except socket.gaierror as exc:
        raise SourceError("The recipe website could not be found.") from exc


class PageFetcher:
    def __init__(self, config: Settings):
        self.config = config

    async def fetch(self, url: str) -> SourcePage:
        current = validate_source_url(url)
        try:
            async with asyncio.timeout(self.config.source_timeout_seconds):
                async with httpx.AsyncClient(
                    timeout=self.config.source_timeout_seconds,
                    follow_redirects=False,
                    trust_env=False,
                ) as client:
                    for _ in range(6):
                        address = await public_address(
                            current.host, current.port or (443 if current.scheme == "https" else 80)
                        )
                        # Connect to the checked address, preserving Host and TLS SNI. A second
                        # DNS lookup at connect time would allow redirects/rebinding to local hosts.
                        async with client.stream(
                            "GET",
                            current.copy_with(host=address),
                            headers={
                                "Host": current.netloc.decode(),
                                "User-Agent": "Idunn/0.1 (user-requested recipe import)",
                            },
                            extensions={"sni_hostname": current.host},
                        ) as response:
                            if response.is_redirect:
                                location = response.headers.get("location")
                                if not location:
                                    raise SourceError(
                                        "The recipe website returned an empty redirect."
                                    )
                                current = validate_source_url(urljoin(str(current), location))
                                continue
                            response.raise_for_status()
                            content_type = response.headers.get("content-type", "").lower()
                            if not any(
                                t in content_type for t in ("text/html", "application/xhtml")
                            ):
                                raise SourceError("The URL did not return an HTML recipe page.")
                            chunks = bytearray()
                            async for chunk in response.aiter_bytes():
                                chunks.extend(chunk)
                                if len(chunks) > self.config.source_max_bytes:
                                    raise SourceError("The recipe page is too large to import.")
                            text = bytes(chunks).decode(
                                response.encoding or "utf-8", errors="replace"
                            )
                            return SourcePage(text, str(current))
                    raise SourceError("The recipe website redirected too many times.")
        except (httpx.HTTPError, TimeoutError) as exc:
            raise SourceError(
                "The recipe website could not be read; check the URL and retry."
            ) from exc


def clean_text(value: str) -> str:
    return BeautifulSoup(value, "html.parser").get_text(" ", strip=True)


def parse_ingredient(line: str) -> IngredientItem:
    """Parse common quantities without throwing away the original line."""
    original = clean_text(line)
    value = original
    fractions = {"½": "1/2", "¼": "1/4", "¾": "3/4", "⅓": "1/3", "⅔": "2/3"}
    for glyph, fraction in fractions.items():
        value = value.replace(glyph, f" {fraction}")
    match = re.match(r"^\s*(\d+\s+\d+/\d+|\d+/\d+|\d+(?:\.\d+)?)\s*", value)
    if not match:
        return IngredientItem(name=original)
    try:
        quantity = float(sum(Fraction(part) for part in match[1].split()))
    except (ValueError, ZeroDivisionError):
        return IngredientItem(name=original)
    rest = value[match.end():].strip()
    # Ranges and alternatives need a person/model, not an invented exact quantity.
    if not rest or re.match(r"^(?:[-–]|to\b)", rest) or quantity <= 0:
        return IngredientItem(name=original)
    units = {
        "g": "g", "gram": "g", "grams": "g", "kg": "kg", "kilogram": "kg",
        "ml": "ml", "l": "l", "litre": "l", "litres": "l",
        "tsp": "tsp", "teaspoon": "tsp", "teaspoons": "tsp",
        "tbsp": "tbsp", "tablespoon": "tbsp", "tablespoons": "tbsp",
        "cup": "cup", "cups": "cup", "katori": "katori", "chamcha": "chamcha",
        "paav": "paav", "piece": "piece", "pieces": "piece", "bunch": "bunch",
    }
    parts = rest.split(maxsplit=1)
    unit = units.get(parts[0].casefold().rstrip("."))
    name = parts[1] if unit and len(parts) == 2 else rest
    if unit and len(parts) == 1:
        return IngredientItem(name=original)
    name, _, note = name.partition(",")
    return IngredientItem(
        name=name.strip(), quantity=quantity, unit=unit,
        notes=(note.strip() or original)[:200],
    )


def recipe_steps(value: Any) -> list[str]:
    if isinstance(value, str):
        return [clean_text(line) for line in value.splitlines() if clean_text(line)]
    if isinstance(value, dict):
        return recipe_steps(
            value.get("itemListElement") or value.get("text") or value.get("name", "")
        )
    if isinstance(value, list):
        return [step for item in value for step in recipe_steps(item)]
    return []


def duration_minutes(value: Any) -> int | None:
    if not isinstance(value, str):
        return None
    try:
        duration = isodate.parse_duration(value)
        if isinstance(duration, timedelta) and duration.total_seconds() >= 0:
            return math.ceil(duration.total_seconds() / 60)
    except (ValueError, TypeError):
        pass
    return None


def extract_meta_image(html: str) -> str | None:
    try:
        soup = BeautifulSoup(html[:100000], "html.parser")
        meta = (
            soup.find("meta", property="og:image")
            or soup.find("meta", attrs={"name": "og:image"})
            or soup.find("meta", attrs={"name": "twitter:image"})
            or soup.find("meta", property="twitter:image")
        )
        if meta and meta.get("content"):
            img = str(meta["content"]).strip()
            if img.startswith(("http://", "https://")):
                return img
    except Exception:
        pass
    return None


def parse_nutrition(raw: Any) -> NutritionInfo | None:
    if not isinstance(raw, dict):
        return None

    def extract_float(v: Any) -> float | None:
        if v is None:
            return None
        m = re.search(r"(\d+(\.\d+)?)", str(v))
        return float(m.group(1)) if m else None

    calories = extract_float(raw.get("calories"))
    protein = extract_float(raw.get("proteinContent"))
    carbs = extract_float(raw.get("carbohydrateContent"))
    fat = extract_float(raw.get("fatContent"))
    fiber = extract_float(raw.get("fiberContent"))

    if any(x is not None for x in (calories, protein, carbs, fat, fiber)):
        return NutritionInfo(
            calories=calories,
            protein=protein,
            carbs=carbs,
            fat=fat,
            fiber=fiber,
        )
    return None


def structured_recipe(page: SourcePage) -> RecipeCreate | None:
    try:
        candidates = loads(page.html)
    except (ValueError, TypeError, KeyError):
        return None
    for raw in candidates:
        try:
            ingredients = raw.get("recipeIngredient", [])
            if isinstance(ingredients, str):
                ingredients = ingredients.splitlines()
            instructions = recipe_steps(raw.get("recipeInstructions", []))
            if not ingredients or not instructions:
                continue
            image = raw.get("image")
            if isinstance(image, list):
                image = image[0] if image else None
            if isinstance(image, dict):
                image = image.get("url") or image.get("contentUrl")
            image = urljoin(page.url, image) if isinstance(image, str) else None
            if image and urlsplit(image).scheme not in {"http", "https"}:
                image = None
            if not image:
                image = extract_meta_image(page.html)
            servings = re.search(r"\d+", str(raw.get("recipeYield", "")))
            nutrition = parse_nutrition(raw.get("nutrition"))
            recipe = RecipeCreate(
                title=clean_text(raw.get("name", "")),
                description=clean_text(raw["description"]) if raw.get("description") else None,
                ingredients=[parse_ingredient(line) for line in ingredients],
                steps=[
                    Step(step_number=i + 1, instruction=text)
                    for i, text in enumerate(instructions)
                ],
                prep_time_minutes=duration_minutes(raw.get("prepTime")),
                cook_time_minutes=duration_minutes(raw.get("cookTime")),
                servings=int(servings[0]) if servings else None,
                image_url=image,
                nutrition=nutrition,
                source_url=page.url,
                source_name=urlsplit(page.url).hostname,
            )
            return recipe
        except (ValidationError, ValueError, TypeError, AttributeError):
            continue
    return None


def youtube_url(url: str) -> str | None:
    parsed = urlsplit(url)
    if parsed.hostname == "youtu.be":
        video_id = parsed.path.strip("/")
    elif parsed.hostname in {
        "youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com"
    }:
        if parsed.path == "/watch":
            video_id = parse_qs(parsed.query).get("v", [""])[0]
        elif parsed.path.startswith(("/shorts/", "/embed/")):
            video_id = parsed.path.split("/")[2]
        else:
            video_id = ""
    else:
        return None
    if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
        raise SourceError("Use a YouTube video link, not a playlist or channel.")
    return f"https://www.youtube.com/watch?v={video_id}"


class RecipeSourceReader:
    def __init__(self, config: Settings, extractor: RecipeTextExtractor | None = None):
        self.config = config
        self.extractor = extractor or RecipeTextExtractor(config)
        self.fetcher = PageFetcher(config)

    async def from_url(self, url: str) -> tuple[ExtractedRecipe, str]:
        validate_source_url(url)
        video = youtube_url(url)
        if video:
            # Fail before downloading audio when the extraction service cannot be used.
            if not self.config.anthropic_api_key:
                raise ProviderNotConfiguredError("Set ANTHROPIC_API_KEY to import videos.")
            text = await self._transcribe(video)
            extracted = await self.extractor.extract(text)
            extracted.recipe.source_url = video
            extracted.recipe.video_url = video
            extracted.recipe.source_name = "YouTube"
            video_id = parse_qs(urlsplit(video).query).get("v", [""])[0]
            if video_id and not extracted.recipe.image_url:
                extracted.recipe.image_url = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
            return extracted, "youtube"
        page = await self.fetcher.fetch(url)
        recipe = await asyncio.to_thread(structured_recipe, page)
        if recipe is not None:
            return ExtractedRecipe(recipe=recipe, confidence=1), "json-ld"
        article = await asyncio.to_thread(lambda: clean_text(Document(page.html).summary()))
        extracted = await self.extractor.extract(article)
        extracted.recipe.source_url = page.url
        extracted.recipe.source_name = urlsplit(page.url).hostname
        if not extracted.recipe.image_url:
            extracted.recipe.image_url = extract_meta_image(page.html)
        return extracted, "blog"

    async def from_text(self, text: str, source_name: str) -> tuple[ExtractedRecipe, str]:
        extracted = await self.extractor.extract(text)
        # Source credit is user supplied, never a URL invented by the model.
        extracted.recipe.source_url = None
        extracted.recipe.source_name = source_name
        extracted.recipe.video_url = None
        return extracted, "manual"

    async def _transcribe(self, url: str) -> str:
        with TemporaryDirectory(prefix="idunn-video-") as directory:
            output = Path(directory) / "transcript.txt"
            process = await asyncio.create_subprocess_exec(
                sys.executable, "-m", "backend.services.youtube_transcribe",
                url, str(output), self.config.whisper_model,
                str(self.config.video_max_seconds), str(self.config.video_max_bytes),
                str(int(self.config.whisper_local_files_only)),
                stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE,
            )
            try:
                _, stderr = await asyncio.wait_for(
                    process.communicate(), self.config.video_timeout_seconds
                )
            except (TimeoutError, asyncio.CancelledError) as exc:
                if process.returncode is None:
                    process.kill()
                await process.communicate()
                if isinstance(exc, asyncio.CancelledError):
                    raise
                raise SourceError("Video import timed out; try a shorter video.") from exc
            if process.returncode:
                detail = stderr.decode(errors="replace").strip()[-400:]
                raise SourceError(f"Video transcription failed. {detail}")
            return await asyncio.to_thread(output.read_text, encoding="utf-8")
