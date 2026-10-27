"use client";

import { useEffect, useMemo, useState } from "react";

import { Button, Card, ErrorBox, Field, SelectField } from "@/components/ui";
import { api, type User } from "@/lib/api";
import type { Terms } from "@/lib/terms";

import { Badge, RowActions } from "./RowActions";
import type { AcademicSession, Program, Section } from "./types";
import { useList } from "./useList";

const URL = "/api/academics/sections/";

type Staff = User & { is_active: boolean };

function staffName(u: Staff) {
  return [u.first_name, u.last_name].filter(Boolean).join(" ") || u.username;
}

export function SectionsTab({ terms, goTo }: { terms: Terms; goTo: (tab: string) => void }) {
  const sessions = useList<AcademicSession>("/api/academics/sessions/");
  const programs = useList<Program>("/api/academics/programs/");
  const users = useList<Staff>("/api/users/");
  const [sessionId, setSessionId] = useState<number | null>(null);
  const sections = useList<Section>(sessionId ? `${URL}?session=${sessionId}` : null);
  const [editing, setEditing] = useState<number | null>(null);
  const [actionError, setActionError] = useState<unknown>(null);

  // Start on the current session.
  useEffect(() => {
    if (sessionId === null && sessions.items.length) {
      setSessionId((sessions.items.find((s) => s.is_current) ?? sessions.items[0]).id);
    }
  }, [sessions.items, sessionId]);

  const staff = useMemo(
    () => users.items.filter((u) => u.is_active && (u.role === "teacher" || u.role === "admin")),
    [users.items],
  );
  const activePrograms = programs.items.filter((p) => p.is_active);

  if (sessions.loaded && sessions.items.length === 0) {
    return <Missing text="Add an academic session first." action="Go to Sessions" onClick={() => goTo("sessions")} />;
  }
  if (programs.loaded && activePrograms.length === 0) {
    return (
      <Missing
        text={`Add ${terms.programs.toLowerCase()} first.`}
        action={`Go to ${terms.programs}`}
        onClick={() => goTo("programs")}
      />
    );
  }
  if (!sessionId) return null;

  // Programs that have sections in this session get their own card; the rest are listed once.
  const grouped = programs.items
    .map((p) => ({ program: p, items: sections.items.filter((s) => s.program === p.id) }))
    .filter((g) => g.items.length);
  const without = activePrograms.filter((p) => !sections.items.some((s) => s.program === p.id));

  return (
    <div className="space-y-4">
      <SelectField
        label="Session"
        options={sessions.items.map((s) => [String(s.id), s.is_current ? `${s.name} (current)` : s.name])}
        value={String(sessionId)}
        onChange={(e) => setSessionId(Number(e.target.value))}
      />

      <Card>
        <h2 className="mb-4 font-medium">Add {terms.section.toLowerCase()}</h2>
        <SectionForm
          terms={terms}
          programs={activePrograms}
          staff={staff}
          sessionId={sessionId}
          onSaved={sections.reload}
        />
      </Card>

      <ErrorBox error={sections.error || actionError} />
      {grouped.map(({ program, items }) => (
        <Card key={program.id}>
          <h2 className="font-medium">{program.name}</h2>
          <ul className="divide-y divide-slate-200 dark:divide-slate-800">
              {items.map((s) => (
                <li key={s.id} className="py-3">
                  <div className="flex items-center justify-between gap-2">
                    <div className="min-w-0">
                      <p className="truncate font-medium">
                        {terms.section} {s.name}
                        {!s.is_active && <Badge tone="red">Inactive</Badge>}
                      </p>
                      <p className="truncate text-xs text-slate-500">
                        {s.class_teacher_name ? `Teacher: ${s.class_teacher_name}` : "No teacher assigned"}
                        {s.capacity ? ` · Capacity ${s.capacity}` : ""}
                      </p>
                    </div>
                    <RowActions
                      editing={editing === s.id}
                      onEdit={() => setEditing(editing === s.id ? null : s.id)}
                      deleteUrl={`${URL}${s.id}/`}
                      name={`${program.name} ${s.name}`}
                      onDeleted={sections.reload}
                      onError={setActionError}
                    />
                  </div>
                  {editing === s.id && (
                    <div className="mt-3">
                      <SectionForm
                        terms={terms}
                        programs={activePrograms}
                        staff={staff}
                        sessionId={sessionId}
                        section={s}
                        onSaved={() => {
                          setEditing(null);
                          sections.reload();
                        }}
                      />
                    </div>
                  )}
                </li>
              ))}
          </ul>
        </Card>
      ))}
      {sections.loaded && without.length > 0 && (
        <Card>
          <h2 className="font-medium">
            {terms.programs} without {terms.sections.toLowerCase()} ({without.length})
          </h2>
          <p className="mt-1 text-sm text-slate-500">{without.map((p) => p.name).join(", ")}</p>
        </Card>
      )}
    </div>
  );
}

function SectionForm({
  terms,
  programs,
  staff,
  sessionId,
  section,
  onSaved,
}: {
  terms: Terms;
  programs: Program[];
  staff: Staff[];
  sessionId: number;
  section?: Section;
  onSaved: () => void;
}) {
  const empty = { program: String(programs[0]?.id ?? ""), name: "", capacity: "", class_teacher: "", is_active: true };
  const [form, setForm] = useState(() =>
    section
      ? {
          program: String(section.program),
          name: section.name,
          capacity: section.capacity ? String(section.capacity) : "",
          class_teacher: section.class_teacher ? String(section.class_teacher) : "",
          is_active: section.is_active,
        }
      : empty,
  );
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  const set = (key: "program" | "name" | "capacity" | "class_teacher") =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => setForm({ ...form, [key]: e.target.value });

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const body = {
      program: Number(form.program),
      session: sessionId,
      name: form.name,
      capacity: form.capacity ? Number(form.capacity) : null,
      class_teacher: form.class_teacher ? Number(form.class_teacher) : null,
      is_active: form.is_active,
    };
    try {
      await api(section ? `${URL}${section.id}/` : URL, {
        method: section ? "PATCH" : "POST",
        body: JSON.stringify(body),
      });
      if (!section) setForm({ ...empty, program: form.program, class_teacher: "" });
      onSaved();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="space-y-3">
      <div className="grid gap-3 sm:grid-cols-2">
        <SelectField
          label={terms.program}
          options={programs.map((p) => [String(p.id), p.name])}
          value={form.program}
          onChange={set("program")}
        />
        <Field label={`${terms.section} name`} value={form.name} onChange={set("name")} placeholder="e.g. A" required />
        <SelectField
          label="Class teacher (optional)"
          options={[["", "— None —"], ...staff.map((u): [string, string] => [String(u.id), staffName(u)])]}
          value={form.class_teacher}
          onChange={set("class_teacher")}
        />
        <Field label="Capacity (optional)" type="number" min="1" value={form.capacity} onChange={set("capacity")} />
      </div>
      {section && (
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} />
          Active
        </label>
      )}
      <ErrorBox error={error} />
      <Button type="submit" disabled={busy}>
        {busy ? "Saving…" : section ? "Save" : `Add ${terms.section.toLowerCase()}`}
      </Button>
    </form>
  );
}

function Missing({ text, action, onClick }: { text: string; action: string; onClick: () => void }) {
  return (
    <Card>
      <p className="text-sm text-slate-500">{text}</p>
      <Button className="mt-3" onClick={onClick}>
        {action}
      </Button>
    </Card>
  );
}
