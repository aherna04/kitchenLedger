from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

from app.db import get_config, get_conn
from app.metadata import (
    compute_sha256,
    extract_image_info,
    generate_thumbnail,
    iter_image_files,
)
from app.ocr import extract_ocr_text, split_recipe_lines


class ScanState:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.running = False
        self.processed = 0
        self.total = 0
        self.message: str | None = None
        self.phase: str = "idle"

    def snapshot(self) -> dict:
        with self.lock:
            return {
                "running": self.running,
                "processed": self.processed,
                "total": self.total,
                "message": self.message,
                "phase": self.phase,
            }

    def claim(self) -> bool:
        with self.lock:
            if self.running:
                return False
            self.running = True
            self.processed = 0
            self.total = 0
            self.phase = "scanning"
            self.message = "Starting inbox scan..."
            return True

    def start(self, total: int) -> None:
        with self.lock:
            self.running = True
            self.processed = 0
            self.total = total
            self.phase = "scanning"
            self.message = "Scanning inbox..."

    def tick(self) -> None:
        with self.lock:
            self.processed += 1

    def set_phase(self, phase: str, message: str | None = None) -> None:
        with self.lock:
            self.phase = phase
            if message is not None:
                self.message = message

    def finish(self, message: str) -> None:
        with self.lock:
            self.running = False
            self.phase = "idle"
            self.message = message


scan_state = ScanState()


def _replace_lines(conn, table: str, recipe_id: int, lines: list[str]) -> None:
    conn.execute(f"DELETE FROM {table} WHERE recipe_id = ?", (recipe_id,))
    for i, text in enumerate(lines):
        cleaned = text.strip()
        if not cleaned:
            continue
        conn.execute(
            f"INSERT INTO {table} (recipe_id, position, text) VALUES (?, ?, ?)",
            (recipe_id, i, cleaned),
        )


def _upsert_recipe(conn, path: Path) -> int | None:
    """Insert or refresh a recipe row. Returns recipe id when OCR should run."""
    existing = conn.execute(
        "SELECT id, mtime, ocr_text FROM recipes WHERE image_path = ?",
        (str(path),),
    ).fetchone()
    info = extract_image_info(path)
    if existing and existing["mtime"] == info["mtime"]:
        generate_thumbnail(path, existing["id"], info["mtime"])
        return None if existing["ocr_text"] else existing["id"]

    sha = compute_sha256(path)
    title_guess = path.stem.replace("_", " ").replace("-", " ").strip() or None

    if existing:
        recipe_id = existing["id"]
        conn.execute(
            """
            UPDATE recipes SET
                filename = ?, mtime = ?, width = ?, height = ?, sha256 = ?,
                updated_at = datetime('now')
            WHERE id = ?
            """,
            (
                path.name,
                info["mtime"],
                info["width"],
                info["height"],
                sha,
                recipe_id,
            ),
        )
        need_ocr = not existing["ocr_text"]
    else:
        cur = conn.execute(
            """
            INSERT INTO recipes (
                image_path, filename, title, status, width, height, sha256, mtime
            ) VALUES (?, ?, ?, 'draft', ?, ?, ?, ?)
            """,
            (
                str(path),
                path.name,
                title_guess,
                info["width"],
                info["height"],
                sha,
                info["mtime"],
            ),
        )
        recipe_id = cur.lastrowid
        need_ocr = True

    conn.commit()
    generate_thumbnail(path, recipe_id, info["mtime"])  # type: ignore[arg-type]
    return recipe_id if need_ocr else None


def _apply_ocr(conn, recipe_id: int, path: Path) -> None:
    ocr_text = extract_ocr_text(path)
    parsed = split_recipe_lines(ocr_text)
    row = conn.execute(
        "SELECT title FROM recipes WHERE id = ?", (recipe_id,)
    ).fetchone()
    title = parsed["title"] or (row["title"] if row else None)
    conn.execute(
        """
        UPDATE recipes SET
            title = ?, ocr_text = ?, updated_at = datetime('now')
        WHERE id = ?
        """,
        (title, ocr_text or None, recipe_id),
    )
    _replace_lines(conn, "recipe_ingredients", recipe_id, parsed["ingredients"])  # type: ignore[arg-type]
    _replace_lines(conn, "recipe_steps", recipe_id, parsed["steps"])  # type: ignore[arg-type]
    conn.commit()


