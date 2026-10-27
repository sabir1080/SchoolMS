"use client";

import { useEffect, useState } from "react";

import { Card } from "@/components/ui";
import { api } from "@/lib/api";
import { dayTitle, type Homework } from "@/lib/homework";
import { formatDate } from "@/lib/navigation";

/** The class diary of a parent's child or the logged-in student, newest day first. */
export function MyHomework({ student }: { student?: number }) {
  const [data, setData] = useState<{ today: string; entries: Homework[] } | null>(null);
  const [all, setAll] = useState(false);
  const query = student ? `?student=${student}` : "";

  useEffect(() => {
    api<{ today: string; entries: Homework[] }>(`/api/me/homework/${query}`).then(setData).catch(() => setData(null));
  }, [query]);

  if (!data || !data.entries.length) return null;
  const days = [...new Set(data.entries.map((h) => h.date))];
  const shown = all ? days : days.slice(0, 3);

  return (
    <Card>
      <h2 className="font-medium">Homework &amp; diary</h2>
      <div className="mt-2 space-y-3">
        {shown.map((d) => (
          <div key={d}>
            <p className="text-xs font-medium text-slate-500">{d === data.today ? "Today" : dayTitle(d)}</p>
            <ul className="mt-1 space-y-1.5">
              {data.entries
                .filter((h) => h.date === d)
                .map((h) => (
                  <li key={h.id} className="rounded-lg bg-slate-50 px-3 py-2 text-sm dark:bg-slate-800/60">
                    {h.subject_name && <span className="mr-1 font-semibold text-brand-600">{h.subject_name}:</span>}
                    <span className="font-medium">{h.title}</span>
                    {h.details && <span className="block text-xs whitespace-pre-line text-slate-600 dark:text-slate-300">{h.details}</span>}
                    {h.due_date && <span className={`block text-xs ${h.due_date <= data.today ? "text-amber-700 dark:text-amber-300" : "text-slate-500"}`}>Due {formatDate(h.due_date)}</span>}
                  </li>
                ))}
            </ul>
          </div>
        ))}
      </div>
      {days.length > 3 && (
        <button onClick={() => setAll(!all)} className="mt-2 text-sm text-brand-600 hover:underline">
          {all ? "Show less" : `Show all (${days.length} days)`}
        </button>
      )}
    </Card>
  );
}
