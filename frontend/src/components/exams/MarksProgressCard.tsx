"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Card } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { MarksProgress } from "@/lib/exams";
import { termsFor } from "@/lib/terms";

/** How far marks entry has got, per section and subject, with links to enter marks. */
export function MarksProgressCard({ examId, status }: { examId: number; status: string }) {
  const { user } = useAuth();
  const terms = termsFor(user?.tenant);
  const [progress, setProgress] = useState<MarksProgress | null>(null);

  useEffect(() => {
    api<MarksProgress>(`/api/exams/${examId}/marks/progress/`).then(setProgress).catch(() => setProgress(null));
  }, [examId, status]);

  if (!progress) return null;
  return (
    <Card>
      <div className="mb-3 flex items-center justify-between gap-3">
        <h2 className="font-medium">Marks entry</h2>
        {progress.sections.length > 0 && (
          <div className="flex gap-4 text-sm">
            <Link href={`/exams/marks/?id=${examId}`} className="text-brand-600 hover:underline">
              {progress.can_enter ? "Enter marks →" : "View marks →"}
            </Link>
            {progress.sections.some((s) => s.can_see_result) && (
              <Link href={`/exams/results/?id=${examId}`} className="font-medium text-brand-600 hover:underline">
                Result →
              </Link>
            )}
          </div>
        )}
      </div>
      {progress.sections.length === 0 ? (
        <p className="text-sm text-slate-500">
          {user?.role === "teacher"
            ? `You don't teach a ${terms.section.toLowerCase()} in this exam (as class teacher or in the timetable).`
            : `No ${terms.sections.toLowerCase()} in these ${terms.programs.toLowerCase()} yet.`}
        </p>
      ) : (
        <ul className="divide-y divide-slate-200 text-sm dark:divide-slate-800">
          {progress.sections.map((s) => {
            const done = s.papers.filter((p) => s.student_count > 0 && p.entered >= s.student_count).length;
            return (
              <li key={s.id} className="py-2">
                <div className="flex items-center justify-between gap-2">
                  <Link href={`/exams/marks/?id=${examId}&section=${s.id}`} className="font-medium hover:underline">
                    {s.program_name} - {s.name}
                  </Link>
                  <span className={`text-xs ${done === s.papers.length && s.papers.length ? "text-emerald-700 dark:text-emerald-400" : "text-slate-500"}`}>
                    {done} of {s.papers.length} subjects complete
                  </span>
                </div>
                <div className="mt-1 flex flex-wrap gap-1">
                  {s.papers.map((p) => (
                    <Link
                      key={p.id}
                      href={`/exams/marks/?id=${examId}&section=${s.id}&paper=${p.id}`}
                      className={`rounded-full px-2 py-0.5 text-xs ${
                        s.student_count > 0 && p.entered >= s.student_count
                          ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300"
                          : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300"
                      }`}
                    >
                      {p.subject_name} {p.entered}/{s.student_count}
                    </Link>
                  ))}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </Card>
  );
}