def _prune_missing(conn, root: Path) -> int:
    rows = conn.execute(
        "SELECT id, image_path FROM recipes WHERE image_path LIKE ?",
        (f"{root}%",),
    ).fetchall()
    removed = 0
    for row in rows:
        if not Path(row["image_path"]).exists():
            conn.execute("DELETE FROM recipes WHERE id = ?", (row["id"],))
            removed += 1
    if removed:
        conn.commit()
    return removed


def _clear_stale_heroes(conn) -> int:
    """Clear hero refs when the hero file is gone from disk."""
    rows = conn.execute(
        """
        SELECT id, hero_path FROM recipes
        WHERE hero_path IS NOT NULL AND hero_path != ''
        """
    ).fetchall()
    cleared = 0
    for row in rows:
        if not Path(row["hero_path"]).exists():
            conn.execute(
                """
                UPDATE recipes SET
                    hero_filename = NULL, hero_path = NULL, hero_mtime = NULL,
                    updated_at = datetime('now')
                WHERE id = ?
                """,
                (row["id"],),
            )
            cleared += 1
    if cleared:
        conn.commit()
    return cleared


def _match_heroes(conn, hero_root: Path) -> int:
    """Match hero/ images to recipes by filename stem; return count matched."""
    hero_files = iter_image_files(hero_root)
    if not hero_files:
        return 0

    by_stem: dict[str, list[sqlite3.Row]] = {}
    rows = conn.execute(
        "SELECT id, filename, hero_path, hero_mtime FROM recipes"
    ).fetchall()
    for row in rows:
        stem = Path(row["filename"]).stem.lower()
        by_stem.setdefault(stem, []).append(row)

    matched = 0
    for path in hero_files:
        stem = path.stem.lower()
        candidates = by_stem.get(stem) or []
        if not candidates:
            continue
        # Prefer an unmatched recipe; otherwise update the first match
        recipe = candidates[0]
        for cand in candidates:
            if not cand["hero_path"]:
                recipe = cand
                break

        mtime = path.stat().st_mtime
        existing_path = recipe["hero_path"]
        existing_mtime = recipe["hero_mtime"]
        if existing_path == str(path) and existing_mtime == mtime:
            generate_thumbnail(path, recipe["id"], mtime, variant="hero")
            matched += 1
            continue

        conn.execute(
            """
            UPDATE recipes SET
                hero_filename = ?, hero_path = ?, hero_mtime = ?,
                updated_at = datetime('now')
            WHERE id = ?
            """,
            (path.name, str(path), mtime, recipe["id"]),
        )
        generate_thumbnail(path, recipe["id"], mtime, variant="hero")
        matched += 1

    if matched:
        conn.commit()
    return matched


def _run_scan() -> None:
    try:
        with get_conn() as conn:
            cfg = get_config(conn)
            root = Path(cfg["inbox_path"])
            hero_root = Path(cfg.get("hero_path") or "")
        files = iter_image_files(root)
        scan_state.start(len(files))
        ocr_ids: list[tuple[int, Path]] = []
        removed = 0
        hero_matched = 0

        with get_conn() as conn:
            for path in files:
                try:
                    recipe_id = _upsert_recipe(conn, path)
                    if recipe_id is not None:
                        ocr_ids.append((recipe_id, path))
                except Exception as exc:
                    scan_state.set_phase(
                        "scanning", f"Error on {path.name}: {exc}"
                    )
                scan_state.tick()

            scan_state.set_phase("pruning", "Pruning missing files...")
            removed = _prune_missing(conn, root)

        if ocr_ids:
            scan_state.set_phase("ocr", "Running OCR on new recipes...")
            with get_conn() as conn:
                for recipe_id, path in ocr_ids:
                    try:
                        _apply_ocr(conn, recipe_id, path)
                    except Exception as exc:
                        scan_state.set_phase(
                            "ocr", f"OCR error on {path.name}: {exc}"
                        )

        scan_state.set_phase("hero", "Matching hero images...")
        with get_conn() as conn:
            _clear_stale_heroes(conn)
            if hero_root:
                try:
                    hero_matched = _match_heroes(conn, hero_root)
                except Exception as exc:
                    scan_state.set_phase("hero", f"Hero match error: {exc}")

        parts = [f"Scan complete: {len(files)} files, {len(ocr_ids)} OCR'd"]
        if removed:
            parts.append(f"{removed} pruned")
        if hero_matched:
            parts.append(f"{hero_matched} heroes")
        scan_state.finish(", ".join(parts))
    except Exception as exc:
        scan_state.finish(f"Scan failed: {exc}")


def start_scan() -> bool:
    if not scan_state.claim():
        return False
    thread = threading.Thread(target=_run_scan, daemon=True)
    thread.start()
    return True
