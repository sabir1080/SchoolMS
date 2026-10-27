"use client";

import { useCallback, useEffect, useState } from "react";

import type { Subject } from "@/components/academics/types";
import { useList } from "@/components/academics/useList";
import { Button, Card, ErrorBox, Field, SelectField } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { dayTitle, isoDay, shiftDay, type Homework } from "@/lib/homework";
import { formatDate } from "@/lib/navigation";
import { termsFor } from "@/lib/terms";
import { useLatestRequest } from "@/lib/useLatestRequest";

interface DiarySection {
  id: number;
  program_name: string;
  name: string;
}

export default function HomeworkPage() {
  const { user } = useAuth();
  const terms = termsFor(user?.tenant);
  const sections = useList<DiarySection>("/api/homework/sections/");
  const [sectionId, setSectionId] = useState("");
  const [date, setDate] = useState(isoDay(new Date()));
  const [entries, setEntries] = useState<Homework[] | null>(null);
  const [editing, setEditing] = useState<Homework | "new" | null>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    if (!sectionId && sections.items.length) setSectionId(String(sections.items[0].id));
  }, [sections.items, sectionId]);

  const latest = useLatestRequest();
  const load = useCallback(() => {
    if (!sectionId) return;
    setEntries(null);
    latest(api<Homework[]>(`/api/homework/?section=${sectionId}&date=${date}`), setEntries, setError);
  }, [sectionId, date, latest]);
  useEffect(() => load(), [load]);

  async function remove(h: Homework) {
    if (!window.confirm(`Delete "${h.title}"?`)) return;
    try {
      await api(`/api/homework/${h.id}/`, { method: "DELETE" });
      load();
    } catch (err) {
      setError(err);
    }
  }

  const section = sections.items.find((s) => String(s.id) === sectionId);

  return (
    <div className="max-w-3xl space-y-4">
      <div className="flex items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold">Homework &amp; diary</h1>
        <button onClick={() => window.print()} className="text-sm text-brand-600 hover:underline print:hidden">
          Print
        </button>
      </div>

      {sections.loaded && !sections.items.length ? (
        <Card>
          <p className="text-sm text-slate-500">
            {user?.role === "teacher"
              ? `You can write the diary for ${terms.sections.toLowerCase()} you are class teacher of or teach in the timetable. None yet.`
              : `No ${terms.sections.toLowerCase()} in the current session yet.`}
          </p>
        </Card>
      ) : (
        <div className="flex flex-wrap items-end gap-3 print:hidden">
          <div className="w-full max-w-xs">
            <SelectField
              label={terms.section}
              value={sectionId}
              onChange={(e) => {
                setSectionId(e.target.value);
                setEditing(null);
              }}
              options={sections.items.map((s) => [String(s.id), `${s.program_name} - ${s.name}`])}
            />
          </div>
          <div className="flex items-center gap-1">
            <button onClick={() => setDate(shiftDay(date, -1))} className="rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-700" aria-label="Previous day">
              ‹
            </button>
            <input aria-label="Diary date" type="date" value={date} onChange={(e) => e.target.value && setDate(e.target.value)} className="rounded-lg border border-slate-300 bg-transparent px-3 py-2 text-sm dark:border-slate-700" />
            <button onClick={() => setDate(shiftDay(date, 1))} className="rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-700" aria-label="Next day">
              ›
            </button>
          </div>
        </div>
      )}
      <ErrorBox error={error} />

      {section && (
        <Card>
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <div>
              <h2 className="font-medium">
                {section.program_name} - {section.name}
              </h2>
              <p className="text-sm text-slate-500">{dayTitle(date)}</p>
            </div>
            {editing !== "new" && (
              <button onClick={() => setEditing("new")} className="rounded-lg bg-brand-600 px-3 py-2 text-sm font-medium text-white print:hidden">
                + Add homework
              </button>
            )}
          </div>
          {editing === "new" && (
            <HomeworkForm
              sectionId={Number(sectionId)}
              date={date}
              onDone={() => {
                setEditing(null);
                load();
              }}
            />
          )}
          {entries === null ? null : entries.length === 0 && editing !== "new" ? (
            <p className="text-sm text-slate-500">Nothing in the diary for this day.</p>
          ) : (
            <ul className="divide-y divide-slate-200 dark:divide-slate-800">
              {entries.map((h) =>
                editing !== null && editing !== "new" && editing.id === h.id ? (
                  <li key={h.id} className="py-3">
                    <HomeworkForm
                      sectionId={Number(sectionId)}
                      date={date}
                      homework={h}
                      onDone={() => {
                        setEditing(null);
                        load();
                      }}
                    />
                  </li>
                ) : (
                  <li key={h.id} className="py-3">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        {h.subject_name && <p className="text-xs font-semibold tracking-wide text-brand-600 uppercase">{h.subject_name}</p>}
                        <p className="font-medium">{h.title}</p>
                        {h.details && <p className="mt-1 text-sm whitespace-pre-line text-slate-600 dark:text-slate-300">{h.details}</p>}
                        <p className="mt-1 text-xs text-slate-500">
                          {h.due_date && `Due ${formatDate(h.due_date)} · `}
                          {h.created_by_name}
                        </p>
                      </div>
                      {h.can_edit && (
                        <span className="flex shrink-0 gap-3 text-xs print:hidden">
                          <button onClick={() => setEditing(h)} className="text-brand-600">
                            Edit
                          </button>
                          <button onClick={() => remove(h)} className="text-red-600">
                            Delete
                          </button>
                        </span>
                      )}
                    </div>
                  </li>
                ),
              )}
            </ul>
          )}
        </Card>
      )}
    </div>
  );
}

