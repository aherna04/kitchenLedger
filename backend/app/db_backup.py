from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from app.config import BACKUPS_DIR, DB_PATH, ensure_app_dirs
from app.db import get_conn


def create_backup() -> dict:
    ensure_app_dirs()
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"index-{stamp}.db"
    dest = BACKUPS_DIR / filename
    with get_conn() as conn:
        # Online backup API via sqlite3 backup if available; fall back to copy
        dest_conn = __import__("sqlite3").connect(dest)
        try:
            conn.backup(dest_conn)
        finally:
            dest_conn.close()
    stat = dest.stat()
    return {
        "path": str(dest),
        "filename": filename,
        "size_bytes": stat.st_size,
        "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
    }


def list_backups() -> list[dict]:
    ensure_app_dirs()
    items: list[dict] = []
    for path in sorted(BACKUPS_DIR.glob("index-*.db"), reverse=True):
        stat = path.stat()
        items.append(
            {
                "path": str(path),
                "filename": path.name,
                "size_bytes": stat.st_size,
                "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            }
        )
    return items


def copy_db_fallback(dest: Path) -> None:
    """Unused helper kept for scripts that prefer a cold copy."""
    shutil.copy2(DB_PATH, dest)
