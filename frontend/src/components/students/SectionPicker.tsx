"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import type { AcademicSession, Program, Section } from "@/components/academics/types";
import { useList } from "@/components/academics/useList";
import { Field, SelectField } from "@/components/ui";
import type { Terms } from "@/lib/terms";

export interface SectionChoice {
  section: string;
  roll_number: string;
}

/** Pick a program, then one of its sections in a session (the current one by default), plus a roll number. */
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

  useEffect(() => {
    if (!sessionId && sessions.items.length) {
      setSessionId(String((sessions.items.find((s) => s.is_current) ?? sessions.items[0]).id));
    }
  }, [sessions.items, sessionId]);

  const activeSections = useMemo(() => sections.items.filter((s) => s.is_active), [sections.items]);
  const programsWithSections = programs.items.filter((p) => activeSections.some((s) => s.program === p.id));
  const sectionOptions = activeSections.filter((s) => String(s.program) === program);

  if (sessions.loaded && programs.loaded && sections.loaded && programsWithSections.length === 0) {
    return (
      <p className="text-sm text-slate-500">
        No {terms.sections.toLowerCase()} in this session yet.{" "}
        <Link href="/academics/?tab=sections" className="text-indigo-600 hover:underline">
          Add them in Academic setup
        </Link>{" "}
        (you can assign the {terms.program.toLowerCase()} later).
      </p>
    );
  }

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
        options={[["", `— Choose ${terms.program.toLowerCase()} —`], ...programsWithSections.map((p): [string, string] => [String(p.id), p.name])]}
        value={program}
        onChange={(e) => {
          setProgram(e.target.value);
          const only = activeSections.filter((s) => String(s.program) === e.target.value);
          onChange({ ...value, section: only.length === 1 ? String(only[0].id) : "" });
        }}
      />
      {program && (
        <SelectField
          label={terms.section}
          options={[["", `— Choose ${terms.section.toLowerCase()} —`], ...sectionOptions.map((s): [string, string] => [String(s.id), s.name])]}
          value={value.section}
          onChange={(e) => onChange({ ...value, section: e.target.value })}
        />
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
