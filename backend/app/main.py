from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.config import (
    KL_DATA_DIR,
    KL_ROOT,
    ensure_app_dirs,
    ensure_media_dirs,
    mime_type_for_path,
)
from app.db import get_config, get_conn, init_db, update_config
from app.db_backup import create_backup, list_backups
from app.metadata import generate_thumbnail, thumb_cache_path
from app.models import (
    CooccurringOut,
    ConfigOut,
    ConfigUpdate,
    DatabaseBackupListOut,
    DatabaseBackupOut,
    IngredientOut,
    LinesReplace,
    RecipeListOut,
    RecipeOut,
    RecipeUpdate,
    ScanStatusOut,
    StepOut,
    TagAssign,
    TagCreate,
    TagMerge,
    TagOut,
    TagUpdate,
)
from app.recipes import (
    get_recipe,
    list_recipes,
    replace_ingredients,
    replace_steps,
    update_recipe,
)
from app.scanner import scan_state, start_scan
from app import tags as tags_mod

app = FastAPI(title="Kitchen Ledger", version="2026.07.25")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    ensure_media_dirs()
    ensure_app_dirs()
    init_db()


def _recipe_out(data: dict) -> RecipeOut:
    return RecipeOut(**data)


def _tag_out(data: dict) -> TagOut:
    return TagOut(
        id=data["id"],
        name=data["name"],
        slug=data["slug"],
        recipe_count=int(data.get("recipe_count") or 0),
    )


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "version": app.version}


@app.get("/api/config", response_model=ConfigOut)
def read_config() -> ConfigOut:
    with get_conn() as conn:
        cfg = get_config(conn)
    return ConfigOut(
        inbox_path=cfg["inbox_path"],
        recipes_path=cfg["recipes_path"],
        kl_root=str(KL_ROOT),
        kl_data_dir=str(KL_DATA_DIR),
    )


@app.patch("/api/config", response_model=ConfigOut)
def patch_config(body: ConfigUpdate) -> ConfigOut:
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    with get_conn() as conn:
        cfg = update_config(conn, updates) if updates else get_config(conn)
    return ConfigOut(
        inbox_path=cfg["inbox_path"],
        recipes_path=cfg["recipes_path"],
        kl_root=str(KL_ROOT),
        kl_data_dir=str(KL_DATA_DIR),
    )


@app.post("/api/scan", response_model=ScanStatusOut)
def post_scan() -> ScanStatusOut:
    if not start_scan():
        raise HTTPException(status_code=409, detail="Scan already running")
    return ScanStatusOut(**scan_state.snapshot())


@app.get("/api/scan/status", response_model=ScanStatusOut)
def get_scan_status() -> ScanStatusOut:
    return ScanStatusOut(**scan_state.snapshot())


