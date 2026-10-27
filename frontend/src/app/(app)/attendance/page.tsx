"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { AttendanceTabs } from "@/components/attendance/AttendanceTabs";
import { useMySections } from "@/components/attendance/useMySections";
import { Button, Card, ErrorBox, Field } from "@/components/ui";
import { api } from "@/lib/api";
import {
  localToday,
  percentText,
  sectionText,
  STATUS_OPTIONS,
  type AttendanceStatus,
  type SectionInfo,
  type Summary,
} from "@/lib/attendance";
import { useAuth } from "@/lib/auth";
import { termsFor } from "@/lib/terms";

interface SheetRow {
  student: number;
  admission_no: string;
  full_name: string;
  roll_number: string;
  status: AttendanceStatus | null;
  remark: string;
}

interface Sheet {
  section: SectionInfo;
  date: string;
  marked: boolean;
  students: SheetRow[];
  summary: Summary;
}

export default function AttendancePage() {
  const { user } = useAuth();
  const terms = termsFor(user?.tenant);
  const { sections, error: sectionsError, reload: reloadSections } = useMySections();
  const [sectionId, setSectionId] = useState("");
  const [date, setDate] = useState(localToday());
  const [sheet, setSheet] = useState<Sheet | null>(null);
  const [marks, setMarks] = useState<Record<number, AttendanceStatus | null>>({});
  const [error, setError] = useState<unknown>(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  // Default to the first section not yet marked today.
  useEffect(() => {
    if (!sectionId && sections?.length) {
      setSectionId(String((sections.find((s) => !s.marked_today) ?? sections[0]).id));
    }
  }, [sections, sectionId]);

  const load = useCallback(async () => {
    if (!sectionId || !date) return;
    setError(null);
    setMessage("");
    try {
      const data = await api<Sheet>(`/api/attendance/sheet/?section=${sectionId}&date=${date}`);
      setSheet(data);
      setMarks(Object.fromEntries(data.students.map((s) => [s.student, s.status])));
    } catch (err) {
      setSheet(null);
      setError(err);
    }
  }, [sectionId, date]);

  useEffect(() => {
    load();
  }, [load]);

  const counts = useMemo(() => {
    const c: Record<string, number> = { present: 0, absent: 0, leave: 0, late: 0, unmarked: 0 };
    for (const s of sheet?.students ?? []) c[marks[s.student] ?? "unmarked"] += 1;
    return c;
  }, [sheet, marks]);

  const changed = sheet?.students.some((s) => marks[s.student] !== s.status) ?? false;

  async function save() {
    if (!sheet) return;
    const records = sheet.students
      .filter((s) => marks[s.student])
      .map((s) => ({ student: s.student, status: marks[s.student], remark: s.remark }));
    if (records.length === 0) return;
    setBusy(true);
    setError(null);
    try {
      const data = await api<Sheet>("/api/attendance/sheet/", {
        method: "POST",
        body: JSON.stringify({ section: Number(sectionId), date, records }),
      });
      setSheet(data);
      setMarks(Object.fromEntries(data.students.map((s) => [s.student, s.status])));
      setMessage(`Attendance saved: ${percentText(data.summary)} present.`);
      reloadSections();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  if (sections === null) return null;

  return (
    <div className="space-y-4 pb-24">
      <h1 className="text-2xl font-semibold">Attendance</h1>
      <AttendanceTabs />
      <ErrorBox error={sectionsError} />

      {sections.length === 0 ? (
        <Card>
          <p className="text-sm text-slate-500">
            {user?.role === "admin" ? (
              <>
                No {terms.sections.toLowerCase()} in the current session.{" "}
                <Link href="/academics/?tab=sections" className="text-indigo-600 hover:underline">
                  Set them up in Academic setup
                </Link>
                .
              </>
            ) : (
              `You are not the class teacher of any ${terms.section.toLowerCase()} yet. Ask your admin to assign you.`
            )}
          </p>
        </Card>
      ) : (
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
                    {sectionText(s, terms.section)} {s.marked_today ? "✓" : ""}
                  </option>
                ))}
              </select>
            </label>
            <Field label="Date" type="date" value={date} max={localToday()} onChange={(e) => setDate(e.target.value)} />
          </div>
          <p className="mt-2 text-xs text-slate-500">✓ = attendance already taken today</p>
        </Card>
      )}

      <ErrorBox error={error} />

      {sheet && (
        <>
          {sheet.students.length === 0 ? (
            <Card>
              <p className="text-sm text-slate-500">No active students in this {terms.section.toLowerCase()} yet.</p>
            </Card>
          ) : (
            <Card>
              <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                <div className="flex flex-wrap gap-3 text-sm">
                  {STATUS_OPTIONS.map((o) => (
                    <span key={o.value} className="flex items-center gap-1">
                      <span className={`h-2.5 w-2.5 rounded-full ${o.dot}`} />
                      {o.label}: <span className="font-semibold">{counts[o.value]}</span>
                    </span>
                  ))}
                  {counts.unmarked > 0 && <span className="text-slate-500">Not marked: {counts.unmarked}</span>}
                </div>
                <button
                  type="button"
                  onClick={() =>
                    setMarks(Object.fromEntries(sheet.students.map((s) => [s.student, marks[s.student] ?? "present"])))
                  }
                  className="rounded-lg border border-emerald-600 px-3 py-1.5 text-sm text-emerald-700 dark:text-emerald-400"
                >
                  Mark rest present
                </button>
              </div>
              {sheet.marked && !changed && (
                <p className="mb-3 rounded-lg bg-slate-50 px-3 py-2 text-xs text-slate-500 dark:bg-slate-800">
                  Attendance for this date was already taken. You can change it and save again.
                </p>
              )}
              <ul className="divide-y divide-slate-200 dark:divide-slate-800">
                {sheet.students.map((s) => (
                  <li key={s.student} className="py-3">
                    <p className="mb-2 text-sm">
                      {s.roll_number && <span className="mr-2 text-slate-500">{s.roll_number}.</span>}
                      <span className="font-medium">{s.full_name}</span>
                    </p>
                    <div className="grid grid-cols-4 gap-2" role="radiogroup" aria-label={`Attendance for ${s.full_name}`}>
                      {STATUS_OPTIONS.map((o) => {
                        const on = marks[s.student] === o.value;
                        return (
                          <button
                            key={o.value}
                            type="button"
                            role="radio"
                            aria-checked={on}
                            aria-label={`${o.label} ${s.full_name}`}
                            onClick={() => setMarks({ ...marks, [s.student]: o.value })}
                            className={`rounded-lg border py-2 text-sm font-medium ${
                              on ? o.on : "border-slate-300 text-slate-600 dark:border-slate-700 dark:text-slate-300"
                            }`}
                          >
                            {o.label}
                          </button>
                        );
                      })}
                    </div>
                  </li>
                ))}
              </ul>
            </Card>
          )}
          {message && <p className="rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{message}</p>}
        </>
      )}

      {sheet && sheet.students.length > 0 && (
        <div className="fixed inset-x-0 bottom-0 border-t border-slate-200 bg-white/95 px-4 py-3 backdrop-blur md:left-60 dark:border-slate-800 dark:bg-slate-900/95">
          <div className="flex items-center justify-between gap-3">
            <span className="text-sm text-slate-500">
              {changed ? "Unsaved changes" : sheet.marked ? "Saved" : "Not saved yet"}
            </span>
            <Button onClick={save} disabled={busy || counts.unmarked === sheet.students.length || !changed}>
              {busy ? "Saving…" : "Save attendance"}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
