import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { api, Tag } from "../api/client";

export default function RecipeDetail() {
  const { id } = useParams();
  const recipeId = Number(id);
  const qc = useQueryClient();

  const { data: recipe, isLoading } = useQuery({
    queryKey: ["recipe", recipeId],
    queryFn: () => api.getRecipe(recipeId),
    enabled: Number.isFinite(recipeId),
  });

  const { data: allTags = [] } = useQuery({
    queryKey: ["tags"],
    queryFn: api.listTags,
  });

  const [title, setTitle] = useState("");
  const [servings, setServings] = useState("");
  const [source, setSource] = useState("");
  const [notes, setNotes] = useState("");
  const [ingredientsText, setIngredientsText] = useState("");
  const [stepsText, setStepsText] = useState("");
  const [selectedTagIds, setSelectedTagIds] = useState<number[]>([]);
  const [newTagName, setNewTagName] = useState("");
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!recipe) return;
    setTitle(recipe.title || "");
    setServings(recipe.servings || "");
    setSource(recipe.source || "");
    setNotes(recipe.notes || "");
    setIngredientsText(recipe.ingredients.map((i) => i.text).join("\n"));
    setStepsText(recipe.steps.map((s) => s.text).join("\n"));
    setSelectedTagIds(recipe.tags.map((t) => t.id));
  }, [recipe]);

  const save = useMutation({
    mutationFn: async (markReviewed: boolean) => {
      await api.replaceIngredients(
        recipeId,
        ingredientsText.split("\n").map((l) => l.trim()).filter(Boolean)
      );
      await api.replaceSteps(
        recipeId,
        stepsText.split("\n").map((l) => l.trim()).filter(Boolean)
      );
      return api.updateRecipe(recipeId, {
        title,
        servings,
        source,
        notes,
        tag_ids: selectedTagIds,
        status: markReviewed ? "reviewed" : recipe?.status,
      });
    },
    onSuccess: () => {
      setMessage("Saved");
      qc.invalidateQueries({ queryKey: ["recipe", recipeId] });
      qc.invalidateQueries({ queryKey: ["recipes"] });
      qc.invalidateQueries({ queryKey: ["tags"] });
    },
    onError: (err: Error) => setMessage(err.message),
  });

  const createTag = useMutation({
    mutationFn: () => api.createTag(newTagName.trim()),
    onSuccess: (tag: Tag) => {
      setSelectedTagIds((ids) => (ids.includes(tag.id) ? ids : [...ids, tag.id]));
      setNewTagName("");
      qc.invalidateQueries({ queryKey: ["tags"] });
    },
  });

  const selectedSet = useMemo(() => new Set(selectedTagIds), [selectedTagIds]);

  function toggleTag(tagId: number) {
    setSelectedTagIds((ids) =>
      ids.includes(tagId) ? ids.filter((x) => x !== tagId) : [...ids, tagId]
    );
  }

  if (!Number.isFinite(recipeId)) {
    return <div className="empty-state">Invalid recipe id</div>;
  }
  if (isLoading || !recipe) {
    return <div>Loading…</div>;
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <Link to={recipe.status === "draft" ? "/inbox" : "/recipes"} className="muted">
            ← Back
          </Link>
          <h2 style={{ marginTop: "0.35rem" }}>{recipe.title || recipe.filename}</h2>
        </div>
        <div className="header-actions">
          <button
            className="btn btn-secondary"
            onClick={() => save.mutate(false)}
            disabled={save.isPending}
          >
            Save
          </button>
          {recipe.status === "draft" && (
            <button
              className="btn"
              onClick={() => save.mutate(true)}
              disabled={save.isPending}
            >
              Mark reviewed
            </button>
          )}
        </div>
      </div>

      {message && <p className="save-toast">{message}</p>}

      <div className="recipe-detail">
        <div className="recipe-detail-image">
          <img src={api.imageUrl(recipe.id)} alt={recipe.title || recipe.filename} />
          <p className="muted filename">{recipe.filename}</p>
          {recipe.ocr_text && (
            <details className="ocr-raw">
              <summary>Raw OCR text</summary>
              <pre>{recipe.ocr_text}</pre>
            </details>
          )}
        </div>

        <div className="recipe-detail-form">
          <div className="form-group">
            <label>Title</label>
            <input value={title} onChange={(e) => setTitle(e.target.value)} />
          </div>
          <div className="form-row">
            <div className="form-group">
              <label>Servings</label>
              <input value={servings} onChange={(e) => setServings(e.target.value)} />
            </div>
            <div className="form-group">
              <label>Source</label>
              <input value={source} onChange={(e) => setSource(e.target.value)} />
            </div>
          </div>
          <div className="form-group">
            <label>Ingredients (one per line)</label>
            <textarea
              rows={12}
              value={ingredientsText}
              onChange={(e) => setIngredientsText(e.target.value)}
            />
          </div>
          <div className="form-group">
            <label>Directions (one per line)</label>
            <textarea
              rows={12}
              value={stepsText}
              onChange={(e) => setStepsText(e.target.value)}
            />
          </div>
          <div className="form-group">
            <label>Notes</label>
            <textarea rows={4} value={notes} onChange={(e) => setNotes(e.target.value)} />
          </div>
          <div className="form-group">
            <label>Tags</label>
            <div className="tag-list">
              {allTags.map((t) => (
                <button
                  key={t.id}
                  type="button"
                  className={`tag-chip ${selectedSet.has(t.id) ? "tag-chip-active" : ""}`}
                  onClick={() => toggleTag(t.id)}
                >
                  {t.name}
                </button>
              ))}
            </div>
            <div className="inline-create">
              <input
                value={newTagName}
                onChange={(e) => setNewTagName(e.target.value)}
                placeholder="New tag"
              />
              <button
                className="btn btn-secondary"
                type="button"
                disabled={!newTagName.trim() || createTag.isPending}
                onClick={() => createTag.mutate()}
              >
                Add
              </button>
            </div>
          </div>
          <div className="form-group">
            <label>Status</label>
            <span className={`status-pill status-${recipe.status}`}>{recipe.status}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
