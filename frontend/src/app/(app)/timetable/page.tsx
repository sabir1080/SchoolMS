"use client";

import { useCallback, useEffect, useState } from "react";

import type { AcademicSession, Section, Subject } from "@/components/academics/types";
import { useList } from "@/components/academics/useList";
import { TimetableGrid } from "@/components/timetable/TimetableGrid";
import { Button, Card, ErrorBox, Field, SelectField } from "@/components/ui";
import { api, type User } from "@/lib/api";

type StaffUser = User & { is_active: boolean };
import { useAuth } from "@/lib/auth";
import { DAY_SHORT, type Entry, type Period, type Timetable } from "@/lib/timetable";
import { termsFor } from "@/lib/terms";
import { useLatestRequest } from "@/lib/useLatestRequest";

type Tab = "class" | "teacher" | "periods";

export default function TimetablePage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const [tab, setTab] = useState<Tab>(isAdmin ? "class" : "teacher");
  const terms = termsFor(user?.tenant);
  const tabs: [Tab, string][] = [
    ["class", `${terms.program} timetable`],
    ["teacher", isAdmin ? "Teacher timetable" : "My timetable"],
    ...(isAdmin ? ([["periods", "Periods & days"]] as [Tab, string][]) : []),
  ];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold">Timetable</h1>
        <button onClick={() => window.print()} className="text-sm text-brand-600 hover:underline print:hidden">
          Print
        </button>
      </div>
      <div className="flex w-max max-w-full gap-1 overflow-x-auto rounded-xl bg-slate-200/60 p-1 print:hidden dark:bg-slate-800" role="tablist">
        {tabs.map(([key, label]) => (
          <button
            key={key}
            role="tab"
            aria-selected={tab === key}
            onClick={() => setTab(key)}
            className={`rounded-lg px-3 py-2 text-sm whitespace-nowrap ${tab === key ? "bg-white font-medium shadow-sm dark:bg-slate-900" : "text-slate-600 dark:text-slate-300"}`}
          >
            {label}
          </button>
        ))}
      </div>
      {tab === "class" && <ClassTimetable editable={isAdmin} />}
      {tab === "teacher" && <TeacherTimetable isAdmin={isAdmin} />}
      {tab === "periods" && <PeriodsSetup />}
    </div>
  );
}

function useCurrentSections() {
  const sessions = useList<AcademicSession>("/api/academics/sessions/");
  const current = sessions.items.find((s) => s.is_current);
  const sections = useList<Section>(current ? `/api/academics/sections/?session=${current.id}` : null);
  return { sections: sections.items.filter((s) => s.is_active), loaded: sessions.loaded && (!current || sections.loaded) };
}

function ClassTimetable({ editable }: { editable: boolean }) {
  const { user } = useAuth();
  const terms = termsFor(user?.tenant);
  const { sections, loaded } = useCurrentSections();
  const [sectionId, setSectionId] = useState("");
  const [data, setData] = useState<Timetable | null>(null);
  const [editing, setEditing] = useState<{ day: number; period: number; entry?: Entry } | null>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    if (!sectionId && sections.length) setSectionId(String(sections[0].id));
  }, [sections, sectionId]);

  const latest = useLatestRequest();
  const load = useCallback(() => {
    if (sectionId) latest(api<Timetable>(`/api/timetable/entries/?section=${sectionId}`), setData, setError);
  }, [sectionId, latest]);
  useEffect(() => load(), [load]);

  if (loaded && !sections.length) {
    return (
      <Card>
        <p className="text-sm text-slate-500">No {terms.sections.toLowerCase()} in the current session yet. Add them in Academic setup.</p>
      </Card>
    );
  }
  const section = sections.find((s) => String(s.id) === sectionId);

  return (
    <div className="space-y-3">
      <div className="max-w-xs print:hidden">
        <SelectField
          label={terms.section}
          value={sectionId}
          onChange={(e) => {
            setSectionId(e.target.value);
            setEditing(null);
            setData(null); // never show (or edit) the previous section's timetable while the new one loads
          }}
          options={sections.map((s) => [String(s.id), `${s.program_name} - ${s.name}`])}
        />
      </div>
      <ErrorBox error={error} />
      {data && section && data.entries.every((e) => e.section === section.id) && (
        <Card>
          <h2 className="mb-3 font-medium">
            {section.program_name} - {section.name}
            {section.class_teacher_name && <span className="text-sm font-normal text-slate-500"> · Class teacher {section.class_teacher_name}</span>}
          </h2>
          <TimetableGrid data={data} show="teacher" onCell={editable ? (day, period, entry) => setEditing({ day, period, entry }) : undefined} />
          {editable && <p className="mt-2 text-xs text-slate-500 print:hidden">Tap a period to set its subject and teacher.</p>}
        </Card>
      )}
      {editing && data && section && (
        <CellEditor
          key={`${editing.day}-${editing.period}`}
          section={section}
          data={data}
          slot={editing}
          onDone={() => {
            setEditing(null);
            load();
          }}
        />
      )}
    </div>
  );
}

