"use client";

import { useCallback, useEffect, useState } from "react";

import { Button, Card, ErrorBox, Field, SelectField } from "@/components/ui";
import { api, type Role, type User } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { ROLE_LABELS } from "@/lib/navigation";
import { policyHint } from "@/lib/passwords";

type ManagedUser = User & { is_active: boolean };

const ROLE_OPTIONS: [string, string][] = (["teacher", "student", "parent", "admin"] as Role[]).map((r) => [
  r,
  ROLE_LABELS[r],
]);

const EMPTY_FORM = { username: "", email: "", first_name: "", last_name: "", phone: "", role: "teacher", password: "" };

export default function UsersPage() {
  const { user: me, refreshSubscription } = useAuth();
  const [users, setUsers] = useState<ManagedUser[]>([]);
  const [roleFilter, setRoleFilter] = useState("");
  const [form, setForm] = useState(EMPTY_FORM);
  const [error, setError] = useState<unknown>(null);
  const [saving, setSaving] = useState(false);
  const [resetting, setResetting] = useState<number | null>(null);

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
      refreshSubscription();
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
      refreshSubscription();
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
            <div>
              <Field label="Password" type="password" value={form.password} onChange={set("password")} required />
              <p className="mt-1 text-xs text-slate-500">{policyHint(me?.tenant?.password_policy)}</p>
            </div>
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
            <li key={u.id} className="py-3">
              <div className="flex items-center justify-between gap-3">
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
                <div className="flex shrink-0 gap-3 text-sm">
                  {u.id !== me?.id && (
                    <button
                      onClick={() => setResetting(resetting === u.id ? null : u.id)}
                      className="text-indigo-600 hover:underline"
                    >
                      {resetting === u.id ? "Cancel" : "Reset password"}
                    </button>
                  )}
                  {u.is_active && u.id !== me?.id && (
                    <button onClick={() => deactivate(u)} className="text-red-600 hover:underline">
                      Deactivate
                    </button>
                  )}
                </div>
              </div>
              {resetting === u.id && (
                <ResetPassword
                  user={u}
                  hint={policyHint(me?.tenant?.password_policy)}
                  onDone={() => setResetting(null)}
                />
              )}
            </li>
          ))}
          {users.length === 0 && <li className="py-3 text-sm text-slate-500">No users yet.</li>}
        </ul>
      </Card>
    </div>
  );
}

function ResetPassword({ user, hint, onDone }: { user: ManagedUser; hint: string; onDone: () => void }) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api(`/api/users/${user.id}/set-password/`, {
        method: "POST",
        body: JSON.stringify({ new_password: password }),
      });
      setMessage(`New password set for ${user.username}. Share it with them.`);
      setPassword("");
      setTimeout(onDone, 2500);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="mt-3 space-y-2 rounded-xl bg-slate-50 p-3 dark:bg-slate-800">
      <Field
        label={`New password for ${user.username}`}
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        autoComplete="off"
        required
      />
      {hint && <p className="text-xs text-slate-500">{hint}</p>}
      <ErrorBox error={error} />
      {message && <p className="rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{message}</p>}
      <Button type="submit" disabled={busy}>
        {busy ? "Saving…" : "Set password"}
      </Button>
    </form>
  );
}
