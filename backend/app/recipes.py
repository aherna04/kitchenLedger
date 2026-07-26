from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path

from app.db import get_config
from app.metadata import generate_thumbnail
from app.tags import get_recipe_tags, set_recipe_tags


def get_ingredients(conn: sqlite3.Connection, recipe_id: int) -> list[dict]:
    rows = conn.execute(
        """
        SELECT id, position, text FROM recipe_ingredients
        WHERE recipe_id = ?
        ORDER BY position, id
        """,
        (recipe_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_steps(conn: sqlite3.Connection, recipe_id: int) -> list[dict]:
    rows = conn.execute(
        """
        SELECT id, position, text FROM recipe_steps
        WHERE recipe_id = ?
        ORDER BY position, id
        """,
        (recipe_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def enrich_recipe(conn: sqlite3.Connection, row: sqlite3.Row | dict) -> dict:
    data = dict(row)
    recipe_id = data["id"]
    data["ingredients"] = get_ingredients(conn, recipe_id)
    data["steps"] = get_steps(conn, recipe_id)
    data["tags"] = get_recipe_tags(conn, recipe_id)
    return data


def get_recipe(conn: sqlite3.Connection, recipe_id: int) -> dict | None:
    row = conn.execute(
        "SELECT * FROM recipes WHERE id = ?", (recipe_id,)
    ).fetchone()
    if not row:
        return None
    return enrich_recipe(conn, row)


def replace_ingredients(
    conn: sqlite3.Connection, recipe_id: int, lines: list[str]
) -> list[dict]:
    conn.execute("DELETE FROM recipe_ingredients WHERE recipe_id = ?", (recipe_id,))
    for i, text in enumerate(lines):
        cleaned = text.strip()
        if not cleaned:
            continue
        conn.execute(
            """
            INSERT INTO recipe_ingredients (recipe_id, position, text)
            VALUES (?, ?, ?)
            """,
            (recipe_id, i, cleaned),
        )
    conn.execute(
        "UPDATE recipes SET updated_at = datetime('now') WHERE id = ?",
        (recipe_id,),
    )
    conn.commit()
    return get_ingredients(conn, recipe_id)


def replace_steps(
    conn: sqlite3.Connection, recipe_id: int, lines: list[str]
) -> list[dict]:
    conn.execute("DELETE FROM recipe_steps WHERE recipe_id = ?", (recipe_id,))
    for i, text in enumerate(lines):
        cleaned = text.strip()
        if not cleaned:
            continue
        conn.execute(
            """
            INSERT INTO recipe_steps (recipe_id, position, text)
            VALUES (?, ?, ?)
            """,
            (recipe_id, i, cleaned),
        )
    conn.execute(
        "UPDATE recipes SET updated_at = datetime('now') WHERE id = ?",
        (recipe_id,),
    )
    conn.commit()
    return get_steps(conn, recipe_id)


def _unique_dest(dest: Path) -> Path:
    if not dest.exists():
        return dest
    stem = dest.stem
    suffix = dest.suffix
    parent = dest.parent
    n = 1
    while True:
        candidate = parent / f"{stem}-{n}{suffix}"
        if not candidate.exists():
            return candidate
        n += 1


def _path_under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def move_scan_to_recipes(conn: sqlite3.Connection, recipe_id: int) -> None:
    """If the scan file still lives under inbox/, move it to recipes/."""
    row = conn.execute(
        "SELECT image_path, filename FROM recipes WHERE id = ?", (recipe_id,)
    ).fetchone()
    if not row:
        return
    cfg = get_config(conn)
    inbox = Path(cfg["inbox_path"])
    recipes_dir = Path(cfg["recipes_path"])
    src = Path(row["image_path"])
    if not src.exists() or not _path_under(src, inbox):
        return

    recipes_dir.mkdir(parents=True, exist_ok=True)
    dest = _unique_dest(recipes_dir / src.name)
    shutil.move(str(src), str(dest))
    mtime = dest.stat().st_mtime
    conn.execute(
        """
        UPDATE recipes SET
            image_path = ?, filename = ?, mtime = ?,
            updated_at = datetime('now')
        WHERE id = ?
        """,
        (str(dest), dest.name, mtime, recipe_id),
    )
    conn.commit()
    generate_thumbnail(dest, recipe_id, mtime)


def attach_hero_from_recipe(
    conn: sqlite3.Connection, target_id: int, source_recipe_id: int
) -> dict:
    if target_id == source_recipe_id:
        raise ValueError("Cannot attach a recipe as its own hero")

    target = conn.execute(
        "SELECT * FROM recipes WHERE id = ?", (target_id,)
    ).fetchone()
    source = conn.execute(
        "SELECT * FROM recipes WHERE id = ?", (source_recipe_id,)
    ).fetchone()
    if not target:
        raise LookupError("Target recipe not found")
    if not source:
        raise LookupError("Source recipe not found")

    src_path = Path(source["image_path"])
    if not src_path.exists():
        raise FileNotFoundError("Source image missing on disk")

    cfg = get_config(conn)
    hero_dir = Path(cfg["hero_path"])
    hero_dir.mkdir(parents=True, exist_ok=True)

    stem = Path(target["filename"]).stem
    dest = hero_dir / f"{stem}{src_path.suffix.lower()}"
    if dest.exists() and dest.resolve() != src_path.resolve():
        dest.unlink()
    shutil.move(str(src_path), str(dest))
    mtime = dest.stat().st_mtime

    conn.execute(
        """
        UPDATE recipes SET
            hero_filename = ?, hero_path = ?, hero_mtime = ?,
            updated_at = datetime('now')
        WHERE id = ?
        """,
        (dest.name, str(dest), mtime, target_id),
    )
    # Drop orphan draft (and its ingredients/steps/tags via CASCADE)
    conn.execute("DELETE FROM recipes WHERE id = ?", (source_recipe_id,))
    conn.commit()
    generate_thumbnail(dest, target_id, mtime, variant="hero")
    recipe = get_recipe(conn, target_id)
    if not recipe:
        raise LookupError("Target recipe not found after attach")
    return recipe


def update_recipe(
    conn: sqlite3.Connection,
    recipe_id: int,
    *,
    title: str | None = None,
    servings: str | None = None,
    source: str | None = None,
    notes: str | None = None,
    status: str | None = None,
    tag_ids: list[int] | None = None,
) -> dict | None:
    existing = conn.execute(
        "SELECT id, status FROM recipes WHERE id = ?", (recipe_id,)
    ).fetchone()
    if not existing:
        return None

    prev_status = existing["status"]
    fields: list[str] = []
    params: list[object] = []
    if title is not None:
        fields.append("title = ?")
        params.append(title.strip() or None)
    if servings is not None:
        fields.append("servings = ?")
        params.append(servings.strip() or None)
    if source is not None:
        fields.append("source = ?")
        params.append(source.strip() or None)
    if notes is not None:
        fields.append("notes = ?")
        params.append(notes.strip() or None)
    if status is not None:
        fields.append("status = ?")
        params.append(status)

    if fields:
        fields.append("updated_at = datetime('now')")
        params.append(recipe_id)
        conn.execute(
            f"UPDATE recipes SET {', '.join(fields)} WHERE id = ?",
            params,
        )
        conn.commit()

    if tag_ids is not None:
        set_recipe_tags(conn, recipe_id, tag_ids)

    # Reviewed scans belong in recipes/. Fire on the transition and also
    # self-heal any already-reviewed recipe whose scan is still in inbox.
    effective_status = status if status is not None else prev_status
    if effective_status == "reviewed":
        move_scan_to_recipes(conn, recipe_id)

    return get_recipe(conn, recipe_id)


def list_recipes(
    conn: sqlite3.Connection,
    *,
    tag_ids: list[int] | None = None,
    status: str | None = None,
    q: str | None = None,
    page: int = 1,
    page_size: int = 48,
) -> tuple[list[dict], int]:
    clauses: list[str] = ["1=1"]
    params: list[object] = []

    if status:
        clauses.append("r.status = ?")
        params.append(status)

    if tag_ids:
        for tid in tag_ids:
            clauses.append(
                "r.id IN (SELECT recipe_id FROM recipe_tags WHERE tag_id = ?)"
            )
            params.append(tid)

    if q and q.strip():
        like = f"%{q.strip()}%"
        clauses.append(
            """
            (
                r.title LIKE ?
                OR r.notes LIKE ?
                OR r.source LIKE ?
                OR EXISTS (
                    SELECT 1 FROM recipe_ingredients ri
                    WHERE ri.recipe_id = r.id AND ri.text LIKE ?
                )
                OR EXISTS (
                    SELECT 1 FROM recipe_steps rs
                    WHERE rs.recipe_id = r.id AND rs.text LIKE ?
                )
            )
            """
        )
        params.extend([like, like, like, like, like])

    where = " AND ".join(clauses)
    total = conn.execute(
        f"SELECT COUNT(*) FROM recipes r WHERE {where}", params
    ).fetchone()[0]

    page = max(1, page)
    page_size = max(1, min(page_size, 200))
    offset = (page - 1) * page_size

    rows = conn.execute(
        f"""
        SELECT r.* FROM recipes r
        WHERE {where}
        ORDER BY COALESCE(r.updated_at, r.created_at) DESC, r.id DESC
        LIMIT ? OFFSET ?
        """,
        [*params, page_size, offset],
    ).fetchall()

    items = [enrich_recipe(conn, row) for row in rows]
    return items, total