function CellEditor({
  section,
  data,
  slot,
  onDone,
}: {
  section: Section;
  data: Timetable;
  slot: { day: number; period: number; entry?: Entry };
  onDone: () => void;
}) {
  const subjects = useList<Subject>("/api/academics/subjects/");
  const teachers = useList<StaffUser>("/api/users/?role=teacher&page_size=500");
  const [form, setForm] = useState({
    subject: slot.entry?.subject ? String(slot.entry.subject) : "",
    teacher: slot.entry?.teacher ? String(slot.entry.teacher) : "",
    room: slot.entry?.room ?? "",
  });
  const [error, setError] = useState<unknown>(null);
  const period = data.periods.find((p) => p.id === slot.period);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    const body = JSON.stringify({
      section: section.id,
      day: slot.day,
      period: slot.period,
      subject: form.subject ? Number(form.subject) : null,
      teacher: form.teacher ? Number(form.teacher) : null,
      room: form.room,
    });
    try {
      await api(slot.entry ? `/api/timetable/entries/${slot.entry.id}/` : "/api/timetable/entries/", {
        method: slot.entry ? "PATCH" : "POST",
        body,
      });
      onDone();
    } catch (err) {
      setError(err);
    }
  }

  async function clear() {
    try {
      await api(`/api/timetable/entries/${slot.entry!.id}/`, { method: "DELETE" });
      onDone();
    } catch (err) {
      setError(err);
    }
  }

  return (
    <Card>
      <form onSubmit={save} className="space-y-3 print:hidden">
        <h3 className="font-medium">
          {DAY_SHORT[slot.day]} · {period?.name} · {section.program_name} - {section.name}
        </h3>
        <div className="grid gap-3 sm:grid-cols-3">
          <SelectField
            label="Subject"
            value={form.subject}
            onChange={(e) => setForm({ ...form, subject: e.target.value })}
            options={[["", "Choose…"], ...subjects.items.filter((s) => s.is_active).map((s) => [String(s.id), s.name] as [string, string])]}
            required
          />
          <SelectField
            label="Teacher"
            value={form.teacher}
            onChange={(e) => setForm({ ...form, teacher: e.target.value })}
            options={[["", "No teacher"], ...teachers.items.filter((t) => t.is_active).map((t) => [String(t.id), `${t.first_name} ${t.last_name}`.trim() || t.username] as [string, string])]}
          />
          <Field label="Room (optional)" value={form.room} onChange={(e) => setForm({ ...form, room: e.target.value })} />
        </div>
        <ErrorBox error={error} />
        <div className="flex items-center gap-3">
          <Button type="submit">Save</Button>
          {slot.entry && (
            <button type="button" onClick={clear} className="text-sm text-red-600 hover:underline">
              Clear period
            </button>
          )}
          <button type="button" onClick={onDone} className="text-sm text-slate-600 hover:underline dark:text-slate-300">
            Cancel
          </button>
        </div>
      </form>
    </Card>
  );
}

