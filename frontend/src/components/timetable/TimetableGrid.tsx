"use client";

import { useState } from "react";

import { DAY_SHORT, hm, type Entry, type Timetable } from "@/lib/timetable";

/**
 * A week timetable: a table on wide screens, one day at a time on phones.
 * ``show`` picks the second line of each cell (the teacher for a class, the class for a teacher).
 */
export function TimetableGrid({
  data,
  show,
  onCell,
}: {
  data: Timetable;
  show: "teacher" | "section";
  onCell?: (day: number, periodId: number, entry: Entry | undefined) => void;
}) {
  const todayShown = data.days.some((d) => d.day === data.today);
  const [day, setDay] = useState(todayShown ? data.today : (data.days[0]?.day ?? 0));
  const find = (d: number, p: number) => data.entries.find((e) => e.day === d && e.period === p);

  if (!data.periods.length) return <p className="text-sm text-slate-500">No periods yet. An admin sets them up under “Periods & days”.</p>;

  const cell = (d: number, periodId: number) => {
    const e = find(d, periodId);
    const content = e ? (
      <>
        <span className="block font-medium">{e.subject_name}</span>
        <span className="block text-xs text-slate-500">
          {show === "teacher" ? (e.teacher_name ?? "No teacher") : e.section_name}
          {e.room && ` · ${e.room}`}
        </span>
      </>
    ) : (
      <span className="text-xs text-slate-400">{onCell ? "+ Add" : "—"}</span>
    );
    return onCell ? (
      <button type="button" onClick={() => onCell(d, periodId, e)} className="w-full rounded-lg p-1 text-left hover:bg-brand-50 dark:hover:bg-brand-950" aria-label={`${DAY_SHORT[d]} ${data.periods.find((p) => p.id === periodId)?.name}`}>
        {content}
      </button>
    ) : (
      <div className="p-1">{content}</div>
    );
  };

  return (
    <>
      <div className="hidden overflow-x-auto md:block print:block">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="text-left text-xs text-slate-500">
              <th className="w-28 border-b border-slate-200 px-2 py-2 font-normal dark:border-slate-800">Period</th>
              {data.days.map((d) => (
                <th key={d.day} className={`border-b border-slate-200 px-2 py-2 font-medium dark:border-slate-800 ${d.day === data.today ? "text-brand-600" : ""}`}>
                  {d.name}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.periods.map((p) =>
              p.is_break ? (
                <tr key={p.id} className="bg-slate-50 dark:bg-slate-800/50">
                  <td className="px-2 py-1.5 text-xs text-slate-500">
                    {hm(p.start_time)}–{hm(p.end_time)}
                  </td>
                  <td colSpan={data.days.length} className="px-2 py-1.5 text-center text-xs font-medium tracking-wide text-slate-500 uppercase">
                    {p.name}
                  </td>
                </tr>
              ) : (
                <tr key={p.id} className="border-b border-slate-100 align-top dark:border-slate-800">
                  <td className="px-2 py-2">
                    <span className="block font-medium">{p.name}</span>
                    <span className="text-xs text-slate-500">
                      {hm(p.start_time)}–{hm(p.end_time)}
                    </span>
                  </td>
                  {data.days.map((d) => (
                    <td key={d.day} className="px-1 py-1">
                      {cell(d.day, p.id)}
                    </td>
                  ))}
                </tr>
              ),
            )}
          </tbody>
        </table>
      </div>

      <div className="md:hidden print:hidden">
        <div className="-mx-4 mb-3 flex gap-1 overflow-x-auto px-4">
          {data.days.map((d) => (
            <button
              key={d.day}
              onClick={() => setDay(d.day)}
              className={`rounded-full px-3 py-1 text-sm ${d.day === day ? "bg-brand-600 font-medium text-white" : "bg-slate-100 dark:bg-slate-800"}`}
            >
              {DAY_SHORT[d.day]}
              {d.day === data.today && " •"}
            </button>
          ))}
        </div>
        <ul className="divide-y divide-slate-200 dark:divide-slate-800">
          {data.periods.map((p) => (
            <li key={p.id} className={`flex items-center gap-3 py-2 ${p.is_break ? "text-slate-500" : ""}`}>
              <span className="w-20 shrink-0 text-xs text-slate-500">
                {hm(p.start_time)}–{hm(p.end_time)}
              </span>
              {p.is_break ? <span className="text-xs font-medium uppercase">{p.name}</span> : <span className="min-w-0 flex-1">{cell(day, p.id)}</span>}
            </li>
          ))}
        </ul>
      </div>
    </>
  );
}
