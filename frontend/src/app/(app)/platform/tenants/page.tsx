"use client";

import { useCallback, useEffect, useState } from "react";

import { Button, Card, ErrorBox, Field, PasswordField, SelectField } from "@/components/ui";
import { api, formatMoney, type Plan, type Subscription, type Tenant } from "@/lib/api";
import { formatDate, STATUS_LABELS } from "@/lib/navigation";
import { COUNTRIES, suggestCode } from "@/lib/regions";

type PlatformTenant = Tenant & {
  is_active: boolean;
  email: string;
  subscription: Subscription | null;
  admin_usernames: string[];
};

interface Payment {
  id: number;
  plan_name: string;
  billing_cycle: string;
  amount: string;
  currency: string;
  method: string;
  reference: string;
  created_at: string;
}

const INSTITUTE_TYPES: [string, string][] = [
  ["school", "School"],
  ["college", "College"],
  ["university", "University"],
  ["coaching", "Coaching Center"],
  ["tuition", "Tuition Center"],
];

const METHODS: [string, string][] = [
  ["bank_transfer", "Bank transfer"],
  ["jazzcash", "JazzCash"],
  ["easypaisa", "Easypaisa"],
  ["cash", "Cash"],
  ["card", "Card"],
  ["other", "Other"],
];

const METHOD_LABELS = Object.fromEntries(METHODS);

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
  const [plans, setPlans] = useState<Plan[]>([]);
  const [open, setOpen] = useState<number | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [error, setError] = useState<unknown>(null);

  const load = useCallback(() => {
    api<{ results: PlatformTenant[] }>("/api/platform/tenants/")
      .then((data) => setTenants(data.results))
      .catch(setError);
  }, []);

  useEffect(() => {
    load();
    api<Plan[]>("/api/public/plans/").then(setPlans).catch(setError);
  }, [load]);

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

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold">Institutes</h1>
        <Button onClick={() => setShowCreate((v) => !v)}>{showCreate ? "Close" : "Add institute"}</Button>
      </div>
      <ErrorBox error={error} />

      {showCreate && (
        <CreateInstitute
          onCreated={() => {
            setShowCreate(false);
            load();
          }}
        />
      )}

      <div className="space-y-3">
        {tenants.map((t) => {
          const sub = t.subscription;
          return (
            <Card key={t.id}>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="truncate font-medium">
                    {t.name}
                    {!t.is_active && <span className="ml-2 text-xs text-red-600">suspended</span>}
                  </p>
                  <p className="truncate text-xs text-slate-500">
                    Code: {t.slug} · {t.institute_type} · {t.country} · {t.currency}
                  </p>
                  {sub && (
                    <p className="mt-1 text-sm">
                      <span className="font-medium">{sub.plan.name}</span> ·{" "}
                      <span className={sub.is_usable ? "text-emerald-600" : "text-red-600"}>
                        {STATUS_LABELS[sub.effective_status]}
                      </span>{" "}
                      · until {formatDate(sub.current_period_end)} · {sub.usage.students} students,{" "}
                      {sub.usage.staff} staff
                    </p>
                  )}
                </div>
                <div className="flex shrink-0 gap-3 text-sm">
                  <button onClick={() => setOpen(open === t.id ? null : t.id)} className="text-brand-600 hover:underline">
                    {open === t.id ? "Close" : "Manage"}
                  </button>
                  <button onClick={() => toggleActive(t)} className="text-slate-600 hover:underline dark:text-slate-300">
                    {t.is_active ? "Suspend" : "Activate"}
                  </button>
                </div>
              </div>
              {open === t.id && sub && (
                <>
                  <ManageSubscription tenant={t} plans={plans} onSaved={load} />
                  <ResetAdminPassword tenant={t} />
                </>
              )}
            </Card>
          );
        })}
        {tenants.length === 0 && <p className="text-sm text-slate-500">No institutes yet.</p>}
      </div>
    </div>
  );
}

