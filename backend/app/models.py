from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ConfigOut(BaseModel):
    inbox_path: str
    recipes_path: str
    hero_path: str
    kl_root: str | None = None
    kl_data_dir: str | None = None


class ConfigUpdate(BaseModel):
    inbox_path: str | None = None
    recipes_path: str | None = None
    hero_path: str | None = None


class TagOut(BaseModel):
    id: int
    name: str
    slug: str
    recipe_count: int = 0


class TagCreate(BaseModel):
    name: str = Field(..., min_length=1)


class TagUpdate(BaseModel):
    name: str = Field(..., min_length=1)


class TagMerge(BaseModel):
    source_id: int
    target_id: int


class TagAssign(BaseModel):
    tag_ids: list[int]
    recipe_ids: list[int]


class IngredientOut(BaseModel):
    id: int
    position: int
    text: str


class StepOut(BaseModel):
    id: int
    position: int
    text: str


class RecipeOut(BaseModel):
    id: int
    image_path: str
    filename: str
    title: str | None = None
    servings: str | None = None
    source: str | None = None
    notes: str | None = None
    ocr_text: str | None = None
    status: Literal["draft", "reviewed"]
    width: int | None = None
    height: int | None = None
    sha256: str | None = None
    mtime: float
    hero_filename: str | None = None
    hero_mtime: float | None = None
    created_at: str | None = None
    updated_at: str | None = None
    ingredients: list[IngredientOut] = []
    steps: list[StepOut] = []
    tags: list[TagOut] = []


class RecipeListOut(BaseModel):
    items: list[RecipeOut]
    total: int
    page: int
    page_size: int


class RecipeUpdate(BaseModel):
    title: str | None = None
    servings: str | None = None
    source: str | None = None
    notes: str | None = None
    status: Literal["draft", "reviewed"] | None = None
    tag_ids: list[int] | None = None


class LinesReplace(BaseModel):
    lines: list[str]


class HeroFromRecipeIn(BaseModel):
    source_recipe_id: int


class ScanStatusOut(BaseModel):
    running: bool
    processed: int = 0
    total: int = 0
    message: str | None = None
    phase: str = "idle"


class DatabaseBackupOut(BaseModel):
    path: str
    filename: str
    size_bytes: int
    created_at: str


class DatabaseBackupListOut(BaseModel):
    items: list[DatabaseBackupOut]


class CooccurringOut(BaseModel):
    tags: list[TagOut]
