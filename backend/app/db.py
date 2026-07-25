from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from app.config import (
    DB_PATH,
    INBOX_PATH,
    KL_DATA_DIR,
    RECIPES_PATH,
    ensure_app_dirs,
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS recipes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    image_path TEXT NOT NULL UNIQUE,
    filename TEXT NOT NULL,
    title TEXT,
    servings TEXT,
    source TEXT,
    notes TEXT,
    ocr_text TEXT,
    status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft', 'reviewed')),
    width INTEGER,
    height INTEGER,
    sha256 TEXT,
    mtime REAL NOT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_recipes_status ON recipes(status);
CREATE INDEX IF NOT EXISTS idx_recipes_title ON recipes(title);
CREATE INDEX IF NOT EXISTS idx_recipes_sha256 ON recipes(sha256);

CREATE TABLE IF NOT EXISTS recipe_ingredients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recipe_id INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    position INTEGER NOT NULL DEFAULT 0,
    text TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_recipe_ingredients_recipe ON recipe_ingredients(recipe_id);

CREATE TABLE IF NOT EXISTS recipe_steps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recipe_id INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    position INTEGER NOT NULL DEFAULT 0,
    text TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_recipe_steps_recipe ON recipe_steps(recipe_id);

CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS recipe_tags (
    recipe_id INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (recipe_id, tag_id)
);

CREATE INDEX IF NOT EXISTS idx_recipe_tags_tag ON recipe_tags(tag_id);
"""


def default_config() -> dict[str, str]:
    return {
        "inbox_path": str(INBOX_PATH),
        "recipes_path": str(RECIPES_PATH),
    }


def init_db() -> None:
    ensure_app_dirs()
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        _migrate_schema(conn)
        for key, value in default_config().items():
            conn.execute(
                "INSERT OR IGNORE INTO config (key, value) VALUES (?, ?)",
                (key, value),
            )
        # If a stored path is missing (e.g. host path in a Docker mount),
        # fall back to the env-derived default so scan can find inbox files.
        cfg = get_config(conn)
        defaults = default_config()
        fixes: dict[str, str] = {}
        for key in ("inbox_path", "recipes_path"):
            current = Path(cfg.get(key, ""))
            fallback = Path(defaults[key])
            if (not current.exists()) and fallback.exists():
                fixes[key] = str(fallback)
        if fixes:
            update_config(conn, fixes)
        cleanup_orphan_junction_rows(conn)
        conn.commit()


def _migrate_schema(conn: sqlite3.Connection) -> None:
    """Placeholder for future ALTER TABLE migrations."""
    _ = conn


def cleanup_orphan_junction_rows(conn: sqlite3.Connection) -> None:
    conn.execute(
        "DELETE FROM recipe_tags WHERE recipe_id NOT IN (SELECT id FROM recipes)"
    )
    conn.execute(
        "DELETE FROM recipe_ingredients WHERE recipe_id NOT IN (SELECT id FROM recipes)"
    )
    conn.execute(
        "DELETE FROM recipe_steps WHERE recipe_id NOT IN (SELECT id FROM recipes)"
    )


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    KL_DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 10000")
    try:
        yield conn
    finally:
        conn.close()


def get_config(conn: sqlite3.Connection) -> dict[str, str]:
    rows = conn.execute("SELECT key, value FROM config").fetchall()
    cfg = default_config()
    cfg.update({row["key"]: row["value"] for row in rows})
    return cfg


def update_config(conn: sqlite3.Connection, updates: dict[str, str]) -> dict[str, str]:
    for key, value in updates.items():
        conn.execute(
            """
            INSERT INTO config (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value
            """,
            (key, value),
        )
    conn.commit()
    return get_config(conn)


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return dict(row)
