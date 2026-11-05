"""WhatsApp and printable text export formatting engine.

Generates structured, emoji-rich markdown formatted for WhatsApp sharing with domestic
cooks and household members, as well as print-optimized text for kitchen displays.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import quote

if TYPE_CHECKING:
    from ..models.planner import WeeklyMealPlan
    from ..models.shopping import AggregatedShoppingItem, ShoppingListItem

# Keyword sets for categorizing groceries into familiar Indian kitchen groups.
PRODUCE_KEYWORDS = (
    "onion pyaz tomato tamatar potato aloo palak spinach ginger adrak garlic lahsun "
    "coriander dhaniya chilli mirch carrot gajar peas matar gobi cauliflower bhindi "
    "okra lemon nimbu curry leaves methi"
).split()

DAIRY_KEYWORDS = (
    "paneer milk doodh curd dahi yogurt butter makhan ghee cheese egg anda chicken mutton fish"
).split()

SPICE_KEYWORDS = (
    "haldi turmeric jeera cumin chilli powder garam masala salt namak rai mustard "
    "hing cardamom elaichi clove cinnamon"
).split()

STAPLE_KEYWORDS = (
    "atta flour rice chawal dal lentil oil tel sugar cheeni poha sooji rava besan chana rajma bread"
).split()


def categorize_ingredient(name: str) -> str:
    """Classify ingredient into familiar grocery category.

    Args:
        name: Raw ingredient name string.

    Returns:
        Identified category key string.
    """
    # Lowercase token search handles regional recipe naming variations.
    lower = name.lower()
    for kw in PRODUCE_KEYWORDS:
        if kw in lower:
            return "produce"
    for kw in DAIRY_KEYWORDS:
        if kw in lower:
            return "dairy"
    for kw in SPICE_KEYWORDS:
        if kw in lower:
            return "spices"
    for kw in STAPLE_KEYWORDS:
        if kw in lower:
            return "staples"
    return "other"


def format_whatsapp_shopping_list(
    items: list[ShoppingListItem | AggregatedShoppingItem],
    title: str = "Iðunn Weekly Grocery List",
) -> str:
    """Format shopping list into structured WhatsApp text message.

    Args:
        items: List of shopping list or pantry gap items.
        title: Header title for message.

    Returns:
        Formatted WhatsApp text string with bold headings and emoji bullets.
    """
    # Return quick placeholder if shopping list is empty.
    if not items:
        return f"🛒 *{title}*\n\n_All items in stock! No groceries needed._"

    # Bucket items into distinct shopping aisles.
    buckets: dict[str, list[str]] = {
        "produce": [],
        "dairy": [],
        "staples": [],
        "spices": [],
        "other": [],
    }

    for item in items:
        # Extract common name, quantity, and unit attributes.
        name = item.name
        # Format quantity cleanly: omit decimals if whole integer.
        qty = getattr(item, "gap_quantity", getattr(item, "quantity", 1.0))
        unit = getattr(item, "unit", "")
        qty_str = f"{int(qty)}" if qty == int(qty) else f"{qty:.1f}"

        line = f"• {name.title()} — {qty_str} {unit}".strip()
        cat = categorize_ingredient(name)
        buckets[cat].append(line)

    lines: list[str] = [f"🛒 *{title}*"]

    category_headers = (
        ("produce", "🥬 *Produce:*"),
        ("dairy", "🥛 *Dairy & Proteins:*"),
        ("staples", "🌾 *Staples & Grains:*"),
        ("spices", "🌶️ *Spices & Seasonings:*"),
        ("other", "📦 *Other Essentials:*"),
    )

    # Append non-empty categories with proper spacing.
    for key, header in category_headers:
        group_items = buckets[key]
        if group_items:
            lines.append("")
            lines.append(header)
            lines.extend(group_items)

    lines.append("")
    lines.append("_Generated with Iðunn Kitchen OS_")
    return "\n".join(lines)


def format_whatsapp_meal_plan(plan: WeeklyMealPlan) -> str:
    """Format 7-day meal plan into clean WhatsApp schedule.

    Args:
        plan: Weekly meal plan record.

    Returns:
        Formatted WhatsApp schedule text.
    """
    # Build schedule header with active date range.
    lines: list[str] = [f"📅 *Iðunn Weekly Meal Plan ({plan.week_start_date})*"]

    slot_emojis = {
        "breakfast": "☕ Breakfast",
        "lunch": "🍲 Lunch",
        "dinner": "🍽️ Dinner",
        "snack": "🥪 Snack",
    }

    # Group meals by day array.
    days = getattr(plan, "days", [])
    for day in days:
        day_name = getattr(day, "day_of_week", "Day")
        slots = getattr(day, "slots", [])
        day_lines: list[str] = []
        for slot in slots:
            title = getattr(slot, "custom_title", None) or getattr(slot, "recipe_title", None)
            if not title:
                continue
            meal_type_str = str(getattr(slot, "meal_type", "")).lower()
            if "." in meal_type_str:
                meal_type_str = meal_type_str.split(".")[-1]
            label = slot_emojis.get(meal_type_str, meal_type_str.capitalize() or "Meal")
            servings = getattr(slot, "servings", 1.0)
            servings_note = f" ({servings} servings)" if servings != 1.0 else ""
            day_lines.append(f"• {label}: {title}{servings_note}")

        if day_lines:
            lines.append("")
            lines.append(f"*{day_name.capitalize()}:*")
            lines.extend(day_lines)

    lines.append("")
    lines.append("_Generated with Iðunn Kitchen OS_")
    return "\n".join(lines)


def generate_whatsapp_share_url(text: str) -> str:
    """Generate universal WhatsApp web and mobile deep link.

    Args:
        text: Pre-formatted message body.

    Returns:
        Universal WhatsApp sharing URL.
    """
    # Quote text payload to construct valid HTTP query parameter.
    return f"https://api.whatsapp.com/send?text={quote(text)}"
