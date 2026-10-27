"use client";

import { useEffect, useState } from "react";

import { ExamsTabs } from "@/components/exams/ExamsTabs";
import { Button, Card, ErrorBox, Field } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { GradeBand } from "@/lib/exams";

interface ExamSettings {
  pass_percentage: number;
  show_position: boolean;
}

export default function GradingPage() {
  const { user, refreshUser } = useAuth();
  const isAdmin = user?.role === "admin";
  const [bands, setBands] = useState<GradeBand[]>([]);
  const [settings, setSettings] = useState<ExamSettings | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [message, setMessage] = useState("");

  useEffect(() => {
    api<GradeBand[]>("/api/exams/grading/")
      .then((b) => setBands(b.map((x) => ({ ...x, min_percentage: x.min_percentage.replace(/\.00$/, "") }))))
      .catch(setError);
    if (isAdmin) api<ExamSettings>("/api/institute/settings/").then(setSettings).catch(setError);
  }, [isAdmin]);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setMessage("");
    try {
      const saved = await api<GradeBand[]>("/api/exams/grading/", { method: "PUT", body: JSON.stringify({ bands }) });
      setBands(saved.map((x) => ({ ...x, min_percentage: x.min_percentage.replace(/\.00$/, "") })));
      if (settings) {
        await api("/api/institute/settings/", { method: "PATCH", body: JSON.stringify(settings) });
        refreshUser();
      }
      setMessage("Saved.");
    } catch (err) {
      setError(err);
    }
  }

  const set = (i: number, key: keyof GradeBand, value: string) => setBands(bands.map((b, j) => (j === i ? { ...b, [key]: value } : b)));

  return (
    <div className="max-w-2xl space-y-4">
      <h1 className="text-2xl font-semibold">Exams</h1>
      <ExamsTabs />
      <form onSubmit={save} className="space-y-4">
        {settings && (
          <Card>
            <h2 className="mb-3 font-medium">Passing and position</h2>
            <div className="grid gap-3 sm:grid-cols-2">
              <Field
                label="Pass percentage in each subject"
                type="number"
                min="1"
                max="100"
                value={settings.pass_percentage}
                onChange={(e) => setSettings({ ...settings, pass_percentage: Number(e.target.value) })}
              />
              <label className="flex items-center gap-2 self-end pb-2 text-sm">
                <input type="checkbox" checked={settings.show_position} onChange={(e) => setSettings({ ...settings, show_position: e.target.checked })} />
                Show class position (1st, 2nd, 3rd) on report cards
              </label>
            </div>
            <p className="mt-2 text-xs text-slate-500">New papers get pass marks from this percentage; you can still change each paper.</p>
          </Card>
        )}
        <Card>
          <h2 className="mb-1 font-medium">Grading scale</h2>
          <p className="mb-3 text-sm text-slate-500">A student gets the highest grade whose starting percentage they reach.</p>
          <div className="space-y-2">
            {bands.map((b, i) => (
              <div key={i} className="grid grid-cols-[4.5rem_5.5rem_1fr_auto] items-end gap-2">
                <Field label={i === 0 ? "Grade" : ""} aria-label={`Grade ${i + 1} name`} value={b.name} onChange={(e) => set(i, "name", e.target.value)} disabled={!isAdmin} required />
                <Field
                  label={i === 0 ? "From %" : ""}
                  aria-label={`Grade ${i + 1} from percent`}
                  type="number"
                  min="0"
                  max="100"
                  value={b.min_percentage}
                  onChange={(e) => set(i, "min_percentage", e.target.value)}
                  disabled={!isAdmin}
                  required
                />
                <Field label={i === 0 ? "Remark" : ""} aria-label={`Grade ${i + 1} remark`} value={b.remark} onChange={(e) => set(i, "remark", e.target.value)} disabled={!isAdmin} />
                {isAdmin && (
                  <button type="button" onClick={() => setBands(bands.filter((_, j) => j !== i))} className="pb-2 text-xs text-red-600" aria-label={`Remove grade ${b.name}`}>
                    ✕
                  </button>
                )}
              </div>
            ))}
          </div>
          {isAdmin && (
            <button type="button" onClick={() => setBands([...bands, { name: "", min_percentage: "", remark: "" }])} className="mt-3 text-sm text-indigo-600 hover:underline">
              + Add grade
            </button>
          )}
        </Card>
        <ErrorBox error={error} />
        {message && <p className="text-sm text-emerald-700">{message}</p>}
        {isAdmin && <Button type="submit">Save</Button>}
      </form>
    </div>
  );
}