function TeacherTimetable({ isAdmin }: { isAdmin: boolean }) {
  const teachers = useList<StaffUser>(isAdmin ? "/api/users/?role=teacher&page_size=500" : null);
  const [chosen, setTeacherId] = useState(isAdmin ? "" : "me");
  const [data, setData] = useState<Timetable | null>(null);
  const [error, setError] = useState<unknown>(null);
  const teacherId = chosen || (teachers.items[0] ? String(teachers.items[0].id) : "");
  const choose = (id: string) => {
    setData(null);
    setTeacherId(id);
  };

  const latest = useLatestRequest();
  useEffect(() => {
    if (teacherId) latest(api<Timetable>(`/api/timetable/entries/?teacher=${teacherId}`), setData, setError);
  }, [teacherId, latest]);

  const periods = data ? data.entries.length : 0;
  return (
    <div className="space-y-3">
      {isAdmin && (
        <div className="max-w-xs print:hidden">
          <SelectField
            label="Teacher"
            value={teacherId}
            onChange={(e) => choose(e.target.value)}
            options={teachers.items.map((t) => [String(t.id), `${t.first_name} ${t.last_name}`.trim() || t.username])}
          />
        </div>
      )}
      {isAdmin && teachers.loaded && !teachers.items.length && <p className="text-sm text-slate-500">No teachers yet. Add them under Users.</p>}
      <ErrorBox error={error} />
      {data && (
        <Card>
          <p className="mb-3 text-sm text-slate-500">
            {periods} {periods === 1 ? "period" : "periods"} a week
          </p>
          <TimetableGrid data={data} show="section" />
        </Card>
      )}
    </div>
  );
}

function PeriodsSetup() {
  const { user, refreshUser } = useAuth();
  const periods = useList<Period>("/api/timetable/periods/");
  const [error, setError] = useState<unknown>(null);
  const [message, setMessage] = useState("");
  const [quick, setQuick] = useState({ start: "08:00", periods: "7", minutes: "40", break_after: "4", break_minutes: "20" });
  const [days, setDays] = useState<number[]>((user?.tenant?.working_days ?? "0,1,2,3,4").split(",").map(Number));
  const [adding, setAdding] = useState({ name: "", start_time: "", end_time: "", is_break: false });

  async function run(action: () => Promise<unknown>, done: string) {
    setError(null);
    setMessage("");
    try {
      await action();
      setMessage(done);
      periods.reload();
    } catch (err) {
      setError(err);
    }
  }

  const generate = (e: React.FormEvent) => {
    e.preventDefault();
    run(() => api("/api/timetable/periods/generate/", { method: "POST", body: JSON.stringify(quick) }), "Periods created.");
  };
  const saveDays = () =>
    run(async () => {
      await api("/api/institute/settings/", { method: "PATCH", body: JSON.stringify({ working_days: days.join(",") }) });
      await refreshUser();
    }, "School days saved.");

  return (
    <div className="max-w-2xl space-y-4">
      <Card>
        <h2 className="mb-2 font-medium">School days</h2>
        <div className="flex flex-wrap gap-2">
          {DAY_SHORT.map((name, d) => (
            <label key={d} className={`flex cursor-pointer items-center gap-1.5 rounded-full border px-3 py-1 text-sm ${days.includes(d) ? "border-brand-500 bg-brand-50 dark:bg-brand-950" : "border-slate-300 dark:border-slate-700"}`}>
              <input type="checkbox" checked={days.includes(d)} onChange={() => setDays(days.includes(d) ? days.filter((x) => x !== d) : [...days, d].sort())} />
              {name}
            </label>
          ))}
        </div>
        <button onClick={saveDays} className="mt-3 text-sm font-medium text-brand-600 hover:underline">
          Save school days
        </button>
      </Card>

      {periods.loaded && periods.items.length === 0 && (
        <Card>
          <h2 className="mb-1 font-medium">Quick setup</h2>
          <p className="mb-3 text-sm text-slate-500">Make the whole school day in one go. You can change each period afterwards.</p>
          <form onSubmit={generate} className="grid grid-cols-2 gap-3 sm:grid-cols-5">
            <Field label="School starts" type="time" value={quick.start} onChange={(e) => setQuick({ ...quick, start: e.target.value })} required />
            <Field label="Periods" type="number" min="1" max="12" value={quick.periods} onChange={(e) => setQuick({ ...quick, periods: e.target.value })} required />
            <Field label="Minutes each" type="number" min="10" max="120" value={quick.minutes} onChange={(e) => setQuick({ ...quick, minutes: e.target.value })} required />
            <Field label="Break after period" type="number" min="0" max="12" value={quick.break_after} onChange={(e) => setQuick({ ...quick, break_after: e.target.value })} />
            <Field label="Break minutes" type="number" min="5" max="90" value={quick.break_minutes} onChange={(e) => setQuick({ ...quick, break_minutes: e.target.value })} />
            <div className="col-span-2 sm:col-span-5">
              <Button type="submit">Create periods</Button>
            </div>
          </form>
        </Card>
      )}

      {periods.items.length > 0 && (
        <Card>
          <h2 className="mb-3 font-medium">Periods</h2>
          <ul className="space-y-2">
            {periods.items.map((p) => (
              <PeriodRow key={p.id} period={p} onChanged={periods.reload} onError={setError} />
            ))}
          </ul>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              run(() => api("/api/timetable/periods/", { method: "POST", body: JSON.stringify(adding) }), "Period added.").then(() =>
                setAdding({ name: "", start_time: "", end_time: "", is_break: false }),
              );
            }}
            className="mt-4 grid grid-cols-2 items-end gap-2 border-t border-slate-200 pt-4 sm:grid-cols-5 dark:border-slate-800"
          >
            <Field label="New period" placeholder="e.g. Period 8" value={adding.name} onChange={(e) => setAdding({ ...adding, name: e.target.value })} required />
            <Field label="Starts" type="time" value={adding.start_time} onChange={(e) => setAdding({ ...adding, start_time: e.target.value })} required />
            <Field label="Ends" type="time" value={adding.end_time} onChange={(e) => setAdding({ ...adding, end_time: e.target.value })} required />
            <label className="flex items-center gap-2 pb-2 text-sm">
              <input type="checkbox" checked={adding.is_break} onChange={(e) => setAdding({ ...adding, is_break: e.target.checked })} />
              Break
            </label>
            <Button type="submit">Add</Button>
          </form>
        </Card>
      )}
      <ErrorBox error={error} />
      {message && <p className="text-sm text-emerald-700">{message}</p>}
    </div>
  );
}

