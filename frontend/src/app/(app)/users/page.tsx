"use client";

import { useCallback, useEffect, useState } from "react";

import { Button, Card, ErrorBox, Field, SelectField } from "@/components/ui";
import { api, type Role, type User } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { ROLE_LABELS } from "@/lib/navigation";

type ManagedUser = User & { is_active: boolean };

const ROLE_OPTIONS: [string, string][] = (["teacher", "student", "parent", "admin"] as Role[]).map((r) => [
  r,
  ROLE_LABELS[r],
]);

const EMPTY_FORM = { username: "", email: "", first_name: "", last_name: "", phone: "", role: "teacher", password: "" };

export default function UsersPage() {
  const { user: me } = useAuth();
  const [users, setUsers] = useState<ManagedUser[]>([]);
  const [roleFilter, setRoleFilter] = useState("");
  const [form, setForm] = useState(EMPTY_FORM);
  const [error, setError] = useState<unknown>(null);
  const [saving, setSaving] = useState(false);

  const load = useCallback(() => {
    const query = roleFilter ? `?role=${roleFilter}` : "";
    api<{ results: ManagedUser[] }>(`/api/users/${query}`)
      .then((data) => setUsers(data.results))
      .catch(setError);
  }, [roleFilter]);

  useEffect(load, [load]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await api("/api/users/", { method: "POST", body: JSON.stringify(form) });
      setForm(EMPTY_FORM);
      load();
    } catch (err) {
      setError(err);
    } finally {
      setSaving(false);
    }
  }

  async function deactivate(user: ManagedUser) {
    if (!confirm(`Deactivate ${user.username}?`)) return;
    try {
      await api(`/api/users/${user.id}/`, { method: "DELETE" });
      load();
    } catch (err) {
      setError(err);
    }
  }

  const set = (key: keyof typeof EMPTY_FORM) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setForm({ ...form, [key]: e.target.value });

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Users</h1>

      <Card>
        <form onSubmit={onSubmit} className="space-y-4">
          <h2 className="font-medium">Add user</h2>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Username" value={form.username} onChange={set("username")} required />
            <SelectField label="Role" options={ROLE_OPTIONS} value={form.role} onChange={set("role")} />
            <Field label="First name" value={form.first_name} onChange={set("first_name")} />
            <Field label="Last name" value={form.last_name} onChange={set("last_name")} />
            <Field label="Email (optional)" type="email" value={form.email} onChange={set("email")} />
            <Field label="Phone (optional)" value={form.phone} onChange={set("phone")} />
            <Field label="Password" type="password" value={form.password} onChange={set("password")} required />
          </div>
          <ErrorBox error={error} />
          <Button type="submit" disabled={saving}>
            {saving ? "Saving…" : "Add user"}
          </Button>
        </form>
      </Card>

      <Card>
        <div className="mb-4 flex items-center justify-between gap-4">
          <h2 className="font-medium">All users</h2>
          <select
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
            className="rounded-lg border border-slate-300 bg-transparent px-2 py-1 text-sm dark:border-slate-700 dark:bg-slate-900"
          >
            <option value="">All roles</option>
            {ROLE_OPTIONS.map(([value, text]) => (
              <option key={value} value={value}>
                {text}
              </option>
            ))}
          </select>
        </div>
        <ul className="divide-y divide-slate-200 dark:divide-slate-800">
          {users.map((u) => (
            <li key={u.id} className="flex items-center justify-between gap-3 py-3">
              <div className="min-w-0">
                <p className="truncate font-medium">
                  {[u.first_name, u.last_name].filter(Boolean).join(" ") || u.username}
                  {!u.is_active && <span className="ml-2 text-xs text-red-600">inactive</span>}
                </p>
                <p className="truncate text-xs text-slate-500">
                  {ROLE_LABELS[u.role]} · {u.username}
                  {u.email && ` · ${u.email}`}
                </p>
              </div>
              {u.is_active && u.id !== me?.id && (
                <button onClick={() => deactivate(u)} className="shrink-0 text-sm text-red-600 hover:underline">
                  Deactivate
                </button>
              )}
            </li>
          ))}
          {users.length === 0 && <li className="py-3 text-sm text-slate-500">No users yet.</li>}
        </ul>
      </Card>
    </div>
  );
}
