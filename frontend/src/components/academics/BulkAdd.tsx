"use client";

import { useState } from "react";

import { Button, ErrorBox } from "@/components/ui";
import { api } from "@/lib/api";

/** Textarea where each line becomes one new row (via a bulk-create endpoint). */
export function BulkAdd({
  url,
  label,
  example,
  onAdded,
}: {
  url: string;
  label: string;
  example: string[];
  onAdded: () => void;
}) {
  const [text, setText] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    const names = text.split("\n").map((line) => line.trim()).filter(Boolean);
    if (names.length === 0) return;
    setBusy(true);
    setError(null);
    setMessage("");
    try {
      const created = await api<unknown[]>(url, { method: "POST", body: JSON.stringify({ names }) });
      const skipped = names.length - created.length;
      setMessage(`Added ${created.length}.${skipped ? ` ${skipped} already existed and were skipped.` : ""}`);
      setText("");
      onAdded();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="space-y-2">
      <label className="block space-y-1">
        <span className="text-sm font-medium">{label}</span>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={5}
          placeholder={example.slice(0, 4).join("\n")}
          className="w-full rounded-lg border border-slate-300 bg-transparent px-3 py-2 text-sm outline-none focus:border-brand-500 dark:border-slate-700"
        />
      </label>
      <p className="text-xs text-slate-500">One per line.</p>
      <ErrorBox error={error} />
      {message && <p className="rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{message}</p>}
      <div className="flex flex-wrap gap-2">
        <Button type="submit" disabled={busy || !text.trim()}>
          {busy ? "Adding…" : "Add all"}
        </Button>
        <button
          type="button"
          onClick={() => setText(example.join("\n"))}
          className="rounded-lg border border-slate-300 px-4 py-2 text-sm dark:border-slate-700"
        >
          Fill example list
        </button>
      </div>
    </form>
  );
}
