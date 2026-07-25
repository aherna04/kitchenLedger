import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../api/client";

export default function Inbox() {
  const qc = useQueryClient();

  const { data: status } = useQuery({
    queryKey: ["scan-status"],
    queryFn: api.scanStatus,
    refetchInterval: (q) => (q.state.data?.running ? 1000 : false),
  });

  const { data, refetch, isLoading } = useQuery({
    queryKey: ["recipes", "draft"],
    queryFn: () => api.listRecipes({ status: "draft", page_size: 100 }),
  });

  const scan = useMutation({
    mutationFn: api.startScan,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["scan-status"] });
    },
  });

  // Refresh drafts when scan finishes
  useQuery({
    queryKey: ["scan-status-watch", status?.running],
    queryFn: async () => {
      if (!status?.running) {
        await refetch();
        qc.invalidateQueries({ queryKey: ["recipes"] });
      }
      return true;
    },
    enabled: status != null,
  });

  const drafts = data?.items ?? [];

  return (
    <div>
      <div className="page-header">
        <h2>Inbox</h2>
        <button
          className="btn"
          onClick={() => scan.mutate()}
          disabled={scan.isPending || !!status?.running}
        >
          {status?.running ? "Scanning…" : "Scan"}
        </button>
      </div>
      <p className="page-intro">
        Draft recipes from scanned images. Open one to correct OCR and mark reviewed.
      </p>

      {(status?.running || status?.message) && (
        <div className="scan-banner">
          {status.running ? (
            <>
              <strong>{status.phase}</strong> — {status.message || "Working…"}{" "}
              {status.total > 0 && (
                <span>
                  ({status.processed}/{status.total})
                </span>
              )}
            </>
          ) : (
            <span>{status.message}</span>
          )}
        </div>
      )}

      {scan.isError && <p className="form-error">{(scan.error as Error).message}</p>}

      {isLoading ? (
        <div>Loading…</div>
      ) : drafts.length === 0 ? (
        <div className="empty-state">
          No draft recipes. Drop images into the inbox folder and click Scan.
        </div>
      ) : (
        <div className="recipe-grid">
          {drafts.map((r) => (
            <Link key={r.id} to={`/recipes/${r.id}`} className="recipe-card">
              <img src={api.thumbUrl(r.id)} alt={r.title || r.filename} loading="lazy" />
              <div className="recipe-card-body">
                <h3>{r.title || r.filename}</h3>
                <div className="recipe-card-meta">
                  <span className="status-pill status-draft">draft</span>
                  <span>
                    {r.ingredients.length} ingredients · {r.steps.length} steps
                  </span>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
