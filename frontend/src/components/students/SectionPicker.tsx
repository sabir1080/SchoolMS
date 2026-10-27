"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import type { AcademicSession, Program, Section } from "@/components/academics/types";
import { useList } from "@/components/academics/useList";
import { ErrorBox, Field, SelectField } from "@/components/ui";
import { api } from "@/lib/api";
import type { Terms } from "@/lib/terms";

export interface SectionChoice {
  section: string;
  roll_number: string;
}

/** Pick a program, then one of its sections in a session (the current one by default), plus a roll number.
 *
 * Every active program is offered. If the chosen one has no section in the session yet, the admin can
 * create "A" right here instead of leaving the form.
 */
export function SectionPicker({
  terms,
  value,
  onChange,
  allowSessionChoice = false,
}: {
  terms: Terms;
  value: SectionChoice;
  onChange: (value: SectionChoice) => void;
  allowSessionChoice?: boolean;
}) {
  const sessions = useList<AcademicSession>("/api/academics/sessions/");
  const programs = useList<Program>("/api/academics/programs/");
  const [sessionId, setSessionId] = useState("");
  const sections = useList<Section>(sessionId ? `/api/academics/sections/?session=${sessionId}` : null);
  const [program, setProgram] = useState("");
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<unknown>(null);

  useEffect(() => {
    if (!sessionId && sessions.items.length) {
      setSessionId(String((sessions.items.find((s) => s.is_current) ?? sessions.items[0]).id));
    }
  }, [sessions.items, sessionId]);

  const activeSections = useMemo(() => sections.items.filter((s) => s.is_active), [sections.items]);
  const activePrograms = programs.items.filter((p) => p.is_active);
  const sectionOptions = activeSections.filter((s) => String(s.program) === program);
  const onlySection = sectionOptions.length === 1 ? String(sectionOptions[0].id) : "";

  // A program with a single section: pick it, also when sections finish loading after the choice.
  useEffect(() => {
    if (onlySection && !value.section) onChange({ ...value, section: onlySection });
  }, [onlySection, value, onChange]);

  if (sessions.loaded && sessions.items.length === 0) {
    return (
      <p className="text-sm text-slate-500">
        No academic session yet.{" "}
        <Link href="/academics/?tab=sessions" className="text-indigo-600 hover:underline">
          Add one in Academic setup
        </Link>{" "}
        (you can assign the {terms.program.toLowerCase()} later).
      </p>
    );
  }
  if (programs.loaded && activePrograms.length === 0) {
    return (
      <p className="text-sm text-slate-500">
        No {terms.programs.toLowerCase()} yet.{" "}
        <Link href="/academics/?tab=programs" className="text-indigo-600 hover:underline">
          Add them in Academic setup
        </Link>{" "}
        (you can assign the {terms.program.toLowerCase()} later).
      </p>
    );
  }

  async function createFirstSection() {
    setCreating(true);
    setCreateError(null);
    try {
      const created = await api<Section>("/api/academics/sections/", {
        method: "POST",
        body: JSON.stringify({ program: Number(program), session: Number(sessionId), name: "A" }),
      });
      await sections.reload();
      onChange({ ...value, section: String(created.id) });
    } catch (err) {
      setCreateError(err);
    } finally {
      setCreating(false);
    }
  }

  const programName = activePrograms.find((p) => String(p.id) === program)?.name;

  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {allowSessionChoice && (
        <SelectField
          label="Session"
          options={sessions.items.map((s) => [String(s.id), s.is_current ? `${s.name} (current)` : s.name])}
          value={sessionId}
          onChange={(e) => {
            setSessionId(e.target.value);
            setProgram("");
            onChange({ ...value, section: "" });
          }}
        />
      )}
      <SelectField
        label={terms.program}
        options={[["", `— Choose ${terms.program.toLowerCase()} —`], ...activePrograms.map((p): [string, string] => [String(p.id), p.name])]}
        value={program}
        onChange={(e) => {
          setProgram(e.target.value);
          setCreateError(null);
          onChange({ ...value, section: "" });
        }}
      />
      {program && sectionOptions.length > 0 && (
        <SelectField
          label={terms.section}
          options={[["", `— Choose ${terms.section.toLowerCase()} —`], ...sectionOptions.map((s): [string, string] => [String(s.id), s.name])]}
          value={value.section}
          onChange={(e) => onChange({ ...value, section: e.target.value })}
        />
      )}
      {program && sections.loaded && sectionOptions.length === 0 && (
        <div className="space-y-2 rounded-xl bg-amber-50 p-3 text-sm text-amber-900 sm:col-span-2 dark:bg-amber-950 dark:text-amber-200">
          <p>
            {programName} has no {terms.section.toLowerCase()} in this session yet.
          </p>
          <button
            type="button"
            onClick={createFirstSection}
            disabled={creating}
            className="rounded-lg bg-amber-600 px-3 py-2 font-medium text-white disabled:opacity-60"
          >
            {creating ? "Creating…" : `Create ${terms.section} A and use it`}
          </button>
          <ErrorBox error={createError} />
        </div>
      )}
      {value.section && (
        <Field
          label="Roll number (optional)"
          value={value.roll_number}
          onChange={(e) => onChange({ ...value, roll_number: e.target.value })}
        />
      )}
    </div>
  );
}
