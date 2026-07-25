from __future__ import annotations

import sqlite3

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
        "SELECT id FROM recipes WHERE id = ?", (recipe_id,)
    ).fetchone()
    if not existing:
        return None

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
