"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { AgreementDocument } from "@/components/agreements/AgreementDocument";
import { Button, Card, ErrorBox, Field, SelectField } from "@/components/ui";
import { api, type Plan } from "@/lib/api";
import { AGREEMENT_TONE, type Agreement, type AgreementPreview } from "@/lib/agreements";
import { useAuth } from "@/lib/auth";
import { formatDate } from "@/lib/navigation";

/** Agreements on the Plan & Billing page: accept the trial, sign for a plan, pay, and see every agreement. */
export function BillingAgreements({ plans, choose, onChosen }: { plans: Plan[]; choose: string | null; onChosen: () => void }) {
  const [agreements, setAgreements] = useState<Agreement[] | null>(null);
  const [error, setError] = useState<unknown>(null);

  const load = useCallback(() => {
    api<Agreement[]>("/api/agreements/").then(setAgreements).catch(setError);
  }, []);
  useEffect(load, [load]);

  if (!agreements) return <ErrorBox error={error} />;
  const pending = agreements.find((a) => a.status === "pending_payment");

  return (
    <div className="space-y-4">
      {agreements.length === 0 && <AcceptTrial onDone={load} />}
      {choose && (
        <SignForm
          key={choose}
          plan={plans.find((p) => p.code === choose)!}
          onCancel={onChosen}
          onSigned={() => {
            onChosen();
            load();
          }}
        />
      )}
      {pending && !choose && <PendingPayment agreement={pending} onChange={load} />}
      <Card>
        <h2 className="font-medium">Your agreements</h2>
        {agreements.length === 0 ? (
          <p className="mt-1 text-sm text-slate-500">No agreement yet.</p>
        ) : (
          <ul className="mt-2 divide-y divide-slate-100 text-sm dark:divide-slate-800">
            {agreements.map((a) => (
              <li key={a.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
                <span className="min-w-0">
                  <span className="block font-medium">
                    {a.number} · {a.kind === "trial" ? "Free trial" : `${a.plan_name} (${a.billing_cycle})`}
                  </span>
                  <span className="block text-xs text-slate-500">
                    Signed {formatDate(a.signed_at)} by {a.signer_name}
                    {a.period_end && ` · paid until ${formatDate(a.period_end)}`}
                  </span>
                </span>
                <span className="flex items-center gap-3">
                  <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${AGREEMENT_TONE[a.status]}`}>{a.status_label}</span>
                  <Link href={`/agreement/?id=${a.id}`} className="text-brand-600 hover:underline">
                    View
                  </Link>
                </span>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}

function AcceptTrial({ onDone }: { onDone: () => void }) {
  const { user } = useAuth();
  const [doc, setDoc] = useState<AgreementPreview | null>(null);
  const [name, setName] = useState([user?.first_name, user?.last_name].filter(Boolean).join(" "));
  const [accept, setAccept] = useState(false);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    api<AgreementPreview>("/api/public/agreements/trial/", {}, false).then(setDoc).catch(setError);
  }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    try {
      await api("/api/agreements/accept-trial/", { method: "POST", body: JSON.stringify({ accept, signer_name: name }) });
      onDone();
    } catch (err) {
      setError(err);
    }
  }

  return (
    <Card>
      <h2 className="font-medium">Please accept the free trial agreement</h2>
      <p className="mt-1 text-sm text-slate-500">Your institute was set up for you. Read the short agreement and accept it.</p>
      {doc && (
        <details className="mt-3 rounded-xl border border-slate-200 p-3 dark:border-slate-700">
          <summary className="cursor-pointer text-sm font-medium text-brand-600">Read the free trial agreement</summary>
          <div className="mt-3">
            <AgreementDocument preview={doc} />
          </div>
        </details>
      )}
      <form onSubmit={submit} className="mt-3 space-y-3">
        <Field label="Your full name" value={name} onChange={(e) => setName(e.target.value)} required maxLength={150} />
        <label className="flex items-start gap-2 text-sm">
          <input type="checkbox" checked={accept} onChange={(e) => setAccept(e.target.checked)} className="mt-1" required />
          I have read and agree to the free trial agreement.
        </label>
        <ErrorBox error={error} />
        <Button type="submit">Accept agreement</Button>
      </form>
    </Card>
  );
}

const DETAIL_FIELDS: [string, string, string?][] = [
  ["institute_legal_name", "Institute's full (legal) name"],
  ["institute_address", "Institute address"],
  ["signer_name", "Your full name"],
  ["signer_designation", "Your designation (e.g. Principal, Owner)"],
  ["signer_cnic", "Your CNIC", "35202-1234567-1"],
  ["signer_phone", "Your mobile number", "0300-1234567"],
];

function SignForm({ plan, onCancel, onSigned }: { plan: Plan; onCancel: () => void; onSigned: () => void }) {
  const [cycle, setCycle] = useState("yearly");
  const [doc, setDoc] = useState<AgreementPreview | null>(null);
  const [form, setForm] = useState<Record<string, string> | null>(null);
  const [signature, setSignature] = useState("");
  const [accept, setAccept] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setDoc(null);
    api<AgreementPreview>(`/api/agreements/preview/?plan=${plan.code}&cycle=${cycle}`)
      .then((d) => {
        setDoc(d);
        setForm((f) => f ?? { ...(d.prefill ?? {}) });
      })
      .catch(setError);
  }, [plan.code, cycle]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api("/api/agreements/", { method: "POST", body: JSON.stringify({ plan: plan.code, billing_cycle: cycle, ...form, signature, accept }) });
      onSigned();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="font-medium">Subscription agreement: {plan.name}</h2>
          <p className="mt-1 text-sm text-slate-500">
            {doc?.renewal
              ? "Renewal: your details from the last agreement are filled in. Check them, then sign."
              : "Fill in your details, read the agreement and sign. Then pay, and we activate your plan."}
          </p>
        </div>
        <button type="button" onClick={onCancel} className="text-sm text-slate-500 hover:underline">
          Close
        </button>
      </div>
      <form onSubmit={submit} className="mt-4 space-y-4">
        <div className="max-w-xs">
          <SelectField
            label="Billing period"
            options={[
              ["yearly", "Yearly (365 days)"],
              ["monthly", "Monthly (30 days)"],
            ]}
            value={cycle}
            onChange={(e) => setCycle(e.target.value)}
          />
        </div>
        {doc && (
          <p className="text-sm">
            Fee: <span className="font-semibold">{doc.schedule.price}</span> per {cycle === "yearly" ? "year" : "month"}
          </p>
        )}
        {form && (
          <div className="grid gap-3 sm:grid-cols-2">
            {DETAIL_FIELDS.map(([key, label, placeholder]) => (
              <Field
                key={key}
                label={label}
                value={form[key] ?? ""}
                placeholder={placeholder}
                onChange={(e) => setForm({ ...form, [key]: e.target.value })}
                required
              />
            ))}
          </div>
        )}
        {doc && (
          <details className="rounded-xl border border-slate-200 p-3 dark:border-slate-700">
            <summary className="cursor-pointer text-sm font-medium text-brand-600">Read the full agreement</summary>
            <div className="mt-3">
              <AgreementDocument preview={doc} />
            </div>
          </details>
        )}
        <label className="flex items-start gap-2 text-sm">
          <input type="checkbox" checked={accept} onChange={(e) => setAccept(e.target.checked)} className="mt-1" />
          I have read the subscription agreement and agree to it on behalf of the institute.
        </label>
        <Field
          label="Sign: type your full name exactly as above"
          value={signature}
          onChange={(e) => setSignature(e.target.value)}
          required
        />
        <ErrorBox error={error} />
        <Button type="submit" disabled={busy || !doc}>
          {busy ? "Signing…" : "Sign agreement"}
        </Button>
      </form>
    </Card>
  );
}

function PendingPayment({ agreement, onChange }: { agreement: Agreement; onChange: () => void }) {
  const [instructions, setInstructions] = useState("");
  const [reference, setReference] = useState(agreement.payment_reference);
  const [message, setMessage] = useState("");
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    api<Agreement>(`/api/agreements/${agreement.id}/`)
      .then((a) => setInstructions(a.payment_instructions ?? ""))
      .catch(() => setInstructions(""));
  }, [agreement.id]);

  async function act(body: Record<string, string>, done: string) {
    setError(null);
    setMessage("");
    try {
      await api(`/api/agreements/${agreement.id}/`, { method: "POST", body: JSON.stringify(body) });
      setMessage(done);
      onChange();
    } catch (err) {
      setError(err);
    }
  }

  return (
    <Card>
      <div className="rounded-xl border-2 border-amber-300 bg-amber-50 p-4 text-amber-950 dark:border-amber-700 dark:bg-amber-950 dark:text-amber-100">
        <p className="font-semibold">
          Agreement signed — payment pending ({agreement.number})
        </p>
        <p className="mt-1 text-sm">
          {agreement.plan_name}, {agreement.billing_cycle}: <span className="font-semibold">{agreement.currency} {Number(agreement.amount).toLocaleString()}</span>.
          Your plan starts as soon as we record your payment.
        </p>
        <p className="mt-3 text-sm font-medium">How to pay</p>
        <p className="text-sm whitespace-pre-line">{instructions || "Contact us for payment details."}</p>
      </div>
      <div className="mt-4 flex flex-wrap items-end gap-2">
        <div className="min-w-56 flex-1">
          <Field
            label="Paid already? Payment reference / transaction ID (optional)"
            value={reference}
            onChange={(e) => setReference(e.target.value)}
            maxLength={100}
          />
        </div>
        <Button type="button" onClick={() => act({ payment_reference: reference }, "Thank you. We will confirm your payment.")}>
          Save reference
        </Button>
      </div>
      <div className="mt-3 flex flex-wrap gap-4 text-sm">
        <Link href={`/agreement/?id=${agreement.id}`} className="text-brand-600 hover:underline">
          View / print agreement
        </Link>
        <button
          type="button"
          onClick={() => confirm("Withdraw this unpaid agreement?") && act({ action: "cancel" }, "Agreement withdrawn.")}
          className="text-red-600 hover:underline"
        >
          Withdraw
        </button>
      </div>
      <ErrorBox error={error} />
      {message && <p className="mt-2 text-sm text-emerald-700">{message}</p>}
    </Card>
  );
}
