"use client";

import { useCallback, useEffect, useState } from "react";

import { Card, ErrorBox } from "@/components/ui";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/navigation";

interface Item {
  id: number;
  kind: string;
  label: string;
  created_at: string;
  deleted_by_name: string | null;
  days_left: number;
}

/** Things deleted in the last 30 days: restore them or delete them for good. */
export default function RecycleBinPage() {
  const [items, setItems] = useState<Item[] | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState<number | null>(null);

  const load = useCallback(() => {
    api<Item[]>("/api/recycle-bin/").then(setItems).catch(setError);
  }, []);
  useEffect(load, [load]);

  async function act(item: Item, how: "restore" | "forever") {
    if (how === "forever" && !confirm(`Delete “${item.label}” for good? This cannot be undone.`)) return;
    setBusy(item.id);
    setError(null);
    setMessage("");
    try {
      await api(`/api/recycle-bin/${item.id}/`, { method: how === "restore" ? "POST" : "DELETE" });
      setMessage(how === "restore" ? `Restored: ${item.label}` : `Deleted for good: ${item.label}`);
      load();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="max-w-3xl space-y-4">
      <div>
        <h1 className="text-2xl font-semibold">Recycle bin</h1>
        <p className="text-sm text-slate-500">
          When you delete a student, payment, homework, exam, staff member, certificate or other record, it stays here for 30 days. Restore
          brings it back with everything that was deleted with it.
        </p>
      </div>
      <ErrorBox error={error} />
      {message && <p className="rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{message}</p>}
      {items === null ? (
        <p className="text-sm text-slate-500">Loading…</p>
      ) : items.length === 0 ? (
        <Card>
          <p className="text-sm text-slate-500">The recycle bin is empty.</p>
        </Card>
      ) : (
        <ul className="space-y-2">
          {items.map((item) => (
            <li key={item.id}>
              <Card>
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <span className="min-w-0">
                    <span className="block font-medium break-words">{item.label}</span>
                    <span className="block text-xs text-slate-500">
                      Deleted {formatDate(item.created_at)}
                      {item.deleted_by_name && ` by ${item.deleted_by_name}`} · {item.days_left} day{item.days_left === 1 ? "" : "s"} left
                    </span>
                  </span>
                  <span className="flex shrink-0 gap-2">
                    <button
                      type="button"
                      onClick={() => act(item, "restore")}
                      disabled={busy !== null}
                      className="rounded-lg bg-brand-600 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-60"
                    >
                      Restore
                    </button>
                    <button
                      type="button"
                      onClick={() => act(item, "forever")}
                      disabled={busy !== null}
                      className="rounded-lg border border-red-300 px-3 py-1.5 text-sm text-red-600 disabled:opacity-60"
                    >
                      Delete for good
                    </button>
                  </span>
                </div>
              </Card>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
