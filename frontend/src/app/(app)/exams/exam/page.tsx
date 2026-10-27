"use client";

import { useCallback, useEffect, useState } from "react";

import type { AcademicSession, Program, Subject } from "@/components/academics/types";
import { useList } from "@/components/academics/useList";
import { ExamForm } from "@/components/exams/ExamForm";
import { MarksProgressCard } from "@/components/exams/MarksProgressCard";
import { ExamStatusBadge, ExamsTabs } from "@/components/exams/ExamsTabs";
import { Button, Card, ErrorBox } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { EXAM_STATUS, EXAM_TYPES, marks, shortDate, timeText, type Exam, type ExamStatus, type Paper } from "@/lib/exams";
import { label } from "@/lib/students";
import { termsFor } from "@/lib/terms";

const NEXT_STEP: Record<ExamStatus, { to: ExamStatus; text: string } | null> = {
  draft: { to: "marks_open", text: "Open marks entry" },
  marks_open: { to: "published", text: "Publish result" },
  published: null,
};
const BACK_STEP: Record<ExamStatus, { to: ExamStatus; text: string } | null> = {
  draft: null,
  marks_open: { to: "draft", text: "Back to preparing" },
  published: { to: "marks_open", text: "Unpublish (reopen marks)" },
};

export default function ExamPage() {
  const { user } = useAuth();
  const terms = termsFor(user?.tenant);
  const isAdmin = user?.role === "admin";
  const [exam, setExam] = useState<Exam | null>(null);
  const [programId, setProgramId] = useState("");
  const [editing, setEditing] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const programs = useList<Program>("/api/academics/programs/");
  const sessions = useList<AcademicSession>("/api/academics/sessions/");

  useEffect(() => {
    const id = new URLSearchParams(window.location.search).get("id");
    api<Exam>(`/api/exams/${id}/`).then(setExam).catch(setError);
  }, []);

  useEffect(() => {
    if (exam && (!programId || !exam.programs.includes(Number(programId)))) {
      const first = programs.items.find((p) => exam.programs.includes(p.id));
      if (first) setProgramId(String(first.id));
    }
  }, [exam, programs.items, programId]);

  if (!exam) return <ErrorBox error={error} />;
  const examPrograms = programs.items.filter((p) => exam.programs.includes(p.id));
  const session = sessions.items.find((s) => s.id === exam.session);

  async function setStatus(status: ExamStatus) {
    try {
      setExam(await api<Exam>(`/api/exams/${exam!.id}/`, { method: "PATCH", body: JSON.stringify({ status }) }));
    } catch (err) {
      setError(err);
    }
  }

  const next = NEXT_STEP[exam.status];
  const back = BACK_STEP[exam.status];

  return (
    <div className="max-w-3xl space-y-4">
      <h1 className="text-2xl font-semibold print:hidden">Exams</h1>
      <ExamsTabs />
      <ErrorBox error={error} />

      <Card>
        <div className="hidden print:block">
          <p className="text-xl font-semibold">{user?.tenant?.name}</p>
          <p className="text-sm">Date sheet</p>
        </div>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-xl font-semibold">{exam.name}</h2>
            <p className="text-sm text-slate-500">
              {label(EXAM_TYPES, exam.exam_type)} · Session {exam.session_name}
              {exam.start_date && ` · ${shortDate(exam.start_date, true)}`}
              {exam.end_date && ` – ${shortDate(exam.end_date, true)}`}
            </p>
          </div>
          <span className="print:hidden">
            <ExamStatusBadge {...EXAM_STATUS[exam.status]} />
          </span>
        </div>
        {isAdmin && (
          <div className="mt-3 flex flex-wrap items-center gap-3 print:hidden">
            {next && <Button onClick={() => setStatus(next.to)}>{next.text}</Button>}
            {back && (
              <button onClick={() => setStatus(back.to)} className="text-sm text-slate-600 hover:underline dark:text-slate-300">
                {back.text}
              </button>
            )}
            <button onClick={() => setEditing(!editing)} className="text-sm text-indigo-600 hover:underline">
              {editing ? "Close" : "Edit exam"}
            </button>
          </div>
        )}
        {editing && session && (
          <div className="mt-4 border-t border-slate-200 pt-4 print:hidden dark:border-slate-800">
            <ExamForm
              session={session}
              programs={programs.items}
              exam={exam}
              onSaved={(saved) => {
                setExam(saved);
                setEditing(false);
              }}
            />
          </div>
        )}
      </Card>

      {exam.status !== "draft" && (
        <div className="print:hidden">
          <MarksProgressCard examId={exam.id} status={exam.status} />
        </div>
      )}

      {examPrograms.length > 0 && (
        <div className="-mx-4 overflow-x-auto px-4 print:hidden">
          <div className="flex w-max gap-1 rounded-xl bg-slate-200/60 p-1 dark:bg-slate-800" role="tablist" aria-label={terms.program}>
            {examPrograms.map((p) => (
              <button
                key={p.id}
                role="tab"
                aria-selected={String(p.id) === programId}
                onClick={() => setProgramId(String(p.id))}
                className={`rounded-lg px-3 py-1.5 text-sm whitespace-nowrap ${String(p.id) === programId ? "bg-white font-medium shadow-sm dark:bg-slate-900" : "text-slate-600 dark:text-slate-300"}`}
              >
                {p.name}
              </button>
            ))}
          </div>
        </div>
      )}

      {programId && (
        <Papers
          key={`${exam.id}-${programId}`}
          exam={exam}
          program={examPrograms.find((p) => String(p.id) === programId)!}
          editable={isAdmin}
        />
      )}
    </div>
  );
}