@app.get("/api/recipes", response_model=RecipeListOut)
def get_recipes(
    tag_id: list[int] | None = Query(default=None),
    status: str | None = None,
    q: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=48, ge=1, le=200),
) -> RecipeListOut:
    with get_conn() as conn:
        items, total = list_recipes(
            conn,
            tag_ids=tag_id or [],
            status=status,
            q=q,
            page=page,
            page_size=page_size,
        )
    return RecipeListOut(
        items=[_recipe_out(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@app.get("/api/recipes/{recipe_id}", response_model=RecipeOut)
def get_recipe_by_id(recipe_id: int) -> RecipeOut:
    with get_conn() as conn:
        recipe = get_recipe(conn, recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return _recipe_out(recipe)


@app.patch("/api/recipes/{recipe_id}", response_model=RecipeOut)
def patch_recipe(recipe_id: int, body: RecipeUpdate) -> RecipeOut:
    with get_conn() as conn:
        recipe = update_recipe(
            conn,
            recipe_id,
            title=body.title,
            servings=body.servings,
            source=body.source,
            notes=body.notes,
            status=body.status,
            tag_ids=body.tag_ids,
        )
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return _recipe_out(recipe)


@app.put("/api/recipes/{recipe_id}/ingredients", response_model=list[IngredientOut])
def put_ingredients(recipe_id: int, body: LinesReplace) -> list[IngredientOut]:
    with get_conn() as conn:
        if not get_recipe(conn, recipe_id):
            raise HTTPException(status_code=404, detail="Recipe not found")
        items = replace_ingredients(conn, recipe_id, body.lines)
    return [IngredientOut(**i) for i in items]


@app.put("/api/recipes/{recipe_id}/steps", response_model=list[StepOut])
def put_steps(recipe_id: int, body: LinesReplace) -> list[StepOut]:
    with get_conn() as conn:
        if not get_recipe(conn, recipe_id):
            raise HTTPException(status_code=404, detail="Recipe not found")
        items = replace_steps(conn, recipe_id, body.lines)
    return [StepOut(**i) for i in items]


@app.get("/api/recipes/{recipe_id}/thumbnail")
def get_thumbnail(recipe_id: int):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT image_path, mtime FROM recipes WHERE id = ?", (recipe_id,)
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Recipe not found")
    path = Path(row["image_path"])
    if not path.exists():
        raise HTTPException(status_code=404, detail="Image missing on disk")
    thumb = thumb_cache_path(recipe_id, row["mtime"])
    if not thumb.exists():
        thumb = generate_thumbnail(path, recipe_id, row["mtime"])
    return FileResponse(thumb, media_type="image/jpeg")


@app.get("/api/recipes/{recipe_id}/image")
def get_image(recipe_id: int):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT image_path FROM recipes WHERE id = ?", (recipe_id,)
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Recipe not found")
    path = Path(row["image_path"])
    if not path.exists():
        raise HTTPException(status_code=404, detail="Image missing on disk")
    return FileResponse(path, media_type=mime_type_for_path(path))


@app.get("/api/tags", response_model=list[TagOut])
def get_tags() -> list[TagOut]:
    with get_conn() as conn:
        return [_tag_out(t) for t in tags_mod.list_tags(conn)]


@app.post("/api/tags", response_model=TagOut)
def post_tag(body: TagCreate) -> TagOut:
    with get_conn() as conn:
        try:
            tag = tags_mod.create_tag(conn, body.name)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _tag_out(tag)


@app.patch("/api/tags/{tag_id}", response_model=TagOut)
def patch_tag(tag_id: int, body: TagUpdate) -> TagOut:
    with get_conn() as conn:
        tag = tags_mod.update_tag(conn, tag_id, body.name)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    return _tag_out(tag)


@app.delete("/api/tags/{tag_id}")
def delete_tag(tag_id: int) -> dict:
    with get_conn() as conn:
        ok = tags_mod.delete_tag(conn, tag_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Tag not found")
    return {"ok": True}


@app.post("/api/tags/merge", response_model=TagOut)
def post_merge_tags(body: TagMerge) -> TagOut:
    with get_conn() as conn:
        tag = tags_mod.merge_tags(conn, body.source_id, body.target_id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    return _tag_out(tag)


@app.post("/api/tags/assign-ids")
def post_assign_tags(body: TagAssign) -> dict:
    with get_conn() as conn:
        count = tags_mod.assign_tags_by_ids(conn, body.tag_ids, body.recipe_ids)
    return {"assigned": count}


@app.post("/api/tags/unassign-ids")
def post_unassign_tags(body: TagAssign) -> dict:
    with get_conn() as conn:
        count = tags_mod.remove_tags_by_ids(conn, body.tag_ids, body.recipe_ids)
    return {"removed": count}


@app.get("/api/tags/cooccurring", response_model=CooccurringOut)
def get_cooccurring(
    tag_id: list[int] | None = Query(default=None),
) -> CooccurringOut:
    with get_conn() as conn:
        tags = tags_mod.cooccurring_tags(conn, tag_id or [])
    return CooccurringOut(tags=[_tag_out(t) for t in tags])


@app.post("/api/database/backup", response_model=DatabaseBackupOut)
def post_backup() -> DatabaseBackupOut:
    try:
        result = create_backup()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return DatabaseBackupOut(**result)


@app.get("/api/database/backups", response_model=DatabaseBackupListOut)
def get_backups() -> DatabaseBackupListOut:
    return DatabaseBackupListOut(
        items=[DatabaseBackupOut(**b) for b in list_backups()]
    )
