"use client";

import { useEffect, useState } from "react";

import { AttendanceTabs } from "@/components/attendance/AttendanceTabs";
import { useMySections } from "@/components/attendance/useMySections";
import { Card, ErrorBox, Field } from "@/components/ui";
import { api } from "@/lib/api";
import {
  localToday,
  percentText,
  percentTone,
  sectionText,
  statusInfo,
  type AttendanceStatus,
  type SectionInfo,
  type Summary,
} from "@/lib/attendance";
import { useAuth } from "@/lib/auth";
import { termsFor } from "@/lib/terms";

interface Report {
  section: SectionInfo;
  month: string;
  days: string[];
  summary: Summary;
  students: {
    student: number;
    full_name: string;
    roll_number: string;
    summary: Summary;
    days: Record<string, AttendanceStatus>;
  }[];
}

export default function AttendanceReportPage() {
  const { user } = useAuth();
  const terms = termsFor(user?.tenant);
  const { sections, error: sectionsError } = useMySections();
  const [sectionId, setSectionId] = useState("");
  const [month, setMonth] = useState(localToday().slice(0, 7));
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    if (!sectionId && sections?.length) setSectionId(String(sections[0].id));
  }, [sections, sectionId]);

  useEffect(() => {
    if (!sectionId || !month) return;
    api<Report>(`/api/attendance/report/?section=${sectionId}&month=${month}`)
      .then((r) => {
        setReport(r);
        setError(null);
      })
      .catch(setError);
  }, [sectionId, month]);

  if (sections === null) return null;

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Attendance</h1>
      <AttendanceTabs />
      <ErrorBox error={sectionsError || error} />

      <Card>
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="block space-y-1">
            <span className="text-sm font-medium">{terms.section}</span>
            <select
              value={sectionId}
              onChange={(e) => setSectionId(e.target.value)}
              className="w-full rounded-lg border border-slate-300 bg-transparent px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900"
            >
              {sections.map((s) => (
                <option key={s.id} value={s.id}>
                  {sectionText(s, terms.section)}
                </option>
              ))}
            </select>
          </label>
          <Field label="Month" type="month" value={month} max={localToday().slice(0, 7)} onChange={(e) => setMonth(e.target.value)} />
        </div>
      </Card>

      {report && (
        <>
          <Card>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="font-medium">{sectionText(report.section, terms.section)}</p>
              <p className="text-sm">
                {report.days.length} day{report.days.length === 1 ? "" : "s"} taken · Average{" "}
                <span className={`font-semibold ${percentTone(report.summary.percentage)}`}>{percentText(report.summary)}</span>
              </p>
            </div>
          </Card>

          {report.students.length === 0 ? (
            <Card>
              <p className="text-sm text-slate-500">No active students.</p>
            </Card>
          ) : (
            <Card>
              <div className="-mx-4 overflow-x-auto md:-mx-6">
                <table className="min-w-full text-sm">
                  <thead>
                    <tr className="text-left text-xs text-slate-500">
                      <th className="sticky left-0 bg-white px-4 py-2 md:px-6 dark:bg-slate-900">Student</th>
                      <th className="px-2 py-2 text-center">P</th>
                      <th className="px-2 py-2 text-center">A</th>
                      <th className="px-2 py-2 text-center">L</th>
                      <th className="px-2 py-2 text-center">Late</th>
                      <th className="px-2 py-2 text-center">%</th>
                      {report.days.map((d) => (
                        <th key={d} className="px-1 py-2 text-center font-normal">
                          {Number(d.slice(8))}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                    {report.students.map((row) => (
                      <tr key={row.student}>
                        <td className="sticky left-0 max-w-40 truncate bg-white px-4 py-2 md:px-6 dark:bg-slate-900">
                          {row.roll_number && <span className="mr-1 text-slate-500">{row.roll_number}.</span>}
                          {row.full_name}
                        </td>
                        <td className="px-2 py-2 text-center">{row.summary.present}</td>
                        <td className="px-2 py-2 text-center">{row.summary.absent}</td>
                        <td className="px-2 py-2 text-center">{row.summary.leave}</td>
                        <td className="px-2 py-2 text-center">{row.summary.late}</td>
                        <td className={`px-2 py-2 text-center font-semibold ${percentTone(row.summary.percentage)}`}>
                          {percentText(row.summary)}
                        </td>
                        {report.days.map((d) => {
                          const info = statusInfo(row.days[d]);
                          return (
                            <td key={d} className="px-1 py-2 text-center">
                              {info ? (
                                <span
                                  title={info.label}
                                  className={`inline-flex h-6 min-w-6 items-center justify-center rounded px-1 text-xs text-white ${info.dot}`}
                                >
                                  {info.short}
                                </span>
                              ) : (
                                <span className="text-slate-300">·</span>
                              )}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="mt-3 text-xs text-slate-500">
                P = Present, A = Absent, L = Leave, Lt = Late. Percentage = (Present + Late) ÷ days taken, not counting Leave days.
              </p>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
