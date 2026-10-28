"use client";

import { useCallback, useEffect, useState } from "react";

import { Button, Card, ErrorBox } from "@/components/ui";
import { TenantBackups } from "@/components/backups/TenantBackups";
import { api, downloadFile } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatDate } from "@/lib/navigation";

interface Status {
  last_file: string | null;
  last_excel: string | null;
  days_since_file: number | null;
  last_auto: string | null;
  auto_backup: boolean;
}

/** Institute settings: the institute downloads its own data (backup file and Excel copy). */
export function DataBackupCard() {
  const { user } = useAuth();
  const [status, setStatus] = useState<Status | null>(null);
  const [busy, setBusy] = useState<"file" | "excel" | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [listKey, setListKey] = useState(0);

  const load = useCallback(() => {
    api<Status>("/api/institute/backup/status/").then(setStatus).catch(() => setStatus(null));
  }, []);
  useEffect(load, [load]);

  async function get(kind: "file" | "excel") {
    setBusy(kind);
    setError(null);
    try {
      if (kind === "file") await downloadFile("/api/institute/backup/", "backup.json.gz");
      else await downloadFile("/api/institute/backup/excel/", "data.xlsx");
      load();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(null);
    }
  }

  async function toggleAuto(on: boolean) {
    setError(null);
    try {
      setStatus(await api<Status>("/api/institute/backup/status/", { method: "PATCH", body: JSON.stringify({ auto_backup: on }) }));
      setListKey((k) => k + 1);
    } catch (err) {
      setError(err);
    }
  }

  const overdue = status && (status.days_since_file === null || status.days_since_file >= 30);

  return (
    <Card>
      <h2 className="font-medium">Data backup</h2>
      <p className="mt-1 text-sm text-slate-500">
        Download a copy of all your institute&apos;s data: students, parents, attendance, fees and receipts, exams and results, timetable,
        homework, staff and settings. Keep it in Google Drive or another safe place.
      </p>
      {status && (
        <p className={`mt-2 text-sm ${overdue ? "font-medium text-amber-700" : "text-slate-600 dark:text-slate-300"}`} data-testid="institute-backup-status">
          {status.last_file ? `Last backup: ${formatDate(status.last_file)}` : "No backup downloaded yet."}
          {overdue && " We suggest downloading one every month."}
        </p>
      )}
      {status && (
        <div className="mt-3 rounded-lg border border-slate-200 p-3 dark:border-slate-800">
          <label className="flex items-center justify-between gap-3">
            <span className="text-sm font-medium">Automatic daily backup</span>
            <input
              type="checkbox"
              role="switch"
              aria-label="Automatic daily backup"
              checked={status.auto_backup}
              disabled={busy !== null}
              onChange={(e) => toggleAuto(e.target.checked)}
              className="h-5 w-5 accent-brand-600"
            />
          </label>
          <p className="mt-1 text-xs text-slate-500" data-testid="auto-backup-status">
            {status.auto_backup
              ? "On: the app saves a copy of your data every day it is used and keeps the last 14 days (listed below)."
              : "Off: only the backups you make yourself (Back up now or Download backup)."}
            {status.auto_backup && status.last_auto && ` Last: ${formatDate(status.last_auto)}.`}
          </p>
        </div>
      )}
      <div className="mt-3 flex flex-wrap gap-2">
        <Button type="button" onClick={() => get("file")} disabled={busy !== null}>
          {busy === "file" ? "Preparing…" : "Download backup"}
        </Button>
        <button
          type="button"
          onClick={() => get("excel")}
          disabled={busy !== null}
          className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium dark:border-slate-700"
        >
          {busy === "excel" ? "Preparing…" : "Download in Excel"}
        </button>
      </div>
      <p className="mt-2 text-xs text-slate-500">
        If something goes wrong, restore your data from this file below (or send it to the SchoolMS team). It does not contain your
        payment gateway keys. The Excel file has sheets you can open yourself (students, bills, payments, results, attendance, staff).
      </p>
      <ErrorBox error={error} />
      {user?.tenant && (
        <div className="mt-4">
          <TenantBackups key={listKey} code={user.tenant.slug} />
        </div>
      )}
    </Card>
  );
}
