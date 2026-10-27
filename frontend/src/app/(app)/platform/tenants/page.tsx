"use client";

import { useCallback, useEffect, useState } from "react";

import { Button, Card, ErrorBox, Field, SelectField } from "@/components/ui";
import { api, type Tenant } from "@/lib/api";

type PlatformTenant = Tenant & { is_active: boolean; email: string };

const INSTITUTE_TYPES: [string, string][] = [
  ["school", "School"],
  ["college", "College"],
  ["university", "University"],
  ["coaching", "Coaching Center"],
  ["tuition", "Tuition Center"],
];

const EMPTY_FORM = {
  name: "",
  slug: "",
  institute_type: "school",
  country: "PK",
  currency: "PKR",
  timezone: "Asia/Karachi",
  admin_username: "",
  admin_email: "",
  admin_password: "",
};

export default function TenantsPage() {
  const [tenants, setTenants] = useState<PlatformTenant[]>([]);
  const [form, setForm] = useState(EMPTY_FORM);
  const [error, setError] = useState<unknown>(null);
  const [saving, setSaving] = useState(false);

  const load = useCallback(() => {
    api<{ results: PlatformTenant[] }>("/api/platform/tenants/")
      .then((data) => setTenants(data.results))
      .catch(setError);
  }, []);

  useEffect(load, [load]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await api("/api/platform/tenants/", { method: "POST", body: JSON.stringify(form) });
      setForm(EMPTY_FORM);
      load();
    } catch (err) {
      setError(err);
    } finally {
      setSaving(false);
    }
  }

  async function toggleActive(tenant: PlatformTenant) {
    try {
      await api(`/api/platform/tenants/${tenant.id}/`, {
        method: "PATCH",
        body: JSON.stringify({ is_active: !tenant.is_active }),
      });
      load();
    } catch (err) {
      setError(err);
    }
  }

  const set = (key: keyof typeof EMPTY_FORM) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setForm({ ...form, [key]: e.target.value });

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Institutes</h1>

      <Card>
        <form onSubmit={onSubmit} className="space-y-4">
          <h2 className="font-medium">Add institute</h2>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Institute name" value={form.name} onChange={set("name")} required />
            <Field
              label="Short code (slug)"
              value={form.slug}
              onChange={set("slug")}
              pattern="[a-z0-9-]+"
              title="Lowercase letters, numbers and dashes"
              required
            />
            <SelectField label="Type" options={INSTITUTE_TYPES} value={form.institute_type} onChange={set("institute_type")} />
            <Field label="Country (2 letters)" value={form.country} onChange={set("country")} maxLength={2} required />
            <Field label="Currency" value={form.currency} onChange={set("currency")} maxLength={3} required />
            <Field label="Timezone" value={form.timezone} onChange={set("timezone")} required />
          </div>
          <h3 className="pt-2 text-sm font-medium text-slate-500">First admin account</h3>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Admin username" value={form.admin_username} onChange={set("admin_username")} required />
            <Field label="Admin email" type="email" value={form.admin_email} onChange={set("admin_email")} required />
            <Field
              label="Admin password"
              type="password"
              value={form.admin_password}
              onChange={set("admin_password")}
              required
            />
          </div>
          <ErrorBox error={error} />
          <Button type="submit" disabled={saving}>
            {saving ? "Creating…" : "Create institute"}
          </Button>
        </form>
      </Card>

      <Card>
        <h2 className="mb-4 font-medium">All institutes</h2>
        <ul className="divide-y divide-slate-200 dark:divide-slate-800">
          {tenants.map((t) => (
            <li key={t.id} className="flex items-center justify-between gap-3 py-3">
              <div className="min-w-0">
                <p className="truncate font-medium">
                  {t.name}
                  {!t.is_active && <span className="ml-2 text-xs text-red-600">suspended</span>}
                </p>
                <p className="truncate text-xs text-slate-500">
                  {t.slug} · {t.institute_type} · {t.country} · {t.currency}
                </p>
              </div>
              <button onClick={() => toggleActive(t)} className="shrink-0 text-sm text-indigo-600 hover:underline">
                {t.is_active ? "Suspend" : "Activate"}
              </button>
            </li>
          ))}
          {tenants.length === 0 && <li className="py-3 text-sm text-slate-500">No institutes yet.</li>}
        </ul>
      </Card>
    </div>
  );
}
