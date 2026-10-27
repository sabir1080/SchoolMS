"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Button, Card, ErrorBox, Field, PasswordField, SelectField } from "@/components/ui";
import { api, type LoginResponse } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { browserTimezone, COUNTRIES, suggestCode } from "@/lib/regions";

const INSTITUTE_TYPES: [string, string][] = [
  ["school", "School"],
  ["college", "College"],
  ["university", "University"],
  ["coaching", "Coaching Center"],
  ["tuition", "Tuition Center"],
];

export default function RegisterPage() {
  const { user, acceptLogin } = useAuth();
  const router = useRouter();
  const [form, setForm] = useState({
    name: "",
    slug: "",
    institute_type: "school",
    country: "PK",
    currency: "PKR",
    timezone: "Asia/Karachi",
    phone: "",
    admin_first_name: "",
    admin_last_name: "",
    admin_username: "",
    admin_email: "",
    admin_password: "",
  });
  const [codeEdited, setCodeEdited] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setForm((f) => ({ ...f, timezone: browserTimezone() }));
  }, []);

  useEffect(() => {
    if (user) router.replace("/dashboard");
  }, [user, router]);

  const set = (key: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setForm((f) => ({ ...f, [key]: e.target.value }));

  function onName(e: React.ChangeEvent<HTMLInputElement>) {
    const name = e.target.value;
    setForm((f) => ({ ...f, name, slug: codeEdited ? f.slug : suggestCode(name) }));
  }

  function onCountry(e: React.ChangeEvent<HTMLSelectElement>) {
    const country = COUNTRIES.find((c) => c.code === e.target.value);
    setForm((f) => ({ ...f, country: e.target.value, currency: country?.currency ?? f.currency }));
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const data = await api<LoginResponse>("/api/public/register/", { method: "POST", body: JSON.stringify(form) });
      await acceptLogin(data);
    } catch (err) {
      setError(err);
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto max-w-2xl space-y-4 px-4 py-8">
      <div>
        <h1 className="text-2xl font-semibold">Register your institute</h1>
        <p className="text-sm text-slate-500">Start with a 14-day free trial. No payment needed.</p>
      </div>
      <form onSubmit={onSubmit} className="space-y-4">
        <Card>
          <h2 className="mb-4 font-medium">Institute</h2>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Institute name" value={form.name} onChange={onName} required />
            <div>
              <Field
                label="Institute code"
                value={form.slug}
                onChange={(e) => {
                  setCodeEdited(true);
                  set("slug")(e);
                }}
                autoCapitalize="none"
                autoCorrect="off"
                required
              />
              <p className="mt-1 text-xs text-slate-500">Your users type this code to log in.</p>
            </div>
            <SelectField label="Type" options={INSTITUTE_TYPES} value={form.institute_type} onChange={set("institute_type")} />
            <SelectField
              label="Country"
              options={COUNTRIES.map((c) => [c.code, c.name])}
              value={form.country}
              onChange={onCountry}
            />
            <Field label="Currency" value={form.currency} onChange={set("currency")} maxLength={3} required />
            <Field label="Phone (optional)" value={form.phone} onChange={set("phone")} />
          </div>
        </Card>
        <Card>
          <h2 className="mb-4 font-medium">Your admin account</h2>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="First name" value={form.admin_first_name} onChange={set("admin_first_name")} />
            <Field label="Last name" value={form.admin_last_name} onChange={set("admin_last_name")} />
            <Field
              label="Username"
              value={form.admin_username}
              onChange={set("admin_username")}
              autoCapitalize="none"
              autoComplete="username"
              required
            />
            <Field label="Email" type="email" value={form.admin_email} onChange={set("admin_email")} required />
            <PasswordField
              label="Password"
              value={form.admin_password}
              onChange={set("admin_password")}
              autoComplete="new-password"
              required
            />
            <p className="-mt-2 text-xs text-slate-500 sm:col-span-2">
              At least 4 characters. You can make password rules stricter later in Institute settings.
            </p>
          </div>
        </Card>
        <ErrorBox error={error} />
        <Button type="submit" disabled={busy} className="w-full py-3 sm:w-auto">
          {busy ? "Creating…" : "Create institute & start trial"}
        </Button>
      </form>
      <p className="text-sm text-slate-500">
        Already registered?{" "}
        <Link href="/login" className="font-medium text-indigo-600 hover:underline">
          Log in
        </Link>
      </p>
    </main>
  );
}
