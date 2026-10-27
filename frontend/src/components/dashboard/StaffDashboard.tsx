"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Card, ErrorBox } from "@/components/ui";
import { api } from "@/lib/api";
import { percentTone, type Summary } from "@/lib/attendance";
import { useAuth } from "@/lib/auth";
import { money } from "@/lib/fees";
import { termsFor } from "@/lib/terms";

import { BarList, PairedColumns, PercentColumns } from "./charts";

interface DashboardData {
  session_name: string | null;
  counts: { students: number; new_admissions_this_month: number; teachers: number; sections: number; unassigned_students: number };
  students_by_program: { program: number; name: string; count: number }[];
  attendance?: {
    today: Summary;
    sections_with_students: number;
    marked_sections: number;
    trend: (Summary & { date: string })[];
    month: Summary;
    low_attendance_threshold: number;
    low_attendance: { student: number; full_name: string; class_name: string | null; percentage: number; absent: number; days: number }[];
  };
  fees?: {
    this_month: { month: string; billed: string; collected: string };
    trend: { month: string; billed: string; collected: string }[];
    outstanding: string;
    overdue_students: number;
  };
}

function dayLabel(iso: string) {
  return new Date(`${iso}T00:00:00`).toLocaleDateString(undefined, { day: "numeric", month: "short" });
}

function monthLabel(ym: string) {
  return new Date(`${ym}-01T00:00:00`).toLocaleDateString(undefined, { month: "short" });
}

function Tile({ label, value, note, href, tone = "" }: { label: string; value: string; note?: string; href?: string; tone?: string }) {
  const body = (
    <>
      <p className="text-xs text-slate-500">{label}</p>
      <p className={`text-2xl font-semibold ${tone}`}>{value}</p>
      {note && <p className="text-xs text-slate-500">{note}</p>}
    </>
  );
  const cls = "block rounded-2xl bg-white p-4 shadow-sm dark:bg-slate-900";
  return href ? (
    <Link href={href} className={`${cls} hover:ring-1 hover:ring-brand-200`}>
      {body}
    </Link>
  ) : (
    <div className={cls}>{body}</div>
  );
}

/** The admin / teacher dashboard: key numbers, trends and who needs attention. */
export function StaffDashboard() {
  const { user, subscription } = useAuth();
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState<unknown>(null);
  const terms = termsFor(user?.tenant);
  const currency = user?.tenant?.currency;
  const isAdmin = user?.role === "admin";

  useEffect(() => {
    if (subscription?.is_usable) api<DashboardData>("/api/dashboard/").then(setData).catch(setError);
  }, [subscription?.is_usable]);

  if (!data) return <ErrorBox error={error} />;
  const { counts, attendance, fees } = data;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Tile
          label={isAdmin ? "Active students" : `Students in my ${terms.sections.toLowerCase()}`}
          value={String(counts.students)}
          note={counts.new_admissions_this_month ? `${counts.new_admissions_this_month} new this month` : undefined}
          href="/students/"
        />
        {attendance && (
          <Tile
            label="Attendance today"
            value={attendance.today.percentage === null ? "—" : `${attendance.today.percentage}%`}
            tone={percentTone(attendance.today.percentage)}
            note={`${attendance.marked_sections} of ${attendance.sections_with_students} ${terms.sections.toLowerCase()} marked`}
            href="/attendance/"
          />
        )}
        {fees ? (
          <>
            <Tile label="Fees received this month" value={money(fees.this_month.collected, currency)} href="/fees/" />
            <Tile
              label="Fees still due"
              value={money(fees.outstanding, currency)}
              tone={Number(fees.outstanding) > 0 ? "text-red-600" : ""}
              note={
                fees.overdue_students
                  ? `${fees.overdue_students} student${fees.overdue_students === 1 ? "" : "s"} overdue`
                  : undefined
              }
              href="/fees/invoices/?status=overdue"
            />
          </>
        ) : (
          isAdmin && <Tile label="Teachers" value={String(counts.teachers)} href="/users/" />
        )}
        {!isAdmin && <Tile label={`My ${terms.sections.toLowerCase()}`} value={String(counts.sections)} />}
      </div>

      {isAdmin && counts.unassigned_students > 0 && (
        <p className="rounded-xl bg-amber-50 px-4 py-3 text-sm text-amber-900 dark:bg-amber-950 dark:text-amber-200">
          {counts.unassigned_students} active student{counts.unassigned_students === 1 ? " is" : "s are"} not in any{" "}
          {terms.section.toLowerCase()} this session.{" "}
          <Link href="/students/?unassigned=1" className="font-medium underline">
            View
          </Link>
        </p>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        {attendance && (
          <Card>
            <PercentColumns
              title="Attendance, last 14 school days"
              emptyText="No attendance taken yet."
              columns={attendance.trend.map((d) => ({
                key: d.date,
                label: dayLabel(d.date),
                value: d.percentage,
                detail: `${d.absent} absent, ${d.leave} leave`,
              }))}
            />
          </Card>
        )}
        {fees && (
          <Card>
            <PairedColumns
              title="Fees, last 6 months"
              seriesNames={["Billed", "Received"]}
              format={(n) => money(n, currency)}
              groups={fees.trend.map((m) => ({
                key: m.month,
                label: monthLabel(m.month),
                values: [Number(m.billed), Number(m.collected)],
              }))}
            />
          </Card>
        )}
        <Card>
          <BarList
            title={`Students per ${terms.program.toLowerCase()}${data.session_name ? ` (${data.session_name})` : ""}`}
            emptyText={`No students in any ${terms.section.toLowerCase()} yet.`}
            rows={data.students_by_program.map((p) => ({ key: String(p.program), label: p.name, value: p.count }))}
          />
        </Card>
        {attendance && (
          <Card>
            <h2 className="font-medium">Low attendance this month</h2>
            <p className="mb-2 text-xs text-slate-500">Below {attendance.low_attendance_threshold}% (at least 3 days taken).</p>
            {attendance.low_attendance.length === 0 ? (
              <p className="text-sm text-slate-500">No one below {attendance.low_attendance_threshold}%.</p>
            ) : (
              <ul className="divide-y divide-slate-200 text-sm dark:divide-slate-800">
                {attendance.low_attendance.map((s) => (
                  <li key={s.student}>
                    <Link href={`/students/view/?id=${s.student}`} className="flex items-center justify-between gap-3 py-2">
                      <span className="min-w-0">
                        <span className="block truncate font-medium">{s.full_name}</span>
                        <span className="text-xs text-slate-500">
                          {s.class_name} · {s.absent} absent of {s.days} days
                        </span>
                      </span>
                      <span className={`shrink-0 font-semibold ${percentTone(s.percentage)}`}>{s.percentage}%</span>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        )}
      </div>
    </div>
  );
}
