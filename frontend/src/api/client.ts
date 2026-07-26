export interface Tag {
  id: number;
  name: string;
  slug: string;
  recipe_count: number;
}

export interface Ingredient {
  id: number;
  position: number;
  text: string;
}

export interface Step {
  id: number;
  position: number;
  text: string;
}

export interface Recipe {
  id: number;
  image_path: string;
  filename: string;
  title: string | null;
  servings: string | null;
  source: string | null;
  notes: string | null;
  ocr_text: string | null;
  status: "draft" | "reviewed";
  width: number | null;
  height: number | null;
  sha256: string | null;
  mtime: number;
  hero_filename: string | null;
  hero_mtime: number | null;
  created_at: string | null;
  updated_at: string | null;
  ingredients: Ingredient[];
  steps: Step[];
  tags: Tag[];
}

export interface RecipeList {
  items: Recipe[];
  total: number;
  page: number;
  page_size: number;
}

export interface Config {
  inbox_path: string;
  recipes_path: string;
  hero_path: string;
  kl_root?: string | null;
  kl_data_dir?: string | null;
}

export interface ScanStatus {
  running: boolean;
  processed: number;
  total: number;
  message: string | null;
  phase: string;
}

export interface DatabaseBackup {
  path: string;
  filename: string;
  size_bytes: number;
  created_at: string;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || JSON.stringify(body);
    } catch {
      /* ignore */
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

function qs(params: Record<string, string | number | boolean | undefined | null | (string | number)[]>): string {
  const q = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    if (Array.isArray(value)) {
      for (const v of value) q.append(key, String(v));
    } else {
      q.set(key, String(value));
    }
  }
  const s = q.toString();
  return s ? `?${s}` : "";
}

function cacheBust(v?: number | null): string {
  return v ? `?v=${Math.floor(v)}` : "";
}

export const api = {
  health: () => request<{ ok: boolean; version: string }>("/api/health"),

  getConfig: () => request<Config>("/api/config"),
  updateConfig: (body: Partial<Config>) =>
    request<Config>("/api/config", { method: "PATCH", body: JSON.stringify(body) }),

  startScan: () => request<ScanStatus>("/api/scan", { method: "POST" }),
  scanStatus: () => request<ScanStatus>("/api/scan/status"),

  listRecipes: (opts?: {
    tag_id?: number[];
    status?: string;
    q?: string;
    page?: number;
    page_size?: number;
  }) =>
    request<RecipeList>(
      `/api/recipes${qs({
        tag_id: opts?.tag_id,
        status: opts?.status,
        q: opts?.q,
        page: opts?.page,
        page_size: opts?.page_size,
      })}`
    ),

  getRecipe: (id: number) => request<Recipe>(`/api/recipes/${id}`),

  updateRecipe: (
    id: number,
    body: {
      title?: string | null;
      servings?: string | null;
      source?: string | null;
      notes?: string | null;
      status?: "draft" | "reviewed";
      tag_ids?: number[];
    }
  ) =>
    request<Recipe>(`/api/recipes/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),

  replaceIngredients: (id: number, lines: string[]) =>
    request<Ingredient[]>(`/api/recipes/${id}/ingredients`, {
      method: "PUT",
      body: JSON.stringify({ lines }),
    }),

  replaceSteps: (id: number, lines: string[]) =>
    request<Step[]>(`/api/recipes/${id}/steps`, {
      method: "PUT",
      body: JSON.stringify({ lines }),
    }),

  attachHeroFromRecipe: (targetId: number, sourceRecipeId: number) =>
    request<Recipe>(`/api/recipes/${targetId}/hero-from-recipe`, {
      method: "POST",
      body: JSON.stringify({ source_recipe_id: sourceRecipeId }),
    }),

  // `v` is an mtime-based cache-buster so replaced files display immediately
  // instead of serving a stale browser-cached image at a stable URL.
  thumbUrl: (id: number, v?: number | null) => `/api/recipes/${id}/thumbnail${cacheBust(v)}`,
  imageUrl: (id: number, v?: number | null) => `/api/recipes/${id}/image${cacheBust(v)}`,
  heroUrl: (id: number, v?: number | null) => `/api/recipes/${id}/hero${cacheBust(v)}`,
  heroThumbUrl: (id: number, v?: number | null) => `/api/recipes/${id}/hero-thumbnail${cacheBust(v)}`,
  /** Card thumbnail: prefer hero dish photo when present. */
  cardThumbUrl: (recipe: {
    id: number;
    hero_filename?: string | null;
    hero_mtime?: number | null;
    mtime?: number | null;
  }) =>
    recipe.hero_filename
      ? `/api/recipes/${recipe.id}/hero-thumbnail${cacheBust(recipe.hero_mtime)}`
      : `/api/recipes/${recipe.id}/thumbnail${cacheBust(recipe.mtime)}`,

  listTags: () => request<Tag[]>("/api/tags"),
  createTag: (name: string) =>
    request<Tag>("/api/tags", { method: "POST", body: JSON.stringify({ name }) }),
  updateTag: (id: number, name: string) =>
    request<Tag>(`/api/tags/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ name }),
    }),
  deleteTag: (id: number) =>
    request<{ ok: boolean }>(`/api/tags/${id}`, { method: "DELETE" }),
  mergeTags: (source_id: number, target_id: number) =>
    request<Tag>("/api/tags/merge", {
      method: "POST",
      body: JSON.stringify({ source_id, target_id }),
    }),
  assignTags: (tag_ids: number[], recipe_ids: number[]) =>
    request<{ assigned: number }>("/api/tags/assign-ids", {
      method: "POST",
      body: JSON.stringify({ tag_ids, recipe_ids }),
    }),
  unassignTags: (tag_ids: number[], recipe_ids: number[]) =>
    request<{ removed: number }>("/api/tags/unassign-ids", {
      method: "POST",
      body: JSON.stringify({ tag_ids, recipe_ids }),
    }),
  cooccurringTags: (tag_ids: number[]) =>
    request<{ tags: Tag[] }>(`/api/tags/cooccurring${qs({ tag_id: tag_ids })}`),

  createDatabaseBackup: () =>
    request<DatabaseBackup>("/api/database/backup", { method: "POST" }),
  listDatabaseBackups: () =>
    request<{ items: DatabaseBackup[] }>("/api/database/backups"),
};
