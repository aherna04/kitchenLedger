from __future__ import annotations

import sqlite3

from app.metadata import slugify


def _unique_slug(conn: sqlite3.Connection, base_slug: str) -> str:
    slug = base_slug
    n = 1
    while conn.execute("SELECT 1 FROM tags WHERE slug = ?", (slug,)).fetchone():
        slug = f"{base_slug}-{n}"
        n += 1
    return slug


def _recipe_count_sql() -> str:
    return """
        SELECT t.*,
            COUNT(DISTINCT r.id) AS recipe_count
        FROM tags t
        LEFT JOIN recipe_tags rt ON rt.tag_id = t.id
        LEFT JOIN recipes r ON r.id = rt.recipe_id
    """


def list_tags(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        f"""
        {_recipe_count_sql()}
        GROUP BY t.id
        ORDER BY t.name
        """
    ).fetchall()
    return [dict(r) for r in rows]


def get_tag(conn: sqlite3.Connection, tag_id: int) -> dict | None:
    row = conn.execute(
        f"""
        {_recipe_count_sql()}
        WHERE t.id = ?
        GROUP BY t.id
        """,
        (tag_id,),
    ).fetchone()
    return dict(row) if row else None


def create_tag(conn: sqlite3.Connection, name: str) -> dict:
    slug = _unique_slug(conn, slugify(name))
    cur = conn.execute(
        "INSERT INTO tags (name, slug) VALUES (?, ?)",
        (name.strip(), slug),
    )
    conn.commit()
    return get_tag(conn, cur.lastrowid)  # type: ignore[arg-type]


def get_or_create_tag(conn: sqlite3.Connection, name: str) -> dict:
    cleaned = name.strip()
    if not cleaned:
        raise ValueError("Tag name is required")
    base_slug = slugify(cleaned)
    row = conn.execute(
        "SELECT id FROM tags WHERE lower(name) = lower(?) OR slug = ?",
        (cleaned, base_slug),
    ).fetchone()
    if row:
        tag = get_tag(conn, row["id"])
        if tag:
            return tag
    return create_tag(conn, cleaned)


def get_recipe_tags(conn: sqlite3.Connection, recipe_id: int) -> list[dict]:
    rows = conn.execute(
        """
        SELECT t.*, 0 AS recipe_count FROM tags t
        JOIN recipe_tags rt ON rt.tag_id = t.id
        WHERE rt.recipe_id = ?
        ORDER BY t.name
        """,
        (recipe_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def set_recipe_tags(
    conn: sqlite3.Connection, recipe_id: int, tag_ids: list[int]
) -> None:
    conn.execute("DELETE FROM recipe_tags WHERE recipe_id = ?", (recipe_id,))
    for tid in tag_ids:
        conn.execute(
            "INSERT OR IGNORE INTO recipe_tags (recipe_id, tag_id) VALUES (?, ?)",
            (recipe_id, tid),
        )
    conn.commit()


def assign_tags_by_ids(
    conn: sqlite3.Connection, tag_ids: list[int], recipe_ids: list[int]
) -> int:
    count = 0
    for rid in recipe_ids:
        for tid in tag_ids:
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO recipe_tags (recipe_id, tag_id) VALUES (?, ?)",
                    (rid, tid),
                )
                count += 1
            except sqlite3.Error:
                pass
    conn.commit()
    return count


def remove_tags_by_ids(
    conn: sqlite3.Connection, tag_ids: list[int], recipe_ids: list[int]
) -> int:
    if not tag_ids or not recipe_ids:
        return 0
    tag_placeholders = ",".join("?" * len(tag_ids))
    recipe_placeholders = ",".join("?" * len(recipe_ids))
    cur = conn.execute(
        f"""
        DELETE FROM recipe_tags
        WHERE tag_id IN ({tag_placeholders})
          AND recipe_id IN ({recipe_placeholders})
        """,
        [*tag_ids, *recipe_ids],
    )
    conn.commit()
    return cur.rowcount


def update_tag(conn: sqlite3.Connection, tag_id: int, name: str) -> dict | None:
    existing = conn.execute("SELECT * FROM tags WHERE id = ?", (tag_id,)).fetchone()
    if not existing:
        return None
    slug = existing["slug"]
    if name.strip() != existing["name"]:
        base_slug = slugify(name)
        slug = base_slug
        n = 1
        while conn.execute(
            "SELECT 1 FROM tags WHERE slug = ? AND id != ?", (slug, tag_id)
        ).fetchone():
            slug = f"{base_slug}-{n}"
            n += 1
    conn.execute(
        "UPDATE tags SET name = ?, slug = ? WHERE id = ?",
        (name.strip(), slug, tag_id),
    )
    conn.commit()
    return get_tag(conn, tag_id)


def delete_tag(conn: sqlite3.Connection, tag_id: int) -> bool:
    cur = conn.execute("DELETE FROM tags WHERE id = ?", (tag_id,))
    conn.commit()
    return cur.rowcount > 0


def merge_tags(
    conn: sqlite3.Connection, source_id: int, target_id: int
) -> dict | None:
    if source_id == target_id:
        return get_tag(conn, target_id)
    source = get_tag(conn, source_id)
    target = get_tag(conn, target_id)
    if not source or not target:
        return None
    conn.execute(
        """
        INSERT OR IGNORE INTO recipe_tags (recipe_id, tag_id)
        SELECT recipe_id, ? FROM recipe_tags WHERE tag_id = ?
        """,
        (target_id, source_id),
    )
    conn.execute("DELETE FROM recipe_tags WHERE tag_id = ?", (source_id,))
    conn.execute("DELETE FROM tags WHERE id = ?", (source_id,))
    conn.commit()
    return get_tag(conn, target_id)


def cooccurring_tags(
    conn: sqlite3.Connection, tag_ids: list[int]
) -> list[dict]:
    """Tags that co-occur on recipes matching all selected tag_ids (AND)."""
    if not tag_ids:
        return list_tags(conn)

    clauses: list[str] = []
    params: list[int] = []
    for tid in tag_ids:
        clauses.append(
            "r.id IN (SELECT recipe_id FROM recipe_tags WHERE tag_id = ?)"
        )
        params.append(tid)

    where = " AND ".join(clauses)
    exclude = ",".join("?" * len(tag_ids))
    rows = conn.execute(
        f"""
        SELECT t.*, COUNT(DISTINCT r.id) AS recipe_count
        FROM tags t
        JOIN recipe_tags rt ON rt.tag_id = t.id
        JOIN recipes r ON r.id = rt.recipe_id
        WHERE {where}
          AND t.id NOT IN ({exclude})
        GROUP BY t.id
        HAVING recipe_count > 0
        ORDER BY recipe_count DESC, t.name
        """,
        [*params, *tag_ids],
    ).fetchall()
    return [dict(r) for r in rows]
