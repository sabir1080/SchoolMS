"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { AgreementDocument } from "@/components/agreements/AgreementDocument";
import { Button, Card, ErrorBox, Field, SelectField } from "@/components/ui";
import { api } from "@/lib/api";
import type { Agreement } from "@/lib/agreements";

const METHODS: [string, string][] = [
  ["bank_transfer", "Bank transfer"],
  ["jazzcash", "JazzCash"],
  ["easypaisa", "Easypaisa"],
  ["cash", "Cash"],
  ["card", "Card"],
  ["other", "Other"],
];

/** The platform owner views an institute's agreement and records its payment (which activates it). */
export default function PlatformAgreementPage() {
  const [agreement, setAgreement] = useState<Agreement | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [form, setForm] = useState({ amount: "", method: "bank_transfer", reference: "" });
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  const load = useCallback(() => {
    const id = new URLSearchParams(window.location.search).get("id");
    api<Agreement>(`/api/platform/agreements/${id}/`)
      .then((a) => {
        setAgreement(a);
        setForm((f) => ({ ...f, amount: a.amount ?? "", reference: a.payment_reference }));
      })
      .catch(setError);
  }, []);
  useEffect(load, [load]);

  if (!agreement) return <ErrorBox error={error} />;

  async function record(e: React.FormEvent) {
    e.preventDefault();
    if (!agreement) return;
    setBusy(true);
    setError(null);
    try {
      await api(`/api/platform/tenants/${agreement.tenant}/record-payment/`, {
        method: "POST",
        body: JSON.stringify({
          plan: agreement.schedule.plan_code,
          billing_cycle: agreement.billing_cycle,
          amount: form.amount,
          currency: agreement.currency,
          method: form.method,
          reference: form.reference,
          agreement: agreement.id,
        }),
      });
      setMessage("Payment recorded. The subscription and the agreement are now active.");
      load();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between print:hidden">
        <Link href="/platform/overview/" className="text-sm text-brand-600 hover:underline">
          ← Overview
        </Link>
        <button onClick={() => window.print()} className="rounded-lg bg-brand-600 px-3 py-2 text-sm font-medium text-white">
          Print / Save PDF
        </button>
      </div>
      {agreement.status === "pending_payment" && (
        <div className="print:hidden">
          <Card>
            <h2 className="font-medium">Record the payment for {agreement.number}</h2>
            <p className="mt-1 text-sm text-slate-500">
              When the money has arrived, record it here: the plan starts, the period is set and the agreement becomes active.
            </p>
            <form onSubmit={record} className="mt-3 grid gap-3 sm:grid-cols-4 sm:items-end">
              <Field label={`Amount (${agreement.currency})`} value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} required />
              <SelectField label="Method" options={METHODS} value={form.method} onChange={(e) => setForm({ ...form, method: e.target.value })} />
              <Field label="Reference" value={form.reference} onChange={(e) => setForm({ ...form, reference: e.target.value })} />
              <Button type="submit" disabled={busy}>
                {busy ? "Saving…" : "Record payment"}
              </Button>
            </form>
          </Card>
        </div>
      )}
      <ErrorBox error={error} />
      {message && <p className="rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-700 print:hidden">{message}</p>}
      <AgreementDocument agreement={agreement} />
    </div>
  );
}
