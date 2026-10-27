"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { CombinedCard } from "@/components/exams/CombinedCard";
import { ExamStatusBadge } from "@/components/exams/ExamsTabs";
import { ResultSummary } from "@/components/exams/ResultSummary";
import { Card, ErrorBox } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { COMBINED_STATUS, RESULT_LABEL, ordinal, type Combined, type CombinedResults } from "@/lib/exams";
import { termsFor } from "@/lib/terms";

interface Listing {
  combined: Combined;
  sections: CombinedResults["sections"];
}

export default function CombinedResultPage() {
  const { user } = useAuth();
  const terms = termsFor(user?.tenant);
  const [id, setId] = useState("");
  const [listing, setListing] = useState<Listing | null>(null);
  const [sectionId, setSectionId] = useState("");
  const [data, setData] = useState<CombinedResults | null>(null);
  const [printing, setPrinting] = useState<"sheet" | "cards">("sheet");
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const combinedId = params.get("id") ?? "";
    setId(combinedId);
    setSectionId(params.get("section") ?? "");
    api<Listing>(`/api/combined-results/${combinedId}/results/`).then(setListing).catch(setError);
  }, []);

  useEffect(() => {
    if (listing?.sections.length && !listing.sections.some((s) => String(s.id) === sectionId)) {
      setSectionId(String(listing.sections[0].id));
    }
  }, [listing, sectionId]);

  useEffect(() => {
    if (!id || !sectionId) return;
    setData(null);
    window.history.replaceState(null, "", `?id=${id}&section=${sectionId}`);
    api<CombinedResults>(`/api/combined-results/${id}/results/?section=${sectionId}&attendance=1`).then(setData).catch(setError);
  }, [id, sectionId]);

  function print(mode: "sheet" | "cards") {
    setPrinting(mode);
    setTimeout(() => window.print(), 50);
  }

  if (!listing) return <ErrorBox error={error} />;
  const chip = (active: boolean) =>
    `rounded-full border px-3 py-1 text-sm whitespace-nowrap ${
      active ? "border-brand-500 bg-brand-50 font-medium text-brand-700 dark:bg-brand-950 dark:text-brand-200" : "border-slate-300 dark:border-slate-700"
    }`;
  const cell = "border-b border-slate-200 px-2 py-2 dark:border-slate-800 print:border-slate-300";

  return (
    <div className="space-y-4">
      <style>{`@media print { @page { size: A4 ${printing === "sheet" ? "landscape" : "portrait"}; margin: 12mm; } }`}</style>
      <div className="print:hidden">
        <Link href="/exams/combined/" className="text-sm text-brand-600 hover:underline">
          ← Annual results
        </Link>
        <div className="mt-1 flex flex-wrap items-center justify-between gap-2">
          <h1 className="text-2xl font-semibold">{listing.combined.name}</h1>
          <ExamStatusBadge {...COMBINED_STATUS[listing.combined.status]} />
        </div>
        <p className="text-sm text-slate-500">{listing.combined.components.map((c) => `${c.exam_name} ${c.weight}%`).join(" + ")}</p>
        {listing.combined.status !== "published" && (
          <p className="mt-2 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800 dark:bg-amber-950 dark:text-amber-200">
            Preview: not published yet, so parents and students cannot see it.
          </p>
        )}
      </div>
      <ErrorBox error={error} />

      {listing.sections.length === 0 ? (
        <Card>
          <p className="text-sm text-slate-500">
            {user?.role === "teacher" ? `You are not the class teacher of a ${terms.section.toLowerCase()} in these exams.` : `No ${terms.sections.toLowerCase()} in these exams.`}
          </p>
        </Card>
      ) : (
        <div className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-1 print:hidden">
          {listing.sections.map((s) => (
            <button key={s.id} onClick={() => setSectionId(String(s.id))} className={chip(String(s.id) === sectionId)}>
              {s.program_name} - {s.name}
            </button>
          ))}
        </div>
      )}

      {data && (
        <>
          <div className={printing === "cards" ? "print:hidden" : ""}>
            <div className="mb-2 hidden print:block">
              <p className="text-lg font-semibold">{data.institute.name}</p>
              <p className="text-sm">
                {data.combined.name} · {data.section.program_name} - {data.section.name} · {data.exams.map((e) => `${e.name} ${e.weight}%`).join(" + ")}
              </p>
            </div>
            <ResultSummary summary={data.summary} />
            <div className="mt-4 flex flex-wrap gap-2 print:hidden">
              <button onClick={() => print("sheet")} className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium dark:border-slate-700">
                Print result sheet
              </button>
              <button onClick={() => print("cards")} disabled={!data.students.length} className="rounded-lg bg-brand-600 px-3 py-2 text-sm font-medium text-white disabled:opacity-50">
                Print all report cards
              </button>
            </div>
            {data.students.length === 0 ? (
              <Card>
                <p className="text-sm text-slate-500">No students in this section.</p>
              </Card>
            ) : (
              <div className="mt-4 overflow-x-auto rounded-2xl bg-white shadow-sm dark:bg-slate-900 print:overflow-visible print:shadow-none">
                <table className="w-full text-sm print:text-[11px]">
                  <thead>
                    <tr className="text-left text-xs text-slate-500">
                      {data.show_position && <th className={`${cell} font-normal`}>Pos.</th>}
                      <th className={`${cell} sticky left-0 bg-white font-normal dark:bg-slate-900`}>Student</th>
                      {data.exams.map((e) => (
                        <th key={e.id} className={`${cell} text-right font-normal`}>
                          {e.name}
                          <span className="block text-[10px]">{e.weight}%</span>
                        </th>
                      ))}
                      <th className={`${cell} text-right font-normal`}>Annual %</th>
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
                        {r.exams.map((e) => (
                          <td key={e.exam} className={`${cell} text-right`}>
                            {e.percentage ?? "—"}
                          </td>
                        ))}
                        <td className={`${cell} text-right font-semibold`}>{r.percentage ?? "—"}</td>
                        <td className={`${cell} text-center font-semibold`}>{r.grade ?? "—"}</td>
                        <td className={`${cell} font-medium ${RESULT_LABEL[r.result].tone}`}>
                          {RESULT_LABEL[r.result].label}
                          {r.result === "fail" && <span className="block text-xs font-normal">{r.failed_subjects} subject(s)</span>}
                        </td>
                        <td className={`${cell} print:hidden`}>
                          <Link href={`/exams/combined/card/?id=${id}&section=${sectionId}&student=${r.student}`} className="text-xs whitespace-nowrap text-brand-600 hover:underline">
                            Report card
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
          {printing === "cards" && (
            <div className="hidden print:block">
              {data.students.map((row, i) => (
                <div key={row.student} style={i < data.students.length - 1 ? { breakAfter: "page" } : undefined}>
                  <CombinedCard data={data} row={row} tenant={user?.tenant} />
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
