"use client";

import { useState } from "react";

import type { AcademicSession, Program } from "@/components/academics/types";
import { Button, ErrorBox, Field, SelectField } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { EXAM_TYPES, type Exam } from "@/lib/exams";
import { termsFor } from "@/lib/terms";

/** Create an exam, or edit one when ``exam`` is given. */
export function ExamForm({
  session,
  programs,
  exam,
  onSaved,
}: {
  session: AcademicSession;
  programs: Program[];
  exam?: Exam;
  onSaved: (exam: Exam) => void;
}) {
  const { user } = useAuth();
  const terms = termsFor(user?.tenant);
  const active = programs.filter((p) => p.is_active);
  const [form, setForm] = useState({
    name: exam?.name ?? "",
    exam_type: exam?.exam_type ?? "term",
    start_date: exam?.start_date ?? "",
    end_date: exam?.end_date ?? "",
    programs: exam?.programs ?? active.map((p) => p.id),
  });
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  function toggle(id: number) {
    setForm((f) => ({ ...f, programs: f.programs.includes(id) ? f.programs.filter((p) => p !== id) : [...f.programs, id] }));
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const saved = await api<Exam>(exam ? `/api/exams/${exam.id}/` : "/api/exams/", {
        method: exam ? "PATCH" : "POST",
        body: JSON.stringify({
          ...form,
          session: session.id,
          start_date: form.start_date || null,
          end_date: form.end_date || null,
        }),
      });
      if (!exam) setForm({ ...form, name: "" });
      onSaved(saved);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  const all = active.length > 0 && active.every((p) => form.programs.includes(p.id));

  return (
    <form onSubmit={onSubmit} className="space-y-3">
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Exam name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="e.g. First Term" required />
        <SelectField label="Type" options={EXAM_TYPES} value={form.exam_type} onChange={(e) => setForm({ ...form, exam_type: e.target.value })} />
        <Field label="Starts" type="date" value={form.start_date} onChange={(e) => setForm({ ...form, start_date: e.target.value })} />
        <Field label="Ends" type="date" value={form.end_date} onChange={(e) => setForm({ ...form, end_date: e.target.value })} />
      </div>
      <div>
        <div className="mb-1 flex items-center justify-between">
          <span className="text-sm font-medium">{terms.programs} taking this exam</span>
          <button
            type="button"
            onClick={() => setForm({ ...form, programs: all ? [] : active.map((p) => p.id) })}
            className="text-xs text-indigo-600 hover:underline"
          >
            {all ? "Clear" : "Select all"}
          </button>
        </div>
        <div className="flex flex-wrap gap-2">
          {active.map((p) => (
            <label
              key={p.id}
              className={`flex cursor-pointer items-center gap-2 rounded-full border px-3 py-1 text-sm ${
                form.programs.includes(p.id) ? "border-indigo-500 bg-indigo-50 dark:bg-indigo-950" : "border-slate-300 dark:border-slate-700"
              }`}
            >
              <input type="checkbox" checked={form.programs.includes(p.id)} onChange={() => toggle(p.id)} />
              {p.name}
            </label>
          ))}
        </div>
      </div>
      {!exam && (
        <p className="text-xs text-slate-500">
          Papers are added from each {terms.program.toLowerCase()}&apos;s subjects (100 marks each); you can change them next.
        </p>
      )}
      <ErrorBox error={error} />
      <Button type="submit" disabled={busy}>
        {busy ? "Saving…" : exam ? "Save exam" : "Create exam"}
      </Button>
    </form>
  );
}
