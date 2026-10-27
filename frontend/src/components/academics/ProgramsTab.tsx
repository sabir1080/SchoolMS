"use client";

import { useState } from "react";

import { Button, Card, ErrorBox, Field, SelectField } from "@/components/ui";
import { api } from "@/lib/api";
import { PROGRAM_EXAMPLES, type Terms } from "@/lib/terms";

import { BulkAdd } from "./BulkAdd";
import { Badge, RowActions } from "./RowActions";
import type { Program, Subject } from "./types";
import { useList } from "./useList";

const URL = "/api/academics/programs/";

/** Save a new display order (every program id, top to bottom). */
async function saveOrder(ids: number[]) {
  await api(`${URL}reorder/`, { method: "POST", body: JSON.stringify({ ids }) });
}

export function ProgramsTab({ terms, instituteType }: { terms: Terms; instituteType: string }) {
  const { items, loaded, error, reload } = useList<Program>(URL);
  const subjects = useList<Subject>("/api/academics/subjects/");
  const [editing, setEditing] = useState<number | null>(null);
  const [actionError, setActionError] = useState<unknown>(null);

  const subjectName = (id: number) => subjects.items.find((s) => s.id === id)?.name;

  async function move(index: number, delta: number) {
    const ids = items.map((p) => p.id);
    const target = index + delta;
    if (target < 0 || target >= ids.length) return;
    [ids[index], ids[target]] = [ids[target], ids[index]];
    try {
      await saveOrder(ids);
      reload();
    } catch (err) {
      setActionError(err);
    }
  }

  return (
    <div className="space-y-4">
      <Card>
        <h2 className="mb-4 font-medium">Add {terms.programs.toLowerCase()}</h2>
        <BulkAdd
          url={`${URL}bulk-create/`}
          label={`${terms.program} names`}
          example={PROGRAM_EXAMPLES[instituteType] ?? PROGRAM_EXAMPLES.school}
          onAdded={reload}
        />
      </Card>

      <ErrorBox error={error || actionError} />
      <Card>
        <h2 className="mb-2 font-medium">
          {terms.programs} ({items.length})
        </h2>
        {loaded && items.length === 0 && <p className="text-sm text-slate-500">Nothing added yet.</p>}
        <ul className="divide-y divide-slate-200 dark:divide-slate-800">
          {items.map((p, index) => (
            <li key={p.id} className="py-3">
              <div className="flex items-center justify-between gap-2">
                <div className="flex shrink-0 flex-col">
                  <button
                    onClick={() => move(index, -1)}
                    disabled={index === 0}
                    aria-label={`Move ${p.name} up`}
                    className="rounded px-2 text-slate-500 hover:bg-slate-100 disabled:opacity-25 dark:hover:bg-slate-800"
                  >
                    ▲
                  </button>
                  <button
                    onClick={() => move(index, 1)}
                    disabled={index === items.length - 1}
                    aria-label={`Move ${p.name} down`}
                    className="rounded px-2 text-slate-500 hover:bg-slate-100 disabled:opacity-25 dark:hover:bg-slate-800"
                  >
                    ▼
                  </button>
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium">
                    {p.name}
                    {!p.is_active && <Badge tone="red">Inactive</Badge>}
                  </p>
                  <p className="truncate text-xs text-slate-500">
                    {p.section_count} {(p.section_count === 1 ? terms.section : terms.sections).toLowerCase()}
                    {p.subjects.length > 0 && ` · ${p.subjects.map(subjectName).filter(Boolean).join(", ")}`}
                  </p>
                </div>
                <RowActions
                  editing={editing === p.id}
                  onEdit={() => setEditing(editing === p.id ? null : p.id)}
                  deleteUrl={`${URL}${p.id}/`}
                  name={p.name}
                  onDeleted={reload}
                  onError={setActionError}
                />
              </div>
              {editing === p.id && (
                <ProgramEdit
                  program={p}
                  programs={items}
                  subjects={subjects.items}
                  terms={terms}
                  onSaved={() => {
                    setEditing(null);
                    reload();
                  }}
                />
              )}
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}

function ProgramEdit({
  program,
  programs,
  subjects,
  terms,
  onSaved,
}: {
  program: Program;
  programs: Program[];
  subjects: Subject[];
  terms: Terms;
  onSaved: () => void;
}) {
  const others = programs.filter((p) => p.id !== program.id);
  const index = programs.findIndex((p) => p.id === program.id);
  // "" means "at the top"; otherwise the id of the program this one is shown after.
  const currentAfter = index > 0 ? String(programs[index - 1].id) : "";
  const [after, setAfter] = useState(currentAfter);
  const [form, setForm] = useState({
    name: program.name,
    code: program.code,
    is_active: program.is_active,
    subjects: program.subjects,
  });
  const [error, setError] = useState<unknown>(null);

  function toggleSubject(id: number) {
    setForm((f) => ({
      ...f,
      subjects: f.subjects.includes(id) ? f.subjects.filter((s) => s !== id) : [...f.subjects, id],
    }));
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    try {
      await api(`${URL}${program.id}/`, { method: "PATCH", body: JSON.stringify(form) });
      if (after !== currentAfter) {
        const ids = others.map((p) => p.id);
        const position = after === "" ? 0 : ids.indexOf(Number(after)) + 1;
        ids.splice(position, 0, program.id);
        await saveOrder(ids);
      }
      onSaved();
    } catch (err) {
      setError(err);
    }
  }

  return (
    <form onSubmit={onSubmit} className="mt-3 space-y-3">
      <div className="grid gap-3 sm:grid-cols-3">
        <Field label={`${terms.program} name`} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
        <Field label="Code (optional)" value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} />
        <SelectField
          label="Show after"
          options={[["", "— At the top —"], ...others.map((p): [string, string] => [String(p.id), p.name])]}
          value={after}
          onChange={(e) => setAfter(e.target.value)}
        />
      </div>
      <div>
        <p className="mb-2 text-sm font-medium">Subjects</p>
        {subjects.length === 0 ? (
          <p className="text-xs text-slate-500">Add subjects in the Subjects tab first.</p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {subjects.map((s) => (
              <label
                key={s.id}
                className={`flex cursor-pointer items-center gap-2 rounded-full border px-3 py-1 text-sm ${
                  form.subjects.includes(s.id)
                    ? "border-indigo-500 bg-indigo-50 dark:bg-indigo-950"
                    : "border-slate-300 dark:border-slate-700"
                }`}
              >
                <input type="checkbox" checked={form.subjects.includes(s.id)} onChange={() => toggleSubject(s.id)} />
                {s.name}
              </label>
            ))}
          </div>
        )}
      </div>
      <label className="flex items-center gap-2 text-sm">
        <input type="checkbox" checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} />
        Active
      </label>
      <ErrorBox error={error} />
      <Button type="submit">Save</Button>
    </form>
  );
}
