import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../api/client";

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

export default function Settings() {
  const qc = useQueryClient();
  const [backupMessage, setBackupMessage] = useState<string | null>(null);
  const [form, setForm] = useState<Record<string, string>>({});

  const { data: config } = useQuery({
    queryKey: ["config"],
    queryFn: api.getConfig,
  });

  const { data: backupsData } = useQuery({
    queryKey: ["database-backups"],
    queryFn: api.listDatabaseBackups,
  });

  const save = useMutation({
    mutationFn: () =>
      api.updateConfig({
        inbox_path: form.inbox_path ?? config?.inbox_path,
        recipes_path: form.recipes_path ?? config?.recipes_path,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["config"] });
    },
  });

  const backup = useMutation({
    mutationFn: api.createDatabaseBackup,
    onSuccess: (result) => {
      setBackupMessage(`Created ${result.filename} (${formatBytes(result.size_bytes)})`);
      qc.invalidateQueries({ queryKey: ["database-backups"] });
    },
    onError: (err: Error) => setBackupMessage(err.message || "Backup failed"),
  });

  if (!config) return <div>Loading…</div>;

  const val = (key: "inbox_path" | "recipes_path") =>
    form[key] ?? config[key] ?? "";

  const backups = (backupsData?.items ?? []).slice(0, 10);

  return (
    <div>
      <div className="page-header">
        <h2>Settings</h2>
      </div>

      <section className="settings-section">
        <h3 className="settings-section-title">Paths</h3>
        <p className="settings-section-desc">
          Inbox is where you drop scanned images. Catalog lives under{" "}
          <code>{config.kl_data_dir}</code>.
        </p>
        <div className="form-group">
          <label>Inbox path</label>
          <input
            value={val("inbox_path")}
            onChange={(e) => setForm((f) => ({ ...f, inbox_path: e.target.value }))}
          />
        </div>
        <div className="form-group">
          <label>Recipes path</label>
          <input
            value={val("recipes_path")}
            onChange={(e) => setForm((f) => ({ ...f, recipes_path: e.target.value }))}
          />
        </div>
        <div className="form-group">
          <label>Kitchen root</label>
          <input value={config.kl_root || ""} disabled />
        </div>
        <button className="btn" onClick={() => save.mutate()} disabled={save.isPending}>
          Save paths
        </button>
        {save.isSuccess && <p className="save-toast">Saved</p>}
      </section>

      <section className="settings-section">
        <h3 className="settings-section-title">Database backup</h3>
        <p className="settings-section-desc">
          Creates a SQLite copy under the catalog backups folder.
        </p>
        <button className="btn" onClick={() => backup.mutate()} disabled={backup.isPending}>
          {backup.isPending ? "Backing up…" : "Backup database"}
        </button>
        {backupMessage && <p className="save-toast">{backupMessage}</p>}
        {backups.length > 0 && (
          <ul className="backup-list">
            {backups.map((b) => (
              <li key={b.filename}>
                {b.filename} — {formatBytes(b.size_bytes)} —{" "}
                {new Date(b.created_at).toLocaleString()}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
