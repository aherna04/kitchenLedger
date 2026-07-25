import { useMemo, useState, type FormEvent } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api/client";

export default function Recipes() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [q, setQ] = useState(searchParams.get("q") || "");
  const selectedSlugs = searchParams.getAll("tag");

  const { data: allTags = [] } = useQuery({
    queryKey: ["tags"],
    queryFn: api.listTags,
  });

  const selectedTags = useMemo(
    () => allTags.filter((t) => selectedSlugs.includes(t.slug)),
    [allTags, selectedSlugs]
  );
  const selectedIds = selectedTags.map((t) => t.id);

  const { data: cooccur } = useQuery({
    queryKey: ["cooccurring", selectedIds],
    queryFn: () => api.cooccurringTags(selectedIds),
    enabled: selectedIds.length > 0,
  });

  const { data, isLoading } = useQuery({
    queryKey: ["recipes", "browse", selectedIds, q],
    queryFn: () =>
      api.listRecipes({
        tag_id: selectedIds.length ? selectedIds : undefined,
        q: q || undefined,
        page_size: 100,
      }),
  });

  function setTags(slugs: string[]) {
    const next = new URLSearchParams();
    if (q) next.set("q", q);
    for (const slug of slugs) next.append("tag", slug);
    setSearchParams(next);
  }

  function toggleTag(slug: string) {
    if (selectedSlugs.includes(slug)) {
      setTags(selectedSlugs.filter((s) => s !== slug));
    } else {
      setTags([...selectedSlugs, slug]);
    }
  }

  function applySearch(e: FormEvent) {
    e.preventDefault();
    const next = new URLSearchParams();
    if (q.trim()) next.set("q", q.trim());
    for (const slug of selectedSlugs) next.append("tag", slug);
    setSearchParams(next);
  }

  const sidebarTags =
    selectedIds.length > 0 ? cooccur?.tags ?? [] : allTags.slice(0, 40);
  const items = data?.items ?? [];

  return (
    <div className="browse-layout">
      <aside className="browse-sidebar">
        <h3>Tags</h3>
        {selectedTags.length > 0 && (
          <div className="selected-tags">
            {selectedTags.map((t) => (
              <button
                key={t.id}
                className="tag-chip tag-chip-active"
                onClick={() => toggleTag(t.slug)}
              >
                {t.name} ×
              </button>
            ))}
            <button className="btn btn-secondary btn-sm" onClick={() => setTags([])}>
              Clear
            </button>
          </div>
        )}
        <div className="tag-list">
          {sidebarTags.map((t) => (
            <button
              key={t.id}
              className={`tag-chip ${selectedSlugs.includes(t.slug) ? "tag-chip-active" : ""}`}
              onClick={() => toggleTag(t.slug)}
            >
              {t.name}
              <span className="tag-count">{t.recipe_count}</span>
            </button>
          ))}
          {sidebarTags.length === 0 && (
            <p className="muted">No tags yet. Create some on the Tags page.</p>
          )}
        </div>
      </aside>

      <div className="browse-main">
        <div className="page-header">
          <h2>Recipes</h2>
          <span className="muted">{data?.total ?? 0} recipes</span>
        </div>

        <form className="search-bar" onSubmit={applySearch}>
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search title, ingredients, notes…"
          />
          <button className="btn" type="submit">
            Search
          </button>
        </form>

        {isLoading ? (
          <div>Loading…</div>
        ) : items.length === 0 ? (
          <div className="empty-state">No recipes match these filters.</div>
        ) : (
          <div className="recipe-grid">
            {items.map((r) => (
              <Link key={r.id} to={`/recipes/${r.id}`} className="recipe-card">
                <img src={api.thumbUrl(r.id)} alt={r.title || r.filename} loading="lazy" />
                <div className="recipe-card-body">
                  <h3>{r.title || r.filename}</h3>
                  <div className="recipe-card-meta">
                    <span className={`status-pill status-${r.status}`}>{r.status}</span>
                    {r.tags.slice(0, 3).map((t) => (
                      <span key={t.id} className="tag-chip">
                        {t.name}
                      </span>
                    ))}
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