function HomeworkForm({ sectionId, date, homework, onDone }: { sectionId: number; date: string; homework?: Homework; onDone: () => void }) {
  const subjects = useList<Subject>("/api/academics/subjects/");
  const [form, setForm] = useState({
    subject: homework?.subject ? String(homework.subject) : "",
    title: homework?.title ?? "",
    details: homework?.details ?? "",
    due_date: homework?.due_date ?? "",
  });
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api(homework ? `/api/homework/${homework.id}/` : "/api/homework/", {
        method: homework ? "PATCH" : "POST",
        body: JSON.stringify({
          section: sectionId,
          date,
          subject: form.subject ? Number(form.subject) : null,
          title: form.title,
          details: form.details,
          due_date: form.due_date || null,
        }),
      });
      onDone();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="mb-3 space-y-3 rounded-xl border border-slate-200 p-3 print:hidden dark:border-slate-700">
      <div className="grid gap-3 sm:grid-cols-2">
        <SelectField
          label="Subject"
          value={form.subject}
          onChange={(e) => setForm({ ...form, subject: e.target.value })}
          options={[["", "General / note"], ...subjects.items.filter((s) => s.is_active).map((s) => [String(s.id), s.name] as [string, string])]}
        />
        <Field label="Due date (optional)" type="date" value={form.due_date} min={date} onChange={(e) => setForm({ ...form, due_date: e.target.value })} />
      </div>
      <Field label="Homework" placeholder="e.g. Exercise 4.2, questions 1–5" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} required maxLength={150} />
      <label className="block space-y-1">
        <span className="text-sm font-medium">Details (optional)</span>
        <textarea
          value={form.details}
          onChange={(e) => setForm({ ...form, details: e.target.value })}
          rows={3}
          className="w-full rounded-lg border border-slate-300 bg-transparent px-3 py-2 text-sm dark:border-slate-700"
        />
      </label>
      <ErrorBox error={error} />
      <div className="flex items-center gap-3">
        <Button type="submit" disabled={busy}>
          {busy ? "Saving…" : homework ? "Save" : "Add to diary"}
        </Button>
        <button type="button" onClick={onDone} className="text-sm text-slate-600 hover:underline dark:text-slate-300">
          Cancel
        </button>
      </div>
    </form>
  );
}
