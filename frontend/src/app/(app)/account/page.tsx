"use client";

import { useState } from "react";

import { Button, Card, ErrorBox, Field } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { ROLE_LABELS } from "@/lib/navigation";
import { policyHint } from "@/lib/passwords";

const EMPTY = { current_password: "", new_password: "", confirm: "" };

export default function AccountPage() {
  const { user } = useAuth();
  const [form, setForm] = useState(EMPTY);
  const [error, setError] = useState<unknown>(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  if (!user) return null;

  const set = (key: keyof typeof EMPTY) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [key]: e.target.value }));

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setMessage("");
    if (form.new_password !== form.confirm) {
      setError(new ApiError(400, { confirm: ["The two new passwords do not match."] }));
      return;
    }
    setBusy(true);
    try {
      await api("/api/auth/change-password/", {
        method: "POST",
        body: JSON.stringify({ current_password: form.current_password, new_password: form.new_password }),
      });
      setForm(EMPTY);
      setMessage("Your password has been changed. Use the new password next time you log in.");
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  const hint = user.tenant ? policyHint(user.tenant.password_policy) : "";

  return (
    <div className="max-w-lg space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Change password</h1>
        <p className="text-sm text-slate-500">
          {user.username} · {ROLE_LABELS[user.role]}
          {user.tenant && ` · ${user.tenant.name}`}
        </p>
      </div>
      <Card>
        <form onSubmit={onSubmit} className="space-y-4">
          <Field
            label="Current password"
            type="password"
            value={form.current_password}
            onChange={set("current_password")}
            autoComplete="current-password"
            required
          />
          <div>
            <Field
              label="New password"
              type="password"
              value={form.new_password}
              onChange={set("new_password")}
              autoComplete="new-password"
              required
            />
            {hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
          </div>
          <Field
            label="Confirm new password"
            type="password"
            value={form.confirm}
            onChange={set("confirm")}
            autoComplete="new-password"
            required
          />
          <ErrorBox error={error} />
          {message && <p className="rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{message}</p>}
          <Button type="submit" disabled={busy}>
            {busy ? "Saving…" : "Change password"}
          </Button>
        </form>
      </Card>
    </div>
  );
}
