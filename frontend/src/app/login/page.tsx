"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AuthCard } from "@/components/AuthCard";
import { Button, ErrorBox, Field, PasswordField } from "@/components/ui";
import { api, savedInstitute, type SavedInstitute } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function LoginPage() {
  const { user, login } = useAuth();
  const router = useRouter();
  const [institute, setInstitute] = useState<SavedInstitute | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (user) router.replace(user.role === "super_admin" ? "/platform/tenants" : "/dashboard");
  }, [user, router]);

  useEffect(() => {
    // A shared link like /login/?code=al-huda skips typing the code.
    const code = new URLSearchParams(window.location.search).get("code");
    if (code) {
      lookup(code)
        .then(setInstitute)
        .catch(() => setInstitute(null))
        .finally(() => setReady(true));
    } else {
      setInstitute(savedInstitute.get());
      setReady(true);
    }
  }, []);

  if (!ready) return null;

  return institute ? (
    <CredentialsStep
      institute={institute}
      onChange={() => {
        savedInstitute.clear();
        setInstitute(null);
      }}
      onLogin={async (username, password) => {
        await login(institute.slug, username, password);
      }}
    />
  ) : (
    <CodeStep
      onFound={(found) => {
        savedInstitute.set(found);
        setInstitute(found);
      }}
    />
  );
}

async function lookup(code: string): Promise<SavedInstitute> {
  const data = await api<SavedInstitute>(`/api/public/institutes/${encodeURIComponent(code.trim().toLowerCase())}/`);
  savedInstitute.set({ name: data.name, slug: data.slug });
  return { name: data.name, slug: data.slug };
}

function CodeStep({ onFound }: { onFound: (institute: SavedInstitute) => void }) {
  const [code, setCode] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      onFound(await lookup(code));
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthCard title="SchoolMS" subtitle="Enter your institute code to continue">
      <form onSubmit={onSubmit} className="space-y-4">
        <Field
          label="Institute code"
          value={code}
          onChange={(e) => setCode(e.target.value)}
          placeholder="e.g. al-huda"
          autoCapitalize="none"
          autoCorrect="off"
          autoFocus
          required
        />
        <ErrorBox error={error} />
        <Button type="submit" disabled={busy} className="w-full py-2.5">
          {busy ? "Checking…" : "Continue"}
        </Button>
      </form>
      <p className="text-center text-sm text-slate-500">
        New institute?{" "}
        <Link href="/register" className="font-medium text-indigo-600 hover:underline">
          Register and start a free trial
        </Link>
      </p>
    </AuthCard>
  );
}

function CredentialsStep({
  institute,
  onChange,
  onLogin,
}: {
  institute: SavedInstitute;
  onChange: () => void;
  onLogin: (username: string, password: string) => Promise<void>;
}) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await onLogin(username, password);
    } catch (err) {
      setError(err);
      setBusy(false);
    }
  }

  return (
    <AuthCard title={institute.name} subtitle={`Institute code: ${institute.slug}`}>
      <form onSubmit={onSubmit} className="space-y-4">
        <Field
          label="Username or email"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          autoComplete="username"
          autoCapitalize="none"
          autoCorrect="off"
          required
        />
        <PasswordField
          label="Password"
         
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete="current-password"
          required
        />
        <ErrorBox error={error} />
        <Button type="submit" disabled={busy} className="w-full py-2.5">
          {busy ? "Signing in…" : "Sign in"}
        </Button>
      </form>
      <p className="text-center text-xs text-slate-500">
        Forgot your password? Ask your institute admin to reset it.
      </p>
      <button onClick={onChange} className="w-full text-center text-sm text-indigo-600 hover:underline">
        Change institute
      </button>
    </AuthCard>
  );
}
