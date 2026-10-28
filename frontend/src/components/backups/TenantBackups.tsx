"use client";

import { useCallback, useEffect, useState } from "react";

import { ErrorBox } from "@/components/ui";
import { api, downloadFile } from "@/lib/api";
import { formatDate } from "@/lib/navigation";

interface Preview {
  source: "institute" | "full";
  created_at: string | null;
  with_secrets: boolean;
  institute: string;
  name: string;
  backup: Record<string, number>;
  current: Record<string, number>;
  restored: boolean;
  safety_snapshot?: number;
}

interface Snapshot {
  id: number;
  kind: "restore" | "auto" | "manual";
  day: string | null;
  reason: string;
  size_bytes: number;
  created_at: string;
  created_by_name: string | null;
}

const outline = "rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium disabled:opacity-60 dark:border-slate-700";

/** Restore one institute from a file, and the copies saved before each restore. The owner (Institutes → Manage)
 * also downloads the institute's backup and saved copies; an institute admin restores its own backup files. */
export function TenantBackups({ tenantId, code }: { tenantId?: number; code: string }) {
  const owner = tenantId !== undefined;
  const base = owner ? `/api/platform/tenants/${tenantId}` : "/api/institute/backup";
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [confirm, setConfirm] = useState("");
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [putBack, setPutBack] = useState<Snapshot | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [message, setMessage] = useState("");

  const loadSnapshots = useCallback(() => {
    api<Snapshot[]>(`${base}/snapshots/`).then(setSnapshots).catch(() => setSnapshots([]));
  }, [base]);
  useEffect(loadSnapshots, [loadSnapshots]);

  async function run(work: () => Promise<void>) {
    setBusy(true);
    setError(null);
    setMessage("");
    try {
      await work();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  const upload = (confirmCode?: string) => {
    const body = new FormData();
    body.append("file", file as File);
    if (confirmCode) body.append("confirm_code", confirmCode);
    return api<Preview>(`${base}/restore/`, { method: "POST", body });
  };

  const check = () => run(async () => setPreview(await upload()));

  const backUpNow = () =>
    run(async () => {
      await api(`${base}/snapshots/`, { method: "POST" });
      setMessage("Backup saved in the app. It is listed under Saved with Back up now.");
      loadSnapshots();
    });

  const restore = () =>
    run(async () => {
      const result = await upload(confirm);
      setPreview(null);
      setFile(null);
      setConfirm("");
      setMessage(`Restored ${result.name} from the backup. Its data before the restore was saved below, so you can put it back if needed.`);
      if (!owner) setTimeout(() => window.location.reload(), 2500);
      loadSnapshots();
    });

  const restoreSnapshot = () =>
    run(async () => {
      await api(`${base}/snapshots/${putBack!.id}/`, { method: "POST", body: JSON.stringify({ confirm_code: confirm }) });
      setMessage(`Put back the copy saved ${formatDate(putBack!.created_at)}.`);
      setPutBack(null);
      setConfirm("");
      loadSnapshots();
      if (!owner) setTimeout(() => window.location.reload(), 2500);
    });

  const names = preview ? Array.from(new Set([...Object.keys(preview.backup), ...Object.keys(preview.current)])).sort() : [];
  const confirmBox = (onGo: () => void, label: string, onCancel: () => void) => (
    <div className="mt-3 space-y-2">
      <label className="block text-sm">
        <span className="font-medium">
          Type the institute code <span className="font-mono">{code}</span> to confirm
        </span>
        <input
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          autoCapitalize="none"
          className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 sm:max-w-xs dark:border-slate-700 dark:bg-slate-900"
        />
      </label>
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={onGo}
          disabled={busy || confirm.trim().toLowerCase() !== code}
          className="rounded-lg bg-red-600 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
        >
          {busy ? "Restoring…" : label}
        </button>
        <button type="button" onClick={onCancel} disabled={busy} className={outline}>
          Cancel
        </button>
      </div>
    </div>
  );

  return (
    <div data-testid="tenant-backups">
      {owner && <h3 className="mb-2 text-sm font-medium">Backup &amp; restore (this institute only)</h3>}
      <div className="mb-3 flex flex-wrap gap-2">
        <button type="button" disabled={busy} className={outline} onClick={backUpNow}>
          Back up now (save in the app)
        </button>
        {owner && (
          <button type="button" disabled={busy} className={outline} onClick={() => run(() => downloadFile(`${base}/backup/`, `${code}-backup.json.gz`))}>
            Download this institute&apos;s backup
          </button>
        )}
      </div>

      <div className="rounded-lg border border-slate-200 p-3 dark:border-slate-800">
        <p className="text-sm font-medium">{owner ? "Restore this institute" : "Restore from a backup"}</p>
        <p className="text-xs text-slate-500">
          {owner
            ? "Choose this institute's backup file, or a full platform backup. Only this institute changes; other institutes, its plan, payments and agreements stay as they are."
            : "Choose a backup file you downloaded above (not changed). Your plan, payments and agreements stay as they are. Passwords go back to what they were on the backup date."}
        </p>
        <input
          type="file"
          accept=".gz,.json,application/gzip,application/json"
          aria-label="Backup file"
          className="mt-2 block w-full text-sm"
          onChange={(e) => {
            setFile(e.target.files?.[0] ?? null);
            setPreview(null);
            setConfirm("");
          }}
        />
        {file && !preview && (
          <button type="button" onClick={check} disabled={busy} className={`${outline} mt-2`}>
            {busy ? "Checking…" : "Check file"}
          </button>
        )}
        {preview && (
          <div className="mt-3 text-sm" data-testid="restore-preview">
            <p>
              {preview.source === "full" ? "Full platform backup" : "Institute backup"}
              {preview.created_at && ` made ${formatDate(preview.created_at)}`} for <b>{preview.name}</b>.
            </p>
            <div className="mt-2 overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="text-slate-500">
                    <th className="py-1 pr-3 font-medium">Data</th>
                    <th className="py-1 pr-3 font-medium">Now</th>
                    <th className="py-1 font-medium">After restore</th>
                  </tr>
                </thead>
                <tbody>
                  {names.map((n) => (
                    <tr key={n} className="border-t border-slate-100 dark:border-slate-800">
                      <td className="py-1 pr-3">{n}</td>
                      <td className="py-1 pr-3">{preview.current[n] ?? 0}</td>
                      <td className="py-1">{preview.backup[n] ?? 0}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="mt-2 rounded-lg bg-amber-50 px-3 py-2 text-amber-800">
              Everything this institute added or changed after the backup date will be replaced. Its current data is saved first, so the
              restore can be undone.
            </p>
            {confirmBox(restore, "Restore now", () => {
              setPreview(null);
              setConfirm("");
            })}
          </div>
        )}
      </div>

      {[
        { title: "Copies saved before a restore", items: snapshots.filter((s) => s.kind === "restore"), testId: "restore-copies" },
        { title: "Saved with Back up now (last 10)", items: snapshots.filter((s) => s.kind === "manual"), testId: "manual-backups" },
        { title: "Daily automatic backups (last 14 days)", items: snapshots.filter((s) => s.kind === "auto"), testId: "daily-backups" },
      ].map(
        (group) =>
          group.items.length > 0 && (
            <div key={group.testId} className="mt-3" data-testid={group.testId}>
              <p className="text-sm font-medium">{group.title}</p>
              <ul className="divide-y divide-slate-200 text-sm dark:divide-slate-800">
                {group.items.map((s) => (
                  <li key={s.id} className="py-2">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span>
                        {formatDate(s.created_at)}, {new Date(s.created_at).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}
                        {s.kind === "restore" && ` · ${s.reason}`}
                        {s.kind === "manual" && s.created_by_name && ` · by ${s.created_by_name}`} · {Math.max(1, Math.round(s.size_bytes / 1024))} KB
                      </span>
                      <span className="flex gap-3">
                        <button
                          type="button"
                          className="text-brand-600 hover:underline"
                          onClick={() => run(() => downloadFile(`${base}/snapshots/${s.id}/`, `${code}-saved.json.gz`))}
                        >
                          Download
                        </button>
                        <button
                          type="button"
                          className="text-brand-600 hover:underline"
                          onClick={() => {
                            setPutBack(s);
                            setConfirm("");
                          }}
                        >
                          Put back
                        </button>
                      </span>
                    </div>
                    {putBack?.id === s.id && confirmBox(restoreSnapshot, "Put this copy back", () => setPutBack(null))}
                  </li>
                ))}
              </ul>
            </div>
          ),
      )}
      <ErrorBox error={error} />
      {message && <p className="mt-2 rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{message}</p>}
    </div>
  );
}
