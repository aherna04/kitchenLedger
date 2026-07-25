import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../api/client";

export default function TagsPage() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [search, setSearch] = useState("");

  const { data: tags = [] } = useQuery({
    queryKey: ["tags"],
    queryFn: api.listTags,
  });

  const create = useMutation({
    mutationFn: () => api.createTag(name.trim()),
    onSuccess: () => {
      setShowForm(false);
      setName("");
      qc.invalidateQueries({ queryKey: ["tags"] });
    },
  });

  const remove = useMutation({
    mutationFn: (id: number) => api.deleteTag(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tags"] }),
  });

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return tags;
    return tags.filter((t) => t.name.toLowerCase().includes(q));
  }, [tags, search]);

  return (
    <div>
      <div className="page-header">
        <h2>Tags</h2>
        <button className="btn" onClick={() => setShowForm(true)}>
          New tag
        </button>
      </div>
      <p className="page-intro">
        Labels like dessert, weeknight, or grandma. Assign them on recipe detail pages.
      </p>

      {showForm && (
        <div className="form-card">
          <div className="form-group">
            <label>Name</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Dessert"
            />
          </div>
          <div className="header-actions">
            <button
              className="btn"
              onClick={() => create.mutate()}
              disabled={!name.trim() || create.isPending}
            >
              Create
            </button>
            <button
              className="btn btn-secondary"
              onClick={() => {
                setShowForm(false);
                setName("");
              }}
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {tags.length > 0 && (
        <div className="search-bar" style={{ marginBottom: "1rem", maxWidth: "24rem" }}>
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search tags…"
          />
        </div>
      )}

      {tags.length === 0 ? (
        <div className="empty-state">No tags yet.</div>
      ) : filtered.length === 0 ? (
        <p className="muted">No tags match.</p>
      ) : (
        <div className="label-cards">
          {filtered.map((tag) => (
            <div key={tag.id} className="label-card">
              <Link to={`/recipes?tag=${encodeURIComponent(tag.slug)}`}>
                <h3 className="label-card-title">{tag.name}</h3>
                <div className="label-card-meta">
                  {tag.recipe_count} recipe{tag.recipe_count === 1 ? "" : "s"}
                </div>
              </Link>
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => {
                  if (confirm(`Delete tag “${tag.name}”?`)) remove.mutate(tag.id);
                }}
              >
                Delete
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