function PeriodRow({ period, onChanged, onError }: { period: Period; onChanged: () => void; onError: (e: unknown) => void }) {
  const [form, setForm] = useState({ ...period, start_time: period.start_time.slice(0, 5), end_time: period.end_time.slice(0, 5) });
  const changed = form.name !== period.name || form.start_time !== period.start_time.slice(0, 5) || form.end_time !== period.end_time.slice(0, 5) || form.is_break !== period.is_break;

  async function save() {
    try {
      await api(`/api/timetable/periods/${period.id}/`, { method: "PATCH", body: JSON.stringify(form) });
      onChanged();
    } catch (err) {
      onError(err);
    }
  }
  async function remove() {
    if (!window.confirm(`Delete ${period.name}? Its timetable entries are removed too.`)) return;
    try {
      await api(`/api/timetable/periods/${period.id}/`, { method: "DELETE" });
      onChanged();
    } catch (err) {
      onError(err);
    }
  }
  const input = "w-full rounded-lg border border-slate-300 bg-transparent px-2 py-1.5 text-sm dark:border-slate-700";
  return (
    <li className="grid grid-cols-[1fr_5.5rem_5.5rem] items-center gap-2 sm:grid-cols-[1fr_6rem_6rem_auto_auto]">
      <input aria-label="Period name" className={input} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
      <input aria-label={`${period.name} starts`} type="time" className={input} value={form.start_time} onChange={(e) => setForm({ ...form, start_time: e.target.value })} />
      <input aria-label={`${period.name} ends`} type="time" className={input} value={form.end_time} onChange={(e) => setForm({ ...form, end_time: e.target.value })} />
      <label className="flex items-center gap-1 text-xs">
        <input type="checkbox" checked={form.is_break} onChange={(e) => setForm({ ...form, is_break: e.target.checked })} />
        Break
      </label>
      <span className="flex gap-3 text-xs">
        {changed && (
          <button onClick={save} className="font-medium text-brand-600">
            Save
          </button>
        )}
        <button onClick={remove} className="text-red-600">
          Delete
        </button>
      </span>
    </li>
  );
}
