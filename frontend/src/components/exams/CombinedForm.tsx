"use client";

import { useState } from "react";

import type { AcademicSession } from "@/components/academics/types";
import { Button, ErrorBox, Field } from "@/components/ui";
import { api } from "@/lib/api";
import type { Combined, Exam } from "@/lib/exams";

/** Create or edit an annual result: which exams count and their weights (adding up to 100%). */
export function CombinedForm({
  session,
  exams,
  combined,
  onSaved,
}: {
  session: AcademicSession;
  exams: Exam[];
  combined?: Combined;
  onSaved: (c: Combined) => void;
}) {
  const [name, setName] = useState(combined?.name ?? `Annual Result ${session.name}`);
  const [weights, setWeights] = useState<Record<number, string>>(
    Object.fromEntries((combined?.components ?? []).map((c) => [c.exam, c.weight])),
  );
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  const chosen = exams.filter((e) => e.id in weights);
  const total = chosen.reduce((sum, e) => sum + (Number(weights[e.id]) || 0), 0);

  function toggle(id: number) {
    const next = { ...weights };
    if (id in next) delete next[id];
    else next[id] = "";
    setWeights(next);
  }

  function split() {
    if (!chosen.length) return;
    const each = Math.floor(100 / chosen.length);
    setWeights(Object.fromEntries(chosen.map((e, i) => [e.id, String(i === chosen.length - 1 ? 100 - each * (chosen.length - 1) : each)])));
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const saved = await api<Combined>(combined ? `/api/combined-results/${combined.id}/` : "/api/combined-results/", {
        method: combined ? "PATCH" : "POST",
        body: JSON.stringify({
          session: session.id,
          name,
          components: chosen.map((ex) => ({ exam: ex.id, weight: weights[ex.id] || "0" })),
        }),
      });
      onSaved(saved);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-3">
      <Field label="Name" value={name} onChange={(e) => setName(e.target.value)} required />
      <div>
        <div className="mb-1 flex items-center justify-between">
          <span className="text-sm font-medium">Exams and weightage</span>
          {chosen.length > 1 && (
            <button type="button" onClick={split} className="text-xs text-indigo-600 hover:underline">
              Split equally
            </button>
          )}
        </div>
        {exams.length === 0 ? (
          <p className="text-sm text-slate-500">No exams in this session yet.</p>
        ) : (
          <ul className="space-y-2">
            {exams.map((ex) => (
              <li key={ex.id} className="flex items-center gap-3 rounded-xl border border-slate-200 px-3 py-2 dark:border-slate-700">
                <label className="flex min-w-0 flex-1 cursor-pointer items-center gap-2 text-sm">
                  <input type="checkbox" checked={ex.id in weights} onChange={() => toggle(ex.id)} />
                  <span className="truncate font-medium">{ex.name}</span>
                </label>
                {ex.id in weights && (
                  <span className="flex items-center gap-1 text-sm">
                    <input
                      aria-label={`${ex.name} weight`}
                      type="number"
                      min="1"
                      max="100"
                      step="0.5"
                      required
                      value={weights[ex.id]}
                      onChange={(e) => setWeights({ ...weights, [ex.id]: e.target.value })}
                      className="w-20 rounded-lg border border-slate-300 bg-transparent px-2 py-1 text-right dark:border-slate-700"
                    />
                    %
                  </span>
                )}
              </li>
            ))}
          </ul>
        )}
        <p className={`mt-2 text-sm ${total === 100 ? "text-emerald-700 dark:text-emerald-400" : "text-amber-700 dark:text-amber-300"}`}>
          Total: {total}% {total === 100 ? "✓" : "(must be 100%)"}
        </p>
        <p className="text-xs text-slate-500">
          Example: First Term 25% + Mid-Term 25% + Final 50%. If a class does not take one of these exams, the others are scaled up to 100%.
        </p>
      </div>
      <ErrorBox error={error} />
      <Button type="submit" disabled={busy || !chosen.length || total !== 100}>
        {busy ? "Saving…" : combined ? "Save" : "Create annual result"}
      </Button>
    </form>
  );
}
