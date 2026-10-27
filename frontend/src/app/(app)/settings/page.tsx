"use client";

import { useEffect, useState } from "react";

import { BrandingSettings } from "@/components/BrandingSettings";
import { PaymentSettings } from "@/components/payments/PaymentSettings";
import { Button, Card, ErrorBox, Field } from "@/components/ui";
import { api, type PasswordPolicy } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { POLICY_OPTIONS } from "@/lib/passwords";
import { defaultTermsFor } from "@/lib/terms";

interface InstituteSettings {
  name: string;
  slug: string;
  institute_type: string;
  email: string;
  phone: string;
  address: string;
  country: string;
  currency: string;
  timezone: string;
  password_policy: PasswordPolicy;
  program_label: string;
  section_label: string;
}

export default function SettingsPage() {
  const { user, refreshUser } = useAuth();
  const [form, setForm] = useState<InstituteSettings | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api<InstituteSettings>("/api/institute/settings/").then(setForm).catch(setError);
  }, []);

  if (user?.role !== "admin") {
    return <p className="text-sm text-slate-500">Only institute admins can change settings.</p>;
  }
  if (!form) return <ErrorBox error={error} />;

  const set = (key: keyof InstituteSettings) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setForm({ ...form, [key]: e.target.value });

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form) return;
    setBusy(true);
    setError(null);
    setMessage("");
    try {
      const { name, email, phone, address, password_policy, program_label, section_label } = form;
      setForm(
        await api<InstituteSettings>("/api/institute/settings/", {
          method: "PATCH",
          body: JSON.stringify({ name, email, phone, address, password_policy, program_label, section_label }),
        }),
      );
      setMessage("Settings saved.");
      refreshUser();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="max-w-2xl space-y-6">
      <form onSubmit={onSubmit} className="space-y-6">
        <h1 className="text-2xl font-semibold">Institute settings</h1>

        <Card>
          <h2 className="mb-4 font-medium">Institute details</h2>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Institute name" value={form.name} onChange={set("name")} required />
            <Field label="Institute code" value={form.slug} disabled />
            <Field label="Email" type="email" value={form.email} onChange={set("email")} />
            <Field label="Phone" value={form.phone} onChange={set("phone")} />
            <label className="block space-y-1 sm:col-span-2">
              <span className="text-sm font-medium">Address</span>
              <textarea
                value={form.address}
                onChange={set("address")}
                rows={2}
                className="w-full rounded-lg border border-slate-300 bg-transparent px-3 py-2 text-sm outline-none focus:border-brand-500 dark:border-slate-700"
              />
            </label>
          </div>
          <p className="mt-3 text-xs text-slate-500">
            Code, country ({form.country}), currency ({form.currency}) and timezone ({form.timezone}) can be changed by
            the platform team.
          </p>
        </Card>

        <Card>
          <h2 className="font-medium">Names used in your institute</h2>
          <p className="mb-4 text-sm text-slate-500">
            What do you call a class and a section? Leave empty to use the default.
          </p>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field
              label="Instead of “Class” (e.g. Course, Grade, Program)"
              value={form.program_label}
              onChange={set("program_label")}
              placeholder={defaultTermsFor(form.institute_type).program}
              maxLength={30}
            />
            <Field
              label="Instead of “Section” (e.g. Batch, Group)"
              value={form.section_label}
              onChange={set("section_label")}
              placeholder={defaultTermsFor(form.institute_type).section}
              maxLength={30}
            />
          </div>
        </Card>

        <Card>
          <h2 className="font-medium">Password rules</h2>
          <p className="mb-4 text-sm text-slate-500">Applies when anyone in your institute sets a new password.</p>
          <div className="space-y-2">
            {POLICY_OPTIONS.map((option) => (
              <label
                key={option.value}
                className={`flex cursor-pointer gap-3 rounded-xl border p-3 ${
                  form.password_policy === option.value
                    ? "border-brand-500 bg-brand-50 dark:bg-brand-950"
                    : "border-slate-200 dark:border-slate-700"
                }`}
              >
                <input
                  type="radio"
                  name="password_policy"
                  value={option.value}
                  checked={form.password_policy === option.value}
                  onChange={() => setForm({ ...form, password_policy: option.value })}
                  className="mt-1"
                />
                <span>
                  <span className="block text-sm font-medium">{option.label}</span>
                  <span className="block text-xs text-slate-500">{option.hint}</span>
                </span>
              </label>
            ))}
          </div>
          <p className="mt-3 text-xs text-slate-500">Existing passwords keep working; the rule applies to new ones.</p>
        </Card>

        <ErrorBox error={error} />
        {message && <p className="rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{message}</p>}
        <Button type="submit" disabled={busy}>
          {busy ? "Saving…" : "Save settings"}
        </Button>
      </form>
      <BrandingSettings />
      <PaymentSettings />
    </div>
  );
}
