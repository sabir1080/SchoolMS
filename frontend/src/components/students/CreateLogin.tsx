"use client";

import { useState } from "react";

import { Button, ErrorBox, Field } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { policyHint } from "@/lib/passwords";

/** Small form that creates a login (username + password) through ``url``. */
export function CreateLogin({
  url,
  suggestedUsername,
  onCreated,
}: {
  url: string;
  suggestedUsername: string;
  onCreated: () => void;
}) {
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const [username, setUsername] = useState(suggestedUsername);
  const [password, setPassword] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  if (!open) {
    return (
      <button onClick={() => setOpen(true)} className="text-sm text-indigo-600 hover:underline">
        Create login
      </button>
    );
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api(url, { method: "POST", body: JSON.stringify({ username, password }) });
      onCreated();
    } catch (err) {
      setError(err);
      setBusy(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="mt-2 space-y-2 rounded-xl bg-slate-50 p-3 dark:bg-slate-800">
      <div className="grid gap-2 sm:grid-cols-2">
        <Field label="Username" value={username} onChange={(e) => setUsername(e.target.value)} autoCapitalize="none" required />
        <Field label="Password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="off" required />
      </div>
      <p className="text-xs text-slate-500">
        {policyHint(user?.tenant?.password_policy)} They log in with institute code{" "}
        <span className="font-medium">{user?.tenant?.slug}</span>.
      </p>
      <ErrorBox error={error} />
      <div className="flex gap-3">
        <Button type="submit" disabled={busy}>
          {busy ? "Creating…" : "Create login"}
        </Button>
        <button type="button" onClick={() => setOpen(false)} className="text-sm text-slate-500">
          Cancel
        </button>
      </div>
    </form>
  );
}

/** Lowercase letters and digits from a name, e.g. "Ali Raza" -> "aliraza". */
export function usernameFrom(name: string) {
  return name.toLowerCase().replace(/[^a-z0-9]/g, "").slice(0, 20);
}
