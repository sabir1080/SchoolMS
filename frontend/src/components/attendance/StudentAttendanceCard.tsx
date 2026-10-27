"use client";

import { useEffect, useState } from "react";

import { Card } from "@/components/ui";
import { api } from "@/lib/api";
import { percentText, percentTone, statusInfo, type StudentAttendance } from "@/lib/attendance";

/** Attendance summary for one student: today, this month and this session. */
export function StudentAttendanceCard({ url }: { url: string }) {
  const [data, setData] = useState<StudentAttendance | null>(null);

  useEffect(() => {
    api<StudentAttendance>(url).then(setData).catch(() => setData(null));
  }, [url]);

  if (!data) return null;
  const today = statusInfo(data.today);

  return (
    <Card>
      <h2 className="mb-3 font-medium">Attendance</h2>
      <dl className="grid grid-cols-3 gap-3 text-sm">
        <div>
          <dt className="text-slate-500">Today</dt>
          <dd className="font-semibold">{today ? today.label : "Not taken"}</dd>
        </div>
        <div>
          <dt className="text-slate-500">This month</dt>
          <dd className={`font-semibold ${percentTone(data.month_summary.percentage)}`}>{percentText(data.month_summary)}</dd>
          <dd className="text-xs text-slate-500">
            {data.month_summary.absent} absent · {data.month_summary.leave} leave
          </dd>
        </div>
        <div>
          <dt className="text-slate-500">Session{data.session_name ? ` ${data.session_name}` : ""}</dt>
          <dd className={`font-semibold ${percentTone(data.session_summary.percentage)}`}>{percentText(data.session_summary)}</dd>
          <dd className="text-xs text-slate-500">{data.session_summary.total} days</dd>
        </div>
      </dl>
      {data.records.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1" aria-label="This month day by day">
          {data.records.map((r) => {
            const info = statusInfo(r.status);
            return (
              <span
                key={r.date}
                title={`${r.date}: ${info?.label}`}
                className={`inline-flex h-7 w-7 items-center justify-center rounded text-xs text-white ${info?.dot}`}
              >
                {Number(r.date.slice(8))}
              </span>
            );
          })}
        </div>
      )}
    </Card>
  );
}
