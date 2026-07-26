from __future__ import annotations

from pathlib import Path
import os

KL_ROOT = Path(os.environ.get("KL_ROOT", "/media")).resolve()
KL_DATA_DIR = Path(
    os.environ.get("KL_DATA_DIR", str(KL_ROOT / ".kitchenLedger"))
).resolve()

INBOX_PATH = KL_ROOT / "inbox"
RECIPES_PATH = KL_ROOT / "recipes"
HERO_PATH = KL_ROOT / "hero"

DB_PATH = KL_DATA_DIR / "index.db"
BACKUPS_DIR = KL_DATA_DIR / "backups"
THUMBS_DIR = KL_DATA_DIR / "thumbs"

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".tiff", ".tif", ".webp"}
SUPPORTED_EXTENSIONS = IMAGE_EXTENSIONS

IMAGE_MIME_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".heic": "image/heic",
    ".heif": "image/heif",
    ".tiff": "image/tiff",
    ".tif": "image/tiff",
    ".webp": "image/webp",
}

THUMB_SIZE = 400


def mime_type_for_path(path: Path | str) -> str:
    suffix = Path(path).suffix.lower()
    return IMAGE_MIME_TYPES.get(suffix, "application/octet-stream")


def ensure_media_dirs() -> None:
    for path in (INBOX_PATH, RECIPES_PATH, HERO_PATH):
        path.mkdir(parents=True, exist_ok=True)


def ensure_app_dirs() -> None:
    KL_DATA_DIR.mkdir(parents=True, exist_ok=True)
    THUMBS_DIR.mkdir(parents=True, exist_ok=True)
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
