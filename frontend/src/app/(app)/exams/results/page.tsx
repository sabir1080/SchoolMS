"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { ExamStatusBadge } from "@/components/exams/ExamsTabs";
import { ReportCard } from "@/components/exams/ReportCard";
import { ResultSummary } from "@/components/exams/ResultSummary";
import { Card, ErrorBox } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { EXAM_STATUS, RESULT_LABEL, ordinal, type ExamResults, type MarksProgress } from "@/lib/exams";
import { termsFor } from "@/lib/terms";

export default function ResultsPage() {
  const { user } = useAuth();
  const terms = termsFor(user?.tenant);
  const [examId, setExamId] = useState("");
  const [progress, setProgress] = useState<MarksProgress | null>(null);
  const [sectionId, setSectionId] = useState("");
  const [data, setData] = useState<ExamResults | null>(null);
  const [printing, setPrinting] = useState<"sheet" | "cards">("sheet");
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const id = params.get("id") ?? "";
    setExamId(id);
    setSectionId(params.get("section") ?? "");
    api<MarksProgress>(`/api/exams/${id}/marks/progress/`)
      .then((p) => setProgress({ ...p, sections: p.sections.filter((s) => s.can_see_result) }))
      .catch(setError);
  }, []);

  useEffect(() => {
    if (progress?.sections.length && !progress.sections.some((s) => String(s.id) === sectionId)) {
      setSectionId(String(progress.sections[0].id));
    }
  }, [progress, sectionId]);

  const load = useCallback(() => {
    if (!examId || !sectionId) return;
    setData(null);
    window.history.replaceState(null, "", `?id=${examId}&section=${sectionId}`);
    api<ExamResults>(`/api/exams/${examId}/results/?section=${sectionId}&attendance=1`).then(setData).catch(setError);
  }, [examId, sectionId]);

  useEffect(load, [load]);

  function print(mode: "sheet" | "cards") {
    setPrinting(mode);
    setTimeout(() => window.print(), 50);
  }

  if (!progress) return <ErrorBox error={error} />;
  const chip = (active: boolean) =>
    `rounded-full border px-3 py-1 text-sm whitespace-nowrap ${
      active ? "border-indigo-500 bg-indigo-50 font-medium text-indigo-700 dark:bg-indigo-950 dark:text-indigo-200" : "border-slate-300 dark:border-slate-700"
    }`;

  return (
    <div className="space-y-4">
      <div className="print:hidden">
        <Link href={`/exams/exam/?id=${examId}`} className="text-sm text-indigo-600 hover:underline">
          ← {progress.exam.name}
        </Link>
        <div className="mt-1 flex flex-wrap items-center justify-between gap-2">
          <h1 className="text-2xl font-semibold">Result</h1>
          <ExamStatusBadge {...EXAM_STATUS[progress.exam.status]} />
        </div>
        {progress.exam.status !== "published" && (
          <p className="mt-2 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800 dark:bg-amber-950 dark:text-amber-200">
            Preview: the result is not published yet, so parents and students cannot see it.
          </p>
        )}
      </div>
      <ErrorBox error={error} />

      {progress.sections.length === 0 ? (
        <Card>
          <p className="text-sm text-slate-500">
            {user?.role === "teacher" ? `You are not the class teacher of a ${terms.section.toLowerCase()} in this exam.` : `No ${terms.sections.toLowerCase()} in this exam yet.`}
          </p>
        </Card>
      ) : (
        <div className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-1 print:hidden">
          {progress.sections.map((s) => (
            <button key={s.id} onClick={() => setSectionId(String(s.id))} className={chip(String(s.id) === sectionId)}>
              {s.program_name} - {s.name}
            </button>
          ))}
        </div>
      )}

      {data && (
        <>
          {/* The result sheet is wide, so it prints in landscape; report cards print in portrait. */}
          <style>{`@media print { @page { size: A4 ${printing === "sheet" ? "landscape" : "portrait"}; margin: 12mm; } }`}</style>
          <div className={printing === "cards" ? "print:hidden" : ""}>
            <Summary data={data} />
            <div className="mt-4 flex flex-wrap gap-2 print:hidden">
              <button onClick={() => print("sheet")} className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium dark:border-slate-700">
                Print result sheet
              </button>
              <button onClick={() => print("cards")} disabled={!data.students.length} className="rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white disabled:opacity-50">
                Print all report cards
              </button>
            </div>
            <Sheet data={data} examId={examId} sectionId={sectionId} />
          </div>
          {printing === "cards" && (
            <div className="hidden print:block">
              {data.students.map((row, i) => (
                <div key={row.student} style={i < data.students.length - 1 ? { breakAfter: "page" } : undefined}>
                  <ReportCard data={data} row={row} tenant={user?.tenant} />
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}

function Summary({ data }: { data: ExamResults }) {
  return (
    <div>
      <div className="mb-2 hidden print:block">
        <p className="text-lg font-semibold">{data.institute.name}</p>
        <p className="text-sm">
          Result sheet · {data.exam.name} · {data.section.program_name} - {data.section.name} · Session {data.exam.session_name}
        </p>
      </div>
      <ResultSummary summary={data.summary} />
    </div>
  );
}

function Sheet({ data, examId, sectionId }: { data: ExamResults; examId: string; sectionId: string }) {
  if (!data.students.length) {
    return (
      <Card>
        <p className="text-sm text-slate-500">No students in this section.</p>
      </Card>
    );
  }
  const cell = "border-b border-slate-200 px-2 py-2 dark:border-slate-800 print:border-slate-300";
  return (
    <div className="mt-4 overflow-x-auto rounded-2xl bg-white shadow-sm dark:bg-slate-900 print:overflow-visible print:shadow-none">
      <table className="w-full text-sm print:text-[11px]">
        <thead>
          <tr className="text-left text-xs text-slate-500">
            {data.show_position && <th className={`${cell} font-normal`}>Pos.</th>}
            <th className={`${cell} sticky left-0 bg-white font-normal dark:bg-slate-900`}>Student</th>
            {data.papers.map((p) => (
              <th key={p.id} className={`${cell} text-right font-normal`}>
                {p.subject_name}
                <span className="block text-[10px]">/{p.total_marks}</span>
              </th>
            ))}
            <th className={`${cell} text-right font-normal`}>Total</th>
            <th className={`${cell} text-right font-normal`}>%</th>
            <th className={`${cell} text-center font-normal`}>Grade</th>
            <th className={`${cell} font-normal`}>Result</th>
            <th className={`${cell} print:hidden`} />
          </tr>
        </thead>
        <tbody>
          {data.students.map((r) => (
            <tr key={r.student}>
              {data.show_position && <td className={`${cell} font-semibold`}>{r.position ? ordinal(r.position) : "—"}</td>}
              <td className={`${cell} sticky left-0 bg-white dark:bg-slate-900`}>
                <span className="block font-medium whitespace-nowrap">{r.full_name}</span>
                <span className="text-xs text-slate-500">Roll {r.roll_number || "—"}</span>
              </td>
              {r.subjects.map((s) => (
                <td key={s.paper} className={`${cell} text-right ${s.passed === false ? "font-semibold text-red-600 dark:text-red-400" : ""}`}>
                  {s.absent ? "Abs" : (s.marks ?? "—")}
                </td>
              ))}
              <td className={`${cell} text-right font-medium whitespace-nowrap`}>
                {r.obtained}/{r.total}
              </td>
              <td className={`${cell} text-right`}>{r.percentage ?? "—"}</td>
              <td className={`${cell} text-center font-semibold`}>{r.grade ?? "—"}</td>
              <td className={`${cell} font-medium ${RESULT_LABEL[r.result].tone}`}>{RESULT_LABEL[r.result].label}</td>
              <td className={`${cell} print:hidden`}>
                <Link href={`/exams/report-card/?id=${examId}&section=${sectionId}&student=${r.student}`} className="text-xs whitespace-nowrap text-indigo-600 hover:underline">
                  Report card
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