function Papers({ exam, program, editable }: { exam: Exam; program: Program; editable: boolean }) {
  const subjects = useList<Subject>("/api/academics/subjects/");
  const [papers, setPapers] = useState<Paper[] | null>(null);
  const [rows, setRows] = useState<Record<number, { total_marks: string; pass_marks: string; date: string; start_time: string }>>({});
  const [removed, setRemoved] = useState<number[]>([]);
  const [adding, setAdding] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [message, setMessage] = useState("");

  const show = useCallback((list: Paper[]) => {
    setPapers(list);
    setRows(
      Object.fromEntries(
        list.map((p) => [p.id, { total_marks: marks(p.total_marks), pass_marks: marks(p.pass_marks), date: p.date ?? "", start_time: p.start_time?.slice(0, 5) ?? "" }]),
      ),
    );
    setRemoved([]);
  }, []);

  useEffect(() => {
    api<Paper[]>(`/api/exams/${exam.id}/papers/?program=${program.id}`).then(show).catch(setError);
  }, [exam.id, program.id, show]);

  if (!papers) return <ErrorBox error={error} />;

  async function save(add: number[] = []) {
    setError(null);
    setMessage("");
    try {
      const result = await api<Paper[]>(`/api/exams/${exam.id}/papers/`, {
        method: "PUT",
        body: JSON.stringify({
          program: program.id,
          remove: removed,
          add,
          papers: papers!
            .filter((p) => !removed.includes(p.id))
            .map((p) => ({ id: p.id, ...rows[p.id], date: rows[p.id].date || null, start_time: rows[p.id].start_time || null })),
        }),
      });
      show(result);
      setAdding("");
      setMessage("Saved.");
    } catch (err) {
      setRemoved([]);
      setError(err);
    }
  }

  const visible = papers.filter((p) => !removed.includes(p.id));
  const missing = subjects.items.filter((s) => s.is_active && !papers.some((p) => p.subject === s.id));
  const set = (id: number, key: "total_marks" | "pass_marks" | "date" | "start_time", value: string) =>
    setRows({ ...rows, [id]: { ...rows[id], [key]: value } });
  const input = "w-full rounded-lg border border-slate-300 bg-transparent px-2 py-1.5 text-sm dark:border-slate-700";

  return (
    <Card>
      <div className="mb-3 flex items-center justify-between gap-3">
        <h2 className="font-medium">
          {program.name} · date sheet <span className="text-sm font-normal text-slate-500">({visible.length} {visible.length === 1 ? "paper" : "papers"})</span>
        </h2>
        <button onClick={() => window.print()} className="text-sm text-indigo-600 hover:underline print:hidden">
          Print
        </button>
      </div>

      {visible.length === 0 ? (
        <p className="text-sm text-slate-500">No papers yet. Add subjects below.</p>
      ) : !editable ? (
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-slate-500">
              <th className="py-1 font-normal">Date</th>
              <th className="py-1 font-normal">Subject</th>
              <th className="py-1 text-right font-normal">Marks</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((p) => (
              <tr key={p.id} className="border-t border-slate-100 dark:border-slate-800">
                <td className="py-2">
                  {shortDate(p.date)} <span className="text-xs text-slate-500">{timeText(p.start_time)}</span>
                </td>
                <td className="py-2 font-medium">{p.subject_name}</td>
                <td className="py-2 text-right">
                  {marks(p.total_marks)} <span className="text-xs text-slate-500">(pass {marks(p.pass_marks)})</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <>
          <ul className="space-y-3 print:hidden">
            {visible.map((p) => (
              <li key={p.id} className="rounded-xl border border-slate-200 p-3 dark:border-slate-700">
                <div className="mb-2 flex items-center justify-between">
                  <span className="font-medium">{p.subject_name}</span>
                  <button onClick={() => setRemoved([...removed, p.id])} className="text-xs text-red-600 hover:underline">
                    Remove
                  </button>
                </div>
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                  <label className="text-xs text-slate-500">
                    Total marks
                    <input aria-label={`${p.subject_name} total marks`} type="number" min="1" className={input} value={rows[p.id].total_marks} onChange={(e) => set(p.id, "total_marks", e.target.value)} />
                  </label>
                  <label className="text-xs text-slate-500">
                    Pass marks
                    <input aria-label={`${p.subject_name} pass marks`} type="number" min="0" className={input} value={rows[p.id].pass_marks} onChange={(e) => set(p.id, "pass_marks", e.target.value)} />
                  </label>
                  <label className="text-xs text-slate-500">
                    Date
                    <input aria-label={`${p.subject_name} date`} type="date" className={input} value={rows[p.id].date} onChange={(e) => set(p.id, "date", e.target.value)} />
                  </label>
                  <label className="text-xs text-slate-500">
                    Time
                    <input aria-label={`${p.subject_name} time`} type="time" className={input} value={rows[p.id].start_time} onChange={(e) => set(p.id, "start_time", e.target.value)} />
                  </label>
                </div>
              </li>
            ))}
          </ul>
          <table className="hidden w-full text-sm print:table">
            <tbody>
              {visible.map((p) => (
                <tr key={p.id} className="border-t border-slate-200">
                  <td className="py-2">
                    {shortDate(p.date)} {timeText(p.start_time)}
                  </td>
                  <td className="py-2 font-medium">{p.subject_name}</td>
                  <td className="py-2 text-right">{marks(p.total_marks)} marks</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}

      {editable && (
        <div className="mt-4 space-y-3 print:hidden">
          {missing.length > 0 && (
            <div className="flex flex-wrap items-center gap-2 text-sm">
              <select
                value={adding}
                onChange={(e) => setAdding(e.target.value)}
                aria-label="Add a subject"
                className="rounded-lg border border-slate-300 bg-transparent px-2 py-1.5 dark:border-slate-700 dark:bg-slate-900"
              >
                <option value="">+ Add a subject…</option>
                {missing.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
              {adding && (
                <button onClick={() => save([Number(adding)])} className="text-indigo-600 hover:underline">
                  Add
                </button>
              )}
            </div>
          )}
          <ErrorBox error={error} />
          {message && <p className="text-sm text-emerald-700">{message}</p>}
          <Button onClick={() => save()}>Save {program.name} papers</Button>
        </div>
      )}
    </Card>
  );
}
