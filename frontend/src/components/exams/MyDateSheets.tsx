"use client";

import { useEffect, useState } from "react";

import { Card } from "@/components/ui";
import { api } from "@/lib/api";
import { marks, shortDate, timeText, type Paper } from "@/lib/exams";

interface MyExam {
  id: number;
  name: string;
  status: string;
  start_date: string | null;
  end_date: string | null;
  papers: Paper[];
}

/** Date sheets of announced exams for a parent's child or the logged-in student. */
export function MyDateSheets({ url }: { url: string }) {
  const [exams, setExams] = useState<MyExam[]>([]);

  useEffect(() => {
    api<MyExam[]>(url).then(setExams).catch(() => setExams([]));
  }, [url]);

  const upcoming = exams.filter((e) => e.status !== "published");
  if (upcoming.length === 0) return null;

  return (
    <>
      {upcoming.map((exam) => (
        <Card key={exam.id}>
          <h2 className="font-medium">{exam.name} — date sheet</h2>
          <ul className="mt-2 divide-y divide-slate-200 text-sm dark:divide-slate-800">
            {exam.papers.map((p) => (
              <li key={p.id} className="grid grid-cols-[1fr_1fr_auto] items-center gap-2 py-2">
                <span>
                  {shortDate(p.date)} <span className="text-xs whitespace-nowrap text-slate-500">{timeText(p.start_time)}</span>
                </span>
                <span className="font-medium">{p.subject_name}</span>
                <span className="text-xs text-slate-500">{marks(p.total_marks)} marks</span>
              </li>
            ))}
          </ul>
        </Card>
      ))}
    </>
  );
}