function ManageSubscription({ tenant, plans, onSaved }: { tenant: PlatformTenant; plans: Plan[]; onSaved: () => void }) {
  const sub = tenant.subscription!;
  const [form, setForm] = useState({
    plan: sub.plan.code,
    billing_cycle: "monthly",
    amount: "",
    currency: tenant.currency,
    method: "bank_transfer",
    reference: "",
  });
  const [payments, setPayments] = useState<Payment[]>([]);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  const loadPayments = useCallback(() => {
    api<Payment[]>(`/api/platform/tenants/${tenant.id}/payments/`).then(setPayments).catch(setError);
  }, [tenant.id]);

  useEffect(loadPayments, [loadPayments]);

  // Pre-fill the plan's price when the plan, cycle or currency changes.
  useEffect(() => {
    const plan = plans.find((p) => p.code === form.plan);
    const price = plan?.prices.find((p) => p.currency === form.currency && p.billing_cycle === form.billing_cycle);
    if (price) setForm((f) => ({ ...f, amount: price.amount }));
  }, [plans, form.plan, form.billing_cycle, form.currency]);

  const set = (key: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setForm((f) => ({ ...f, [key]: e.target.value }));

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setMessage("");
    try {
      await api(`/api/platform/tenants/${tenant.id}/record-payment/`, { method: "POST", body: JSON.stringify(form) });
      setMessage("Payment recorded and subscription extended.");
      loadPayments();
      onSaved();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mt-4 space-y-4 border-t border-slate-200 pt-4 dark:border-slate-800">
      <form onSubmit={onSubmit} className="space-y-4">
        <h3 className="text-sm font-medium">Record payment &amp; extend</h3>
        <div className="grid gap-4 sm:grid-cols-3">
          <SelectField label="Plan" options={plans.map((p) => [p.code, p.name])} value={form.plan} onChange={set("plan")} />
          <SelectField
            label="Billing cycle"
            options={[
              ["monthly", "Monthly (+30 days)"],
              ["yearly", "Yearly (+365 days)"],
            ]}
            value={form.billing_cycle}
            onChange={set("billing_cycle")}
          />
          <SelectField label="Method" options={METHODS} value={form.method} onChange={set("method")} />
          <Field label="Amount" type="number" min="0" step="0.01" value={form.amount} onChange={set("amount")} required />
          <Field label="Currency" value={form.currency} onChange={set("currency")} maxLength={3} required />
          <Field label="Reference (optional)" value={form.reference} onChange={set("reference")} />
        </div>
        <ErrorBox error={error} />
        {message && <p className="rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{message}</p>}
        <Button type="submit" disabled={busy}>
          {busy ? "Saving…" : "Record payment"}
        </Button>
      </form>

      <div>
        <h3 className="mb-2 text-sm font-medium">Payment history</h3>
        {payments.length === 0 ? (
          <p className="text-sm text-slate-500">No payments yet.</p>
        ) : (
          <ul className="divide-y divide-slate-200 text-sm dark:divide-slate-800">
            {payments.map((p) => (
              <li key={p.id} className="flex flex-wrap justify-between gap-2 py-2">
                <span>
                  {formatDate(p.created_at)} · {p.plan_name} ({p.billing_cycle}) · {METHOD_LABELS[p.method] ?? p.method}
                  {p.reference && ` · ${p.reference}`}
                </span>
                <span className="font-medium">{formatMoney(p.amount, p.currency)}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

function CreateInstitute({ onCreated }: { onCreated: () => void }) {
  const [form, setForm] = useState(EMPTY_FORM);
  const [error, setError] = useState<unknown>(null);
  const [saving, setSaving] = useState(false);

  const set = (key: keyof typeof EMPTY_FORM) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setForm((f) => ({ ...f, [key]: e.target.value }));

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await api("/api/platform/tenants/", { method: "POST", body: JSON.stringify(form) });
      setForm(EMPTY_FORM);
      onCreated();
    } catch (err) {
      setError(err);
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card>
      <form onSubmit={onSubmit} className="space-y-4">
        <h2 className="font-medium">Add institute (starts on a free trial)</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field
            label="Institute name"
            value={form.name}
            onChange={(e) => setForm((f) => ({ ...f, name: e.target.value, slug: suggestCode(e.target.value) }))}
            required
          />
          <Field label="Institute code" value={form.slug} onChange={set("slug")} autoCapitalize="none" required />
          <SelectField label="Type" options={INSTITUTE_TYPES} value={form.institute_type} onChange={set("institute_type")} />
          <SelectField
            label="Country"
            options={COUNTRIES.map((c) => [c.code, c.name])}
            value={form.country}
            onChange={(e) => {
              const country = COUNTRIES.find((c) => c.code === e.target.value);
              setForm((f) => ({ ...f, country: e.target.value, currency: country?.currency ?? f.currency }));
            }}
          />
          <Field label="Currency" value={form.currency} onChange={set("currency")} maxLength={3} required />
          <Field label="Timezone" value={form.timezone} onChange={set("timezone")} required />
        </div>
        <h3 className="pt-2 text-sm font-medium text-slate-500">First admin account</h3>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Admin username" value={form.admin_username} onChange={set("admin_username")} autoCapitalize="none" required />
          <Field label="Admin email" type="email" value={form.admin_email} onChange={set("admin_email")} required />
          <PasswordField label="Admin password" value={form.admin_password} onChange={set("admin_password")} required />
        </div>
        <ErrorBox error={error} />
        <Button type="submit" disabled={saving}>
          {saving ? "Creating…" : "Create institute"}
        </Button>
      </form>
    </Card>
  );
}

function ResetAdminPassword({ tenant }: { tenant: PlatformTenant }) {
  const [username, setUsername] = useState(tenant.admin_usernames[0] ?? "");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  if (tenant.admin_usernames.length === 0) return null;

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setMessage("");
    try {
      await api(`/api/platform/tenants/${tenant.id}/reset-admin-password/`, {
        method: "POST",
        body: JSON.stringify({ username, new_password: password }),
      });
      setMessage(`New password set for ${username}.`);
      setPassword("");
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="mt-4 space-y-4 border-t border-slate-200 pt-4 dark:border-slate-800">
      <h3 className="text-sm font-medium">Reset admin password</h3>
      <div className="grid gap-4 sm:grid-cols-2">
        <SelectField
          label="Admin"
          options={tenant.admin_usernames.map((u) => [u, u])}
          value={username}
          onChange={(e) => setUsername(e.target.value)}
        />
        <PasswordField
          label="New admin password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete="off"
          required
        />
      </div>
      <ErrorBox error={error} />
      {message && <p className="rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{message}</p>}
      <Button type="submit" disabled={busy}>
        {busy ? "Saving…" : "Reset password"}
      </Button>
    </form>
  );
}
