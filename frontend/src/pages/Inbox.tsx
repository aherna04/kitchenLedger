import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api, Recipe } from "../api/client";

export default function Inbox() {
  const qc = useQueryClient();
  const [linkSource, setLinkSource] = useState<Recipe | null>(null);
  const [pickerQuery, setPickerQuery] = useState("");
  const [linkMessage, setLinkMessage] = useState<string | null>(null);

  const { data: status } = useQuery({
    queryKey: ["scan-status"],
    queryFn: api.scanStatus,
    refetchInterval: (q) => (q.state.data?.running ? 1000 : false),
  });

  const { data, refetch, isLoading } = useQuery({
    queryKey: ["recipes", "draft"],
    queryFn: () => api.listRecipes({ status: "draft", page_size: 100 }),
  });

  const { data: allRecipes } = useQuery({
    queryKey: ["recipes", "picker"],
    queryFn: () => api.listRecipes({ page_size: 200 }),
    enabled: !!linkSource,
  });

  const scan = useMutation({
    mutationFn: api.startScan,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["scan-status"] });
    },
  });

  const attach = useMutation({
    mutationFn: ({ targetId, sourceId }: { targetId: number; sourceId: number }) =>
      api.attachHeroFromRecipe(targetId, sourceId),
    onSuccess: (target) => {
      setLinkMessage(`Linked as hero for “${target.title || target.filename}”`);
      setLinkSource(null);
      setPickerQuery("");
      qc.invalidateQueries({ queryKey: ["recipes"] });
      refetch();
    },
    onError: (err: Error) => setLinkMessage(err.message),
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
  const pickerTargets = useMemo(() => {
    const items = allRecipes?.items ?? [];
    const q = pickerQuery.trim().toLowerCase();
    return items
      .filter((r) => r.id !== linkSource?.id)
      .filter((r) => {
        if (!q) return true;
        return (
          (r.title || "").toLowerCase().includes(q) ||
          r.filename.toLowerCase().includes(q)
        );
      });
  }, [allRecipes, linkSource, pickerQuery]);

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
        Review queue: correct OCR and mark reviewed, or link a dish photo as a hero for an
        existing recipe. Files leave inbox when you process them.
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
      {linkMessage && <p className="save-toast">{linkMessage}</p>}

      {isLoading ? (
        <div>Loading…</div>
      ) : drafts.length === 0 ? (
        <div className="empty-state">
          No drafts. Drop scans or dish photos into the inbox folder and click Scan.
        </div>
      ) : (
        <div className="recipe-grid">
          {drafts.map((r) => (
            <div key={r.id} className="recipe-card">
              <Link to={`/recipes/${r.id}`}>
                <img src={api.cardThumbUrl(r)} alt={r.title || r.filename} loading="lazy" />
              </Link>
              <div className="recipe-card-body">
                <Link to={`/recipes/${r.id}`}>
                  <h3>{r.title || r.filename}</h3>
                </Link>
                <div className="recipe-card-meta">
                  <span className="status-pill status-draft">draft</span>
                  <span>
                    {r.ingredients.length} ingredients · {r.steps.length} steps
                  </span>
                </div>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  style={{ marginTop: "0.5rem", width: "100%" }}
                  onClick={(e) => {
                    e.preventDefault();
                    setLinkMessage(null);
                    setLinkSource(r);
                    setPickerQuery("");
                  }}
                >
                  Link as hero to…
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {linkSource && (
        <div
          className="modal-backdrop"
          onClick={() => {
            setLinkSource(null);
            setPickerQuery("");
          }}
        >
          <div className="modal-panel" onClick={(e) => e.stopPropagation()}>
            <h3>Link as hero to…</h3>
            <p className="muted">
              Attach “{linkSource.title || linkSource.filename}” as the dish photo for a
              recipe. The file moves to the hero folder and this draft is removed.
            </p>
            <input
              className="modal-search"
              value={pickerQuery}
              onChange={(e) => setPickerQuery(e.target.value)}
              placeholder="Search recipes…"
              autoFocus
            />
            <div className="modal-list">
              {pickerTargets.length === 0 ? (
                <p className="muted">No recipes match.</p>
              ) : (
                pickerTargets.map((t) => (
                  <button
                    key={t.id}
                    type="button"
                    className="modal-list-item"
                    disabled={attach.isPending}
                    onClick={() =>
                      attach.mutate({ targetId: t.id, sourceId: linkSource.id })
                    }
                  >
                    <img src={api.cardThumbUrl(t)} alt="" />
                    <span>
                      <strong>{t.title || t.filename}</strong>
                      <span className="muted"> · {t.status}</span>
                    </span>
                  </button>
                ))
              )}
            </div>
            <div className="header-actions" style={{ marginTop: "0.75rem" }}>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => {
                  setLinkSource(null);
                  setPickerQuery("");
                }}
              >
                Cancel
              </button>
            </div>
            {attach.isError && (
              <p className="form-error">{(attach.error as Error).message}</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
