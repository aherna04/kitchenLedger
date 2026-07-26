import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../api/client";

export default function Home() {
  const qc = useQueryClient();
  const { data } = useQuery({
    queryKey: ["recipes", "recent"],
    queryFn: () => api.listRecipes({ page_size: 8 }),
  });
  const { data: drafts } = useQuery({
    queryKey: ["recipes", "drafts-count"],
    queryFn: () => api.listRecipes({ status: "draft", page_size: 1 }),
  });
  const scan = useMutation({
    mutationFn: api.startScan,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["scan-status"] });
      qc.invalidateQueries({ queryKey: ["recipes"] });
    },
  });

  const items = data?.items ?? [];
  const draftCount = drafts?.total ?? 0;

  return (
    <div className="home">
      <div className="home-hero">
        <div className="home-hero-inner">
          <p className="home-eyebrow">Local recipe catalog</p>
          <h1>Kitchen Ledger</h1>
          <p className="home-lead">
            Scan handwritten recipes, correct the OCR draft, and find them again with tags.
          </p>
          <div className="home-actions">
            <Link className="btn" to="/inbox">
              Open inbox{draftCount > 0 ? ` (${draftCount} drafts)` : ""}
            </Link>
            <Link className="btn btn-secondary" to="/recipes">
              Browse recipes
            </Link>
            <button
              className="btn btn-secondary"
              onClick={() => scan.mutate()}
              disabled={scan.isPending}
            >
              {scan.isPending ? "Starting…" : "Scan inbox"}
            </button>
          </div>
          {scan.isError && (
            <p className="form-error">{(scan.error as Error).message}</p>
          )}
        </div>
      </div>

      <section className="home-recent">
        <div className="page-header">
          <h2>Recent recipes</h2>
          <Link to="/recipes">View all</Link>
        </div>
        {items.length === 0 ? (
          <div className="empty-state">
            No recipes yet. Drop scans into the inbox folder and click Scan.
          </div>
        ) : (
          <div className="recipe-grid">
            {items.map((r) => (
              <Link key={r.id} to={`/recipes/${r.id}`} className="recipe-card">
                <img src={api.cardThumbUrl(r)} alt={r.title || r.filename} loading="lazy" />
                <div className="recipe-card-body">
                  <h3>{r.title || r.filename}</h3>
                  <div className="recipe-card-meta">
                    <span className={`status-pill status-${r.status}`}>{r.status}</span>
                    {r.tags.slice(0, 2).map((t) => (
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
      </section>
    </div>
  );
}
