from __future__ import annotations

import hashlib
import re
from pathlib import Path

from PIL import Image, ImageOps

try:
    from pillow_heif import register_heif_opener

    register_heif_opener()
except ImportError:
    pass

from app.config import SUPPORTED_EXTENSIONS, THUMB_SIZE, THUMBS_DIR

THUMB_CACHE_VERSION = "v1"


def slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_-]+", "-", slug)
    return slug.strip("-") or "tag"


def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def extract_image_info(path: Path) -> dict:
    stat = path.stat()
    width = None
    height = None
    try:
        with Image.open(path) as img:
            img = ImageOps.exif_transpose(img)
            width, height = img.size
    except Exception:
        pass
    return {
        "width": width,
        "height": height,
        "size": stat.st_size,
        "mtime": stat.st_mtime,
    }


def thumb_cache_path(recipe_id: int, mtime: float, variant: str = "") -> Path:
    suffix = f"_{variant}" if variant else ""
    return THUMBS_DIR / f"{recipe_id}_{int(mtime)}_{THUMB_CACHE_VERSION}{suffix}.jpg"


def generate_thumbnail(
    path: Path, recipe_id: int, mtime: float, variant: str = ""
) -> Path:
    out = thumb_cache_path(recipe_id, mtime, variant=variant)
    if out.exists():
        return out
    THUMBS_DIR.mkdir(parents=True, exist_ok=True)
    with Image.open(path) as img:
        img = ImageOps.exif_transpose(img)
        img = img.convert("RGB")
        img.thumbnail((THUMB_SIZE, THUMB_SIZE))
        img.save(out, "JPEG", quality=85)
    return out


def iter_image_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    files: list[Path] = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if p.name.startswith("."):
            continue
        if p.suffix.lower() in SUPPORTED_EXTENSIONS:
            files.append(p)
    return sorted(files)
