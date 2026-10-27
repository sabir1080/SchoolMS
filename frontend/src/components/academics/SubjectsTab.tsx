"use client";

import { useState } from "react";

import { Button, Card, ErrorBox, Field } from "@/components/ui";
import { api } from "@/lib/api";
import { SUBJECT_EXAMPLES } from "@/lib/terms";

import { BulkAdd } from "./BulkAdd";
import { Badge, RowActions } from "./RowActions";
import type { Subject } from "./types";
import { useList } from "./useList";

const URL = "/api/academics/subjects/";

export function SubjectsTab() {
  const { items, loaded, error, reload } = useList<Subject>(URL);
  const [editing, setEditing] = useState<number | null>(null);
  const [actionError, setActionError] = useState<unknown>(null);

  return (
    <div className="space-y-4">
      <Card>
        <h2 className="mb-4 font-medium">Add subjects</h2>
        <BulkAdd url={`${URL}bulk-create/`} label="Subject names" example={SUBJECT_EXAMPLES} onAdded={reload} />
      </Card>

      <ErrorBox error={error || actionError} />
      <Card>
        <h2 className="mb-2 font-medium">Subjects ({items.length})</h2>
        {loaded && items.length === 0 && <p className="text-sm text-slate-500">No subjects yet.</p>}
        <ul className="divide-y divide-slate-200 dark:divide-slate-800">
          {items.map((s) => (
            <li key={s.id} className="py-3">
              <div className="flex items-center justify-between gap-2">
                <p className="min-w-0 truncate font-medium">
                  {s.name}
                  {s.code && <span className="ml-2 text-xs text-slate-500">{s.code}</span>}
                  {!s.is_active && <Badge tone="red">Inactive</Badge>}
                </p>
                <RowActions
                  editing={editing === s.id}
                  onEdit={() => setEditing(editing === s.id ? null : s.id)}
                  deleteUrl={`${URL}${s.id}/`}
                  name={s.name}
                  onDeleted={reload}
                  onError={setActionError}
                />
              </div>
              {editing === s.id && (
                <SubjectEdit
                  subject={s}
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

function SubjectEdit({ subject, onSaved }: { subject: Subject; onSaved: () => void }) {
  const [form, setForm] = useState({ name: subject.name, code: subject.code, is_active: subject.is_active });
  const [error, setError] = useState<unknown>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    try {
      await api(`${URL}${subject.id}/`, { method: "PATCH", body: JSON.stringify(form) });
      onSaved();
    } catch (err) {
      setError(err);
    }
  }

  return (
    <form onSubmit={onSubmit} className="mt-3 space-y-3">
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Subject name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
        <Field label="Code (optional)" value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} />
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
