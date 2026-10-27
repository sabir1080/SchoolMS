"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AuthCard } from "@/components/AuthCard";
import { Button, ErrorBox, Field, PasswordField } from "@/components/ui";
import { ApiError, api, savedInstitute, type SavedInstitute } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function LoginPage() {
  const { user, login } = useAuth();
  const router = useRouter();
  const [institute, setInstitute] = useState<SavedInstitute | null>(null);
  const [ready, setReady] = useState(false);
  // Shown on the code step when a remembered institute no longer exists (e.g. it was deleted).
  const [notice, setNotice] = useState("");

  function forget(message = "") {
    savedInstitute.clear();
    setInstitute(null);
    setNotice(message);
  }

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
      const saved = savedInstitute.get();
      if (!saved) {
        setReady(true);
        return;
      }
      // Check the remembered institute still exists before asking for a username.
      lookup(saved.slug)
        .then(setInstitute)
        .catch((err) => {
          if (err instanceof ApiError && (err.status === 404 || err.status === 403)) {
            savedInstitute.clear();
            setNotice(`The institute code “${saved.slug}” saved on this device was not found. Please enter your institute code.`);
          } else {
            setInstitute(saved); // offline or server waking up: keep it and let sign-in report problems
          }
        })
        .finally(() => setReady(true));
    }
  }, []);

  if (!ready) return null;

  return institute ? (
    <CredentialsStep
      institute={institute}
      onChange={() => forget()}
      onLogin={async (username, password) => {
        try {
          await login(institute.slug, username, password);
        } catch (err) {
          if (err instanceof ApiError && /institute code not found/i.test(JSON.stringify(err.body))) {
            forget(`The institute code “${institute.slug}” was not found. Please enter your institute code.`);
            return;
          }
          throw err;
        }
      }}
    />
  ) : (
    <CodeStep
      notice={notice}
      onFound={(found) => {
        savedInstitute.set(found);
        setNotice("");
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

function CodeStep({ notice, onFound }: { notice: string; onFound: (institute: SavedInstitute) => void }) {
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
      {notice && <p className="rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800 dark:bg-amber-950 dark:text-amber-200">{notice}</p>}
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
    <AuthCard title={institute.name} subtitle="Sign in to continue">
      <div className="flex items-center justify-between gap-3 rounded-lg bg-slate-100 px-3 py-2 text-sm dark:bg-slate-800">
        <span>
          Institute code: <span className="font-semibold">{institute.slug}</span>
        </span>
        <button type="button" onClick={onChange} className="font-medium text-indigo-600 hover:underline">
          Change
        </button>
      </div>
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
        Use a different institute code
      </button>
    </AuthCard>
  );
}
