"""OCR helpers for scanned recipe images.

Handwritten OCR is imperfect; results are drafts for the user to correct.
"""

from __future__ import annotations

import re
from pathlib import Path

from PIL import Image, ImageOps

try:
    import pytesseract
except ImportError:  # pragma: no cover
    pytesseract = None  # type: ignore[assignment]

INGREDIENT_HINTS = re.compile(
    r"\b(cup|cups|tsp|tbsp|teaspoon|tablespoon|oz|ounce|lb|pound|"
    r"gram|grams|ml|liter|litre|pinch|dash|clove|egg|eggs|"
    r"flour|sugar|butter|salt|pepper|oil|milk|water|vanilla|"
    r"baking|soda|powder|yeast)\b",
    re.I,
)
DIRECTION_HINTS = re.compile(
    r"\b(mix|stir|bake|cook|heat|preheat|whisk|fold|pour|add|"
    r"combine|cream|beat|simmer|boil|roast|grill|fry|saute|"
    r"chop|slice|dice|until|minutes|oven|pan|bowl|rack)\b",
    re.I,
)
SECTION_INGREDIENTS = re.compile(r"^\s*ingredients?\s*:?\s*$", re.I)
SECTION_DIRECTIONS = re.compile(
    r"^\s*(directions?|instructions?|method|steps?)\s*:?\s*$", re.I
)
NUMBERED_STEP = re.compile(r"^\s*\d+[\.\)]\s+")


def extract_ocr_text(path: Path) -> str:
    if pytesseract is None:
        return ""
    try:
        with Image.open(path) as img:
            img = ImageOps.exif_transpose(img)
            img = img.convert("RGB")
            text = pytesseract.image_to_string(img)
            return text.strip()
    except Exception:
        return ""


def _clean_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw in text.splitlines():
        line = re.sub(r"\s+", " ", raw).strip()
        if not line:
            continue
        lines.append(line)
    return lines


def guess_title(lines: list[str]) -> str | None:
    for line in lines[:5]:
        if SECTION_INGREDIENTS.match(line) or SECTION_DIRECTIONS.match(line):
            continue
        if len(line) < 3 or len(line) > 80:
            continue
        if INGREDIENT_HINTS.search(line) and re.search(r"\d", line):
            continue
        return line
    return None


def split_recipe_lines(ocr_text: str) -> dict[str, list[str] | str | None]:
    """Naively split OCR text into title, ingredients, and direction lines."""
    lines = _clean_lines(ocr_text)
    if not lines:
        return {"title": None, "ingredients": [], "steps": []}

    title = guess_title(lines)
    mode: str | None = None
    ingredients: list[str] = []
    steps: list[str] = []

    for line in lines:
        if title and line == title:
            continue
        if SECTION_INGREDIENTS.match(line):
            mode = "ingredients"
            continue
        if SECTION_DIRECTIONS.match(line):
            mode = "steps"
            continue

        if mode == "ingredients":
            ingredients.append(line)
            continue
        if mode == "steps":
            steps.append(NUMBERED_STEP.sub("", line).strip() or line)
            continue

        # No section headers yet — heuristic classification
        if NUMBERED_STEP.match(line) or DIRECTION_HINTS.search(line):
            steps.append(NUMBERED_STEP.sub("", line).strip() or line)
        elif INGREDIENT_HINTS.search(line) or re.match(r"^[\d¼½¾⅓⅔⅛⅜⅝⅞/.\s]", line):
            ingredients.append(line)
        elif not ingredients and not steps:
            # Early orphan lines often belong with ingredients on handwritten cards
            ingredients.append(line)
        else:
            steps.append(line)

    return {
        "title": title,
        "ingredients": ingredients,
        "steps": steps,
    }
