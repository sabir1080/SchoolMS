"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Card } from "@/components/ui";
import { api } from "@/lib/api";
import { RESULT_LABEL, ordinal, type MyResults } from "@/lib/exams";

/** Published exam and annual results of a parent's child or the logged-in student, with links to report cards. */
export function MyResultsCard({ student }: { student?: number }) {
  const [data, setData] = useState<MyResults | null>(null);
  const query = student ? `?student=${student}` : "";

  useEffect(() => {
    api<MyResults>(`/api/me/results/${query}`).then(setData).catch(() => setData(null));
  }, [query]);

  if (!data || (!data.exams.length && !data.combined.length)) return null;
  const items = [
    ...data.combined.map((c) => ({ key: `c${c.combined.id}`, name: c.combined.name, row: c.students[0], href: `kind=combined&id=${c.combined.id}`, annual: true })),
    ...[...data.exams].reverse().map((e) => ({ key: `e${e.exam.id}`, name: e.exam.name, row: e.students[0], href: `kind=exam&id=${e.exam.id}`, annual: false })),
  ].filter((i) => i.row);

  return (
    <Card>
      <h2 className="font-medium">Results</h2>
      <ul className="mt-2 divide-y divide-slate-200 dark:divide-slate-800">
        {items.map(({ key, name, row, href, annual }) => (
          <li key={key} className="py-2">
            <Link href={`/my-result/?${href}${student ? `&student=${student}` : ""}`} className="flex items-center justify-between gap-3">
              <span className="min-w-0">
                <span className="block font-medium">
                  {name}
                  {annual && (
                    <span className="ml-2 rounded-full bg-indigo-50 px-2 py-0.5 align-middle text-[10px] font-medium whitespace-nowrap text-indigo-700 dark:bg-indigo-950 dark:text-indigo-200">
                      Annual
                    </span>
                  )}
                </span>
                <span className="text-xs text-slate-500">
                  {row.percentage ? `${row.percentage}%` : "—"} · Grade {row.grade ?? "—"}
                  {row.position ? ` · ${ordinal(row.position)} position` : ""}
                </span>
              </span>
              <span className="flex shrink-0 items-center gap-2 text-sm">
                <span className={`font-medium ${RESULT_LABEL[row.result].tone}`}>{RESULT_LABEL[row.result].label}</span>
                <span className="text-indigo-600">
                  <span className="hidden sm:inline">Report card </span>›
                </span>
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </Card>
  );
}
