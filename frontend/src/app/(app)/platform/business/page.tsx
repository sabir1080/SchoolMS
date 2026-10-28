"use client";

import { useEffect, useState } from "react";

import { Button, Card, ErrorBox, Field } from "@/components/ui";
import { api } from "@/lib/api";

interface Profile {
  business_name: string;
  owner_name: string;
  address: string;
  phone: string;
  email: string;
  payment_instructions: string;
  grace_days: number;
  data_retention_days: number;
  refund_policy: string;
}

const area =
  "w-full rounded-lg border border-slate-300 bg-transparent px-3 py-2 text-sm outline-none focus:border-brand-500 dark:border-slate-700";

/** The platform owner's business details and terms, used in every new agreement. */
export default function BusinessPage() {
  const [form, setForm] = useState<Profile | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [message, setMessage] = useState("");

  useEffect(() => {
    api<Profile>("/api/platform/profile/").then(setForm).catch(setError);
  }, []);

  if (!form) return <ErrorBox error={error} />;
  const set = (key: keyof Profile) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => setForm({ ...form, [key]: e.target.value });

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setMessage("");
    try {
      setForm(await api<Profile>("/api/platform/profile/", { method: "PATCH", body: JSON.stringify(form) }));
      setMessage("Saved. New agreements will use these details; signed agreements keep the details they were signed with.");
    } catch (err) {
      setError(err);
    }
  }

  return (
    <form onSubmit={save} className="max-w-2xl space-y-4">
      <h1 className="text-2xl font-semibold">Business details</h1>
      <Card>
        <h2 className="font-medium">You, as the service provider</h2>
        <p className="mb-3 text-sm text-slate-500">Printed at the top of every agreement.</p>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Business name" value={form.business_name} onChange={set("business_name")} required maxLength={150} />
          <Field label="Owner name" value={form.owner_name} onChange={set("owner_name")} maxLength={150} />
          <Field label="Phone" value={form.phone} onChange={set("phone")} maxLength={50} />
          <Field label="Email" type="email" value={form.email} onChange={set("email")} />
          <div className="sm:col-span-2">
            <Field label="Address" value={form.address} onChange={set("address")} maxLength={255} />
          </div>
        </div>
      </Card>
      <Card>
        <h2 className="font-medium">How institutes pay you</h2>
        <p className="mb-3 text-sm text-slate-500">Shown to an institute right after it signs (bank account, JazzCash / Easypaisa number).</p>
        <textarea
          value={form.payment_instructions}
          onChange={set("payment_instructions")}
          rows={4}
          className={area}
          placeholder={"Bank: Meezan Bank, Account title: …, Account no: …\nJazzCash / Easypaisa: 0300-…"}
          aria-label="Payment instructions"
        />
      </Card>
      <Card>
        <h2 className="font-medium">Terms</h2>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          <Field label="Grace days for late renewal" type="number" min={0} max={60} value={String(form.grace_days)} onChange={set("grace_days")} />
          <Field label="Keep data after expiry (days)" type="number" min={30} max={3650} value={String(form.data_retention_days)} onChange={set("data_retention_days")} />
          <div className="sm:col-span-2">
            <Field label="Refund policy" value={form.refund_policy} onChange={set("refund_policy")} maxLength={255} />
          </div>
        </div>
      </Card>
      <ErrorBox error={error} />
      {message && <p className="rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{message}</p>}
      <Button type="submit">Save details</Button>
    </form>
  );
}
