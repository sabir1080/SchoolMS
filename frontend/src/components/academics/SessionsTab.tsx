"use client";

import { useState } from "react";

import { Button, Card, ErrorBox, Field } from "@/components/ui";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/navigation";
import { suggestedSession } from "@/lib/terms";

import { Badge, RowActions } from "./RowActions";
import type { AcademicSession } from "./types";
import { useList } from "./useList";

const URL = "/api/academics/sessions/";

export function SessionsTab() {
  const { items, loaded, error, reload } = useList<AcademicSession>(URL);
  const [editing, setEditing] = useState<number | null>(null);
  const [actionError, setActionError] = useState<unknown>(null);

  async function makeCurrent(session: AcademicSession) {
    try {
      await api(`${URL}${session.id}/`, { method: "PATCH", body: JSON.stringify({ is_current: true }) });
      reload();
    } catch (err) {
      setActionError(err);
    }
  }

  return (
    <div className="space-y-4">
      <Card>
        <h2 className="mb-1 font-medium">Add session</h2>
        <p className="mb-4 text-sm text-slate-500">An academic year or term, e.g. 2026-27 or Spring 2027.</p>
        <SessionForm onSaved={reload} />
      </Card>

      <ErrorBox error={error || actionError} />
      <Card>
        <h2 className="mb-2 font-medium">Sessions</h2>
        {loaded && items.length === 0 && <p className="text-sm text-slate-500">No sessions yet. Add your first one above.</p>}
        <ul className="divide-y divide-slate-200 dark:divide-slate-800">
          {items.map((s) => (
            <li key={s.id} className="py-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <p className="font-medium">
                    {s.name}
                    {s.is_current && <Badge tone="green">Current</Badge>}
                  </p>
                  <p className="text-xs text-slate-500">
                    {formatDate(s.start_date)} – {formatDate(s.end_date)}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  {!s.is_current && (
                    <button onClick={() => makeCurrent(s)} className="text-sm text-emerald-700 hover:underline">
                      Make current
                    </button>
                  )}
                  <RowActions
                    editing={editing === s.id}
                    onEdit={() => setEditing(editing === s.id ? null : s.id)}
                    deleteUrl={`${URL}${s.id}/`}
                    name={s.name}
                    onDeleted={reload}
                    onError={setActionError}
                  />
                </div>
              </div>
              {editing === s.id && (
                <div className="mt-3">
                  <SessionForm
                    session={s}
                    onSaved={() => {
                      setEditing(null);
                      reload();
                    }}
                  />
                </div>
              )}
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}

function SessionForm({ session, onSaved }: { session?: AcademicSession; onSaved: () => void }) {
  const [form, setForm] = useState(() =>
    session
      ? { name: session.name, start_date: session.start_date, end_date: session.end_date }
      : suggestedSession(),
  );
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  const set = (key: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm({ ...form, [key]: e.target.value });

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api(session ? `${URL}${session.id}/` : URL, {
        method: session ? "PATCH" : "POST",
        body: JSON.stringify(form),
      });
      if (!session) setForm({ name: "", start_date: "", end_date: "" });
      onSaved();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="space-y-3">
      <div className="grid gap-3 sm:grid-cols-3">
        <Field label="Session name" value={form.name} onChange={set("name")} required />
        <Field label="Start date" type="date" value={form.start_date} onChange={set("start_date")} required />
        <Field label="End date" type="date" value={form.end_date} onChange={set("end_date")} required />
      </div>
      <ErrorBox error={error} />
      <Button type="submit" disabled={busy}>
        {busy ? "Saving…" : session ? "Save" : "Add session"}
      </Button>
    </form>
  );
}
