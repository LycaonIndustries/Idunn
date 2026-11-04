"""Algorithmic culinary substitution engine for Iðunn Kitchen OS.

Provides zero-AI deterministic functional substitutions based on ingredient roles.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from backend.models.cook_ai import SubstitutionSuggestion

if TYPE_CHECKING:
    from backend.models.inventory import Item

# Static culinary ontology tuples: (substitute, category, ratio, notes)
CULINARY_SUBSTITUTION_DATA: dict[str, list[tuple[str, str, str, str]]] = {
    # Acids
    "lemon juice": [
        ("lime juice", "acid", "1:1", "Citrus acidity profile"),
        ("white vinegar", "acid", "1:0.5", "More pungent; use half amount"),
        ("apple cider vinegar", "acid", "1:0.75", "Fruity acidity for dressings"),
    ],
    "lime juice": [
        ("lemon juice", "acid", "1:1", "Citrus acidity profile"),
        ("white vinegar", "acid", "1:0.5", "Use half amount in marinades"),
    ],
    "white vinegar": [
        ("apple cider vinegar", "acid", "1:1", "Slightly fruitier note"),
        ("lemon juice", "acid", "1:1", "Bright citrus equivalent"),
        ("rice vinegar", "acid", "1:1", "Mild acidity for dressings"),
    ],
    "apple cider vinegar": [
        ("white vinegar", "acid", "1:1", "Neutral acid replacement"),
        ("lemon juice", "acid", "1:1", "Citrus brightness replacement"),
    ],
    # Cooking Fats & Mediums
    "butter": [
        ("ghee", "fat", "1:0.8", "Clarified butter; high smoke point"),
        ("olive oil", "fat", "1:0.75", "Healthy fat cooking alternative"),
        ("coconut oil", "fat", "1:1", "Solid at room temp; great in baking"),
    ],
    "olive oil": [
        ("vegetable oil", "fat", "1:1", "Neutral cooking oil substitute"),
        ("canola oil", "fat", "1:1", "Neutral high-heat oil"),
        ("butter", "fat", "1:1.2", "Adds richness to pan sauteing"),
    ],
    "ghee": [
        ("butter", "fat", "1:1.2", "Standard butter with milk solids"),
        ("coconut oil", "fat", "1:1", "Plant-based high-heat fat"),
    ],
    # Dairy & Creams
    "heavy cream": [
        ("sour cream", "dairy", "1:1", "Adds mild tanginess to sauces"),
        ("greek yogurt", "dairy", "1:1", "Savory high-protein substitute"),
        ("coconut cream", "dairy", "1:1", "Plant-based rich creamy substitute"),
        ("whole milk", "dairy", "1:1", "Whisk with 1 tbsp melted butter"),
    ],
    "sour cream": [
        ("greek yogurt", "dairy", "1:1", "Identical consistency and tang"),
        ("plain yogurt", "dairy", "1:1", "Slightly thinner texture"),
    ],
    "greek yogurt": [
        ("plain yogurt", "dairy", "1:1", "Strain through cloth for thickness"),
        ("sour cream", "dairy", "1:1", "Richer fat content alternative"),
    ],
    # Starches & Thickeners
    "cornstarch": [
        ("all-purpose flour", "thickener", "1:2", "Cook 2 min to remove raw taste"),
        ("arrowroot", "thickener", "1:1", "Clear glossy finish"),
        ("potato starch", "thickener", "1:1", "High starch slurry equivalent"),
    ],
    "all-purpose flour": [
        ("cornstarch", "thickener", "2:1", "Sauce and gravy thickener"),
    ],
    # Aromatics
    "shallot": [
        ("yellow onion", "aromatic", "1:1", "Add pinch of minced garlic"),
        ("red onion", "aromatic", "1:1", "Mild sweetness when cooked"),
        ("scallion", "aromatic", "1:1", "Use white base for cooking"),
    ],
    "yellow onion": [
        ("red onion", "aromatic", "1:1", "Sweet and colorful alternative"),
        ("shallot", "aromatic", "1:1", "Delicate flavor profile"),
        ("scallion", "aromatic", "1:1", "Fast-cooking aromatic substitute"),
    ],
    "garlic": [
        ("garlic powder", "aromatic", "1 clove:0.25 tsp", "Dry concentrated seasoning"),
        ("shallot", "aromatic", "1 clove:1 shallot", "Mild onion-garlic combination"),
    ],
    # Sweeteners
    "honey": [
        ("maple syrup", "sweetener", "1:1", "Plant-derived liquid sweetener"),
        ("granulated sugar", "sweetener", "1:1.25", "Increase recipe liquid slightly"),
        ("brown sugar", "sweetener", "1:1", "Adds molasses depth"),
    ],
    "granulated sugar": [
        ("brown sugar", "sweetener", "1:1", "Caramel undertone replacement"),
        ("honey", "sweetener", "1:0.75", "Reduce recipe liquid by 2 tbsp"),
    ],
    # Binders
    "egg": [
        ("flax egg", "binder", "1 egg:1 tbsp flax + 3 tbsp water", "Rest 5 min until gel forms"),
        ("applesauce", "binder", "1 egg:0.25 cup", "Moisture and sweetness in baking"),
        ("plain yogurt", "binder", "1 egg:0.25 cup", "Moisture binder in quick breads"),
    ],
}


class SubstitutionEngine:
    """Deterministic culinary substitution and pantry alignment engine."""

    @staticmethod
    def normalize_ingredient_name(name: str) -> str:
        """Sanitize ingredient name for graph key lookup.

        Args:
            name: Raw ingredient string from user input or recipe.

        Returns:
            Normalized lowercase single-space string.
        """
        # Remove non-alphanumeric punctuation and lower string.
        cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", name).lower().strip()
        return " ".join(cleaned.split())

    @classmethod
    def get_culinary_substitutions(cls, target_ingredient: str) -> list[SubstitutionSuggestion]:
        """Find functional culinary replacements for an ingredient from static ontology.

        Args:
            target_ingredient: Name of ingredient needing substitute.

        Returns:
            List of SubstitutionSuggestion records.
        """
        norm_target = cls.normalize_ingredient_name(target_ingredient)

        # Check exact key matches first.
        candidates: list[tuple[str, str, str, str]] = []
        if norm_target in CULINARY_SUBSTITUTION_DATA:
            candidates = CULINARY_SUBSTITUTION_DATA[norm_target]
        else:
            # Check partial or substring matches in ontology keys.
            for key, replacements in CULINARY_SUBSTITUTION_DATA.items():
                if key in norm_target or norm_target in key:
                    candidates = replacements
                    break

        # Map raw candidate records into typed schema.
        results: list[SubstitutionSuggestion] = []
        for sub_name, category, ratio, notes in candidates:
            results.append(
                SubstitutionSuggestion(
                    target_ingredient=target_ingredient,
                    substitute_name=sub_name,
                    category=category,
                    ratio=ratio,
                    in_pantry=False,
                    notes=notes,
                )
            )
        return results

    @classmethod
    def find_pantry_substitutions(
        cls,
        target_ingredient: str,
        pantry_inventory: list[str] | list[Item],
    ) -> list[SubstitutionSuggestion]:
        """Find substitutions prioritized by current active pantry stock.

        Args:
            target_ingredient: The missing or target ingredient name.
            pantry_inventory: Collection of inventory items or string item names.

        Returns:
            List of substitutions with available pantry items sorted first.
        """
        suggestions = cls.get_culinary_substitutions(target_ingredient)
        if not suggestions:
            return []

        # Extract normalized strings from inventory items.
        pantry_names: set[str] = set()
        for elem in pantry_inventory:
            raw_name = elem.name if hasattr(elem, "name") else str(elem)
            pantry_names.add(cls.normalize_ingredient_name(raw_name))

        # Check whether each replacement candidate exists in pantry stock.
        for sug in suggestions:
            sug_norm = cls.normalize_ingredient_name(sug.substitute_name)
            # Detect exact match or substring token overlap.
            tokens = sug_norm.split()
            is_present = any(
                sug_norm in p_name or p_name in sug_norm or any(tok in p_name for tok in tokens)
                for p_name in pantry_names
            )
            sug.in_pantry = is_present

        # Sort so that items present in pantry appear first.
        return sorted(suggestions, key=lambda s: not s.in_pantry)
