"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import { ExamStatusBadge } from "@/components/exams/ExamsTabs";
import { Button, Card, ErrorBox } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { EXAM_STATUS, marks, type MarksProgress, type MarksSheet } from "@/lib/exams";
import { termsFor } from "@/lib/terms";

interface Row {
  marks: string;
  absent: boolean;
}

export default function MarksPage() {
  const { user } = useAuth();
  const terms = termsFor(user?.tenant);
  const [examId, setExamId] = useState("");
  const [progress, setProgress] = useState<MarksProgress | null>(null);
  const [sectionId, setSectionId] = useState("");
  const [paperId, setPaperId] = useState("");
  const [dirty, setDirty] = useState(false);
  const [error, setError] = useState<unknown>(null);

  const loadProgress = useCallback((id: string) => {
    api<MarksProgress>(`/api/exams/${id}/marks/progress/`).then(setProgress).catch(setError);
  }, []);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const id = params.get("id") ?? "";
    setExamId(id);
    setSectionId(params.get("section") ?? "");
    setPaperId(params.get("paper") ?? "");
    loadProgress(id);
  }, [loadProgress]);

  // Pick the first section and subject when none is chosen (or the chosen one is not available).
  useEffect(() => {
    if (!progress || progress.sections.length === 0) return;
    const section = progress.sections.find((s) => String(s.id) === sectionId) ?? progress.sections[0];
    if (String(section.id) !== sectionId) setSectionId(String(section.id));
    if (section.papers.length && !section.papers.some((p) => String(p.id) === paperId)) {
      const firstOpen = section.papers.find((p) => p.entered < section.student_count) ?? section.papers[0];
      setPaperId(String(firstOpen.id));
    }
  }, [progress, sectionId, paperId]);

  useEffect(() => {
    if (examId && sectionId && paperId) {
      window.history.replaceState(null, "", `?id=${examId}&section=${sectionId}&paper=${paperId}`);
    }
  }, [examId, sectionId, paperId]);

  function choose(next: () => void) {
    if (dirty && !window.confirm("You have unsaved marks. Leave without saving?")) return;
    setDirty(false);
    next();
  }

  if (!progress) return <ErrorBox error={error} />;
  const section = progress.sections.find((s) => String(s.id) === sectionId);
  const chip = (active: boolean) =>
    `rounded-full border px-3 py-1 text-sm whitespace-nowrap ${
      active ? "border-indigo-500 bg-indigo-50 font-medium text-indigo-700 dark:bg-indigo-950 dark:text-indigo-200" : "border-slate-300 dark:border-slate-700"
    }`;

  return (
    <div className="max-w-3xl space-y-4">
      <div>
        <Link href={`/exams/exam/?id=${examId}`} className="text-sm text-indigo-600 hover:underline">
          ← {progress.exam.name}
        </Link>
        <div className="mt-1 flex flex-wrap items-center justify-between gap-2">
          <h1 className="text-2xl font-semibold">Marks entry</h1>
          <ExamStatusBadge {...EXAM_STATUS[progress.exam.status]} />
        </div>
      </div>
      {!progress.can_enter && (
        <p className="rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800 dark:bg-amber-950 dark:text-amber-200">
          {progress.exam.status === "draft"
            ? "Marks entry has not been opened for this exam yet."
            : "The result is published, so marks are locked. An admin can reopen marks entry."}
        </p>
      )}
      <ErrorBox error={error} />

      {progress.sections.length === 0 ? (
        <Card>
          <p className="text-sm text-slate-500">
            {user?.role === "teacher"
              ? `You are not the class teacher of a ${terms.section.toLowerCase()} in this exam. Ask your admin to assign you.`
              : `No ${terms.sections.toLowerCase()} in these ${terms.programs.toLowerCase()} yet. Add them in Academic setup.`}
          </p>
        </Card>
      ) : (
        <>
          <div>
            <p className="mb-1 text-sm font-medium">{terms.section}</p>
            <div className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-1">
              {progress.sections.map((s) => (
                <button key={s.id} onClick={() => choose(() => { setSectionId(String(s.id)); setPaperId(""); })} className={chip(String(s.id) === sectionId)}>
                  {s.program_name} - {s.name}
                </button>
              ))}
            </div>
          </div>
          {section && (
            <div>
              <p className="mb-1 text-sm font-medium">Subject</p>
              <div className="flex flex-wrap gap-2">
                {section.papers.map((p) => (
                  <button key={p.id} onClick={() => choose(() => setPaperId(String(p.id)))} className={chip(String(p.id) === paperId)}>
                    {p.subject_name}{" "}
                    <span className={p.entered >= section.student_count && section.student_count ? "text-emerald-700 dark:text-emerald-400" : "text-slate-500"}>
                      {p.entered}/{section.student_count}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}
          {section && paperId && section.papers.some((p) => String(p.id) === paperId) && (
            <Sheet
              key={`${sectionId}-${paperId}`}
              url={`/api/exams/${examId}/marks/?section=${sectionId}&paper=${paperId}`}
              saveUrl={`/api/exams/${examId}/marks/`}
              onDirty={setDirty}
              onSaved={() => loadProgress(examId)}
            />
          )}
        </>
      )}
    </div>
  );
}

function Sheet({ url, saveUrl, onDirty, onSaved }: { url: string; saveUrl: string; onDirty: (d: boolean) => void; onSaved: () => void }) {
  const [sheet, setSheet] = useState<MarksSheet | null>(null);
  const [rows, setRows] = useState<Record<number, Row>>({});
  const [error, setError] = useState<unknown>(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const inputs = useRef<(HTMLInputElement | null)[]>([]);

  const show = useCallback((data: MarksSheet) => {
    setSheet(data);
    setRows(Object.fromEntries(data.students.map((s) => [s.student, { marks: s.marks === null ? "" : marks(s.marks), absent: s.absent }])));
  }, []);

  useEffect(() => {
    api<MarksSheet>(url).then(show).catch(setError);
  }, [url, show]);

  if (!sheet) return <ErrorBox error={error} />;
  const total = Number(sheet.paper.total_marks);
  const editable = sheet.can_enter;

  function set(student: number, row: Partial<Row>) {
    setRows((r) => ({ ...r, [student]: { ...r[student], ...row } }));
    setMessage("");
    onDirty(true);
  }

  async function save() {
    setBusy(true);
    setError(null);
    setMessage("");
    try {
      const saved = await api<MarksSheet>(saveUrl, {
        method: "PUT",
        body: JSON.stringify({
          section: sheet!.section.id,
          paper: sheet!.paper.id,
          entries: sheet!.students.map((s) => ({
            student: s.student,
            absent: rows[s.student].absent,
            marks: rows[s.student].absent || rows[s.student].marks === "" ? null : rows[s.student].marks,
          })),
        }),
      });
      show(saved);
      onDirty(false);
      onSaved();
      setMessage("Marks saved.");
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  const entered = sheet.students.filter((s) => rows[s.student]?.absent || rows[s.student]?.marks !== "").length;
  const over = (r: Row) => !r.absent && r.marks !== "" && (Number(r.marks) > total || Number(r.marks) < 0);

  return (
    <Card>
      <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="font-medium">
          {sheet.paper.subject_name} · {sheet.section.program_name} - {sheet.section.name}
        </h2>
        <p className="text-sm text-slate-500">
          Out of {marks(sheet.paper.total_marks)} (pass {marks(sheet.paper.pass_marks)}) · {entered} of {sheet.students.length} entered
        </p>
      </div>
      {sheet.students.length === 0 ? (
        <p className="text-sm text-slate-500">No students in this section.</p>
      ) : (
        <ul className="divide-y divide-slate-200 dark:divide-slate-800">
          {sheet.students.map((s, i) => {
            const row = rows[s.student];
            const fail = !row.absent && row.marks !== "" && Number(row.marks) < Number(sheet.paper.pass_marks);
            return (
              <li key={s.student} className="flex items-center gap-3 py-2">
                <span className="w-8 shrink-0 text-right text-xs text-slate-500">{s.roll_number || "—"}</span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-medium">{s.full_name}</span>
                  <span className="text-xs text-slate-500">Adm {s.admission_no}</span>
                </span>
                <input
                  ref={(el) => {
                    inputs.current[i] = el;
                  }}
                  aria-label={`${s.full_name} marks`}
                  type="number"
                  inputMode="decimal"
                  min="0"
                  max={total}
                  step="0.5"
                  enterKeyHint="next"
                  disabled={!editable || row.absent}
                  value={row.absent ? "" : row.marks}
                  placeholder={row.absent ? "Absent" : ""}
                  onChange={(e) => set(s.student, { marks: e.target.value })}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      inputs.current.slice(i + 1).find((el) => el && !el.disabled)?.focus();
                    }
                  }}
                  className={`w-20 rounded-lg border bg-transparent px-2 py-1.5 text-right text-sm disabled:opacity-60 ${
                    over(row) ? "border-red-500 text-red-700" : fail ? "border-amber-400 text-amber-700 dark:text-amber-300" : "border-slate-300 dark:border-slate-700"
                  }`}
                />
                <label className="flex shrink-0 items-center gap-1 text-xs text-slate-600 dark:text-slate-300">
                  <input type="checkbox" checked={row.absent} disabled={!editable} onChange={(e) => set(s.student, { absent: e.target.checked })} aria-label={`${s.full_name} absent`} />
                  Absent
                </label>
              </li>
            );
          })}
        </ul>
      )}
      {editable && sheet.students.length > 0 && (
        <div className="sticky bottom-0 -mx-4 mt-3 space-y-2 border-t border-slate-200 bg-white px-4 pt-3 pb-2 md:-mx-6 md:px-6 dark:border-slate-800 dark:bg-slate-900">
          <ErrorBox error={error} />
          {message && <p className="text-sm text-emerald-700">{message}</p>}
          <Button onClick={save} disabled={busy || sheet.students.some((s) => over(rows[s.student]))}>
            {busy ? "Saving…" : "Save marks"}
          </Button>
        </div>
      )}
      {!editable && <ErrorBox error={error} />}
    </Card>
  );
}
