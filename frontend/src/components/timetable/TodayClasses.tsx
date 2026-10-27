"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Card } from "@/components/ui";
import { api } from "@/lib/api";
import { hm, type Timetable } from "@/lib/timetable";

/** Today's periods for a parent's child or the logged-in student, with a link to the full week. */
export function TodayClasses({ student }: { student?: number }) {
  const [data, setData] = useState<Timetable | null>(null);
  const query = student ? `?student=${student}` : "";

  useEffect(() => {
    api<Timetable>(`/api/me/timetable/${query}`).then(setData).catch(() => setData(null));
  }, [query]);

  if (!data || !data.entries.length) return null;
  const today = data.entries.filter((e) => e.day === data.today);
  const isSchoolDay = data.days.some((d) => d.day === data.today);

  return (
    <Card>
      <div className="flex items-center justify-between gap-2">
        <h2 className="font-medium">Today&apos;s classes</h2>
        <Link href={`/my-timetable/${query}`} className="text-sm text-indigo-600 hover:underline">
          Full timetable ›
        </Link>
      </div>
      {!isSchoolDay || !today.length ? (
        <p className="mt-2 text-sm text-slate-500">No classes today.</p>
      ) : (
        <ul className="mt-2 divide-y divide-slate-200 text-sm dark:divide-slate-800">
          {data.periods
            .filter((p) => !p.is_break)
            .map((p) => {
              const e = today.find((x) => x.period === p.id);
              return e ? (
                <li key={p.id} className="flex items-center gap-3 py-1.5">
                  <span className="w-20 shrink-0 text-xs text-slate-500">
                    {hm(p.start_time)}–{hm(p.end_time)}
                  </span>
                  <span className="font-medium">{e.subject_name}</span>
                  {e.teacher_name && <span className="ml-auto truncate text-xs text-slate-500">{e.teacher_name}</span>}
                </li>
              ) : null;
            })}
        </ul>
      )}
    </Card>
  );
}
