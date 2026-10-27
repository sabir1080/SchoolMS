"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { FeesTabs } from "@/components/fees/FeesTabs";
import { InvoiceStatusBadge } from "@/components/fees/InvoiceStatusBadge";
import { OnlineAttempts } from "@/components/payments/OnlineAttempts";
import { PayOnline } from "@/components/payments/PayOnline";
import { Button, Card, ErrorBox, Field, SelectField } from "@/components/ui";
import { api } from "@/lib/api";
import { localToday } from "@/lib/attendance";
import { useAuth } from "@/lib/auth";
import { invoiceNo, money, PAYMENT_METHODS, type InvoiceDetail } from "@/lib/fees";
import { formatDate } from "@/lib/navigation";
import { label } from "@/lib/students";

export default function InvoicePage() {
  const { user } = useAuth();
  const currency = user?.tenant?.currency;
  const [id, setId] = useState<string | null>(null);
  const [invoice, setInvoice] = useState<InvoiceDetail | null>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => setId(new URLSearchParams(window.location.search).get("id")), []);

  const load = useCallback(() => {
    if (id) api<InvoiceDetail>(`/api/fees/invoices/${id}/`).then(setInvoice).catch(setError);
  }, [id]);

  useEffect(load, [load]);

  if (!invoice) return <ErrorBox error={error} />;
  const open = invoice.status === "unpaid" || invoice.status === "partial";

  async function cancel() {
    if (!confirm("Cancel this bill? It will no longer count as due.")) return;
    try {
      setInvoice(await api<InvoiceDetail>(`/api/fees/invoices/${invoice!.id}/cancel/`, { method: "POST" }));
    } catch (err) {
      setError(err);
    }
  }

  async function deletePayment(paymentId: number) {
    if (!confirm("Delete this payment? Use this only to fix a mistake.")) return;
    try {
      await api(`/api/fees/payments/${paymentId}/`, { method: "DELETE" });
      load();
    } catch (err) {
      setError(err);
    }
  }

  return (
    <div className="max-w-3xl space-y-4">
      <h1 className="text-2xl font-semibold print:hidden">Fees</h1>
      <FeesTabs />
      <ErrorBox error={error} />

      <Card>
        <div className="mb-4 hidden print:block">
          <p className="text-xl font-semibold">{user?.tenant?.name}</p>
          <p className="text-sm">Fee bill / receipt</p>
        </div>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-sm text-slate-500">{invoiceNo(invoice.number)}</p>
            <h2 className="text-xl font-semibold">{invoice.title}</h2>
            <p className="mt-1 text-sm">
              <Link href={`/students/view/?id=${invoice.student.id}`} className="font-medium text-indigo-600 hover:underline print:text-black">
                {invoice.student.full_name}
              </Link>{" "}
              · Adm #{invoice.student.admission_no}
              {invoice.student.class_name && ` · ${invoice.student.class_name}`}
            </p>
            <p className="text-sm text-slate-500">
              Issued {formatDate(invoice.issue_date)} · Due {formatDate(invoice.due_date)} · Session {invoice.session_name}
            </p>
          </div>
          <InvoiceStatusBadge status={invoice.status} />
        </div>

        <table className="mt-4 w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200 text-left text-xs text-slate-500 dark:border-slate-800">
              <th className="py-2">Fee</th>
              <th className="py-2 text-right">Amount</th>
            </tr>
          </thead>
          <tbody>
            {invoice.items.map((item) => (
              <tr key={item.id} className="border-b border-slate-100 dark:border-slate-800">
                <td className="py-2">
                  {item.description}
                  {Number(item.discount) > 0 && (
                    <span className="block text-xs text-emerald-700">Discount −{money(item.discount, currency)}</span>
                  )}
                </td>
                <td className="py-2 text-right">
                  {Number(item.discount) > 0 && (
                    <span className="mr-2 text-xs text-slate-400 line-through">{money(item.amount, currency)}</span>
                  )}
                  {money(item.net, currency)}
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot className="font-medium">
            <tr>
              <td className="pt-3">Total</td>
              <td className="pt-3 text-right">{money(invoice.total, currency)}</td>
            </tr>
            <tr>
              <td>Paid</td>
              <td className="text-right text-emerald-700">{money(invoice.paid, currency)}</td>
            </tr>
            <tr className="text-lg">
              <td>Balance</td>
              <td className={`text-right ${Number(invoice.balance) > 0 ? "text-red-600" : ""}`}>{money(invoice.balance, currency)}</td>
            </tr>
          </tfoot>
        </table>
        {invoice.notes && <p className="mt-3 text-sm text-slate-500">{invoice.notes}</p>}

        {invoice.payments.length > 0 && (
          <div className="mt-4">
            <h3 className="mb-1 text-sm font-medium">Payments</h3>
            <ul className="divide-y divide-slate-100 text-sm dark:divide-slate-800">
              {invoice.payments.map((p) => (
                <li key={p.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
                  <span>
                    Receipt #{p.receipt_number} · {formatDate(p.date)} · {label(PAYMENT_METHODS, p.method)}
                    {p.reference && ` · ${p.reference}`}
                    {p.received_by_name && <span className="text-slate-500"> · by {p.received_by_name}</span>}
                  </span>
                  <span className="flex items-center gap-3">
                    <span className="font-medium">{money(p.amount, currency)}</span>
                    <button onClick={() => deletePayment(p.id)} className="text-xs text-red-600 hover:underline print:hidden">
                      Delete
                    </button>
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </Card>

      {open && (
        <div className="space-y-4 print:hidden">
          <RecordPayment invoice={invoice} onSaved={setInvoice} />
          <Card>
            <h2 className="font-medium">Online payment</h2>
            <p className="mb-2 text-sm text-slate-500">Parents see these buttons on their dashboard for this bill.</p>
            <PayOnline invoiceId={invoice.id} />
          </Card>
        </div>
      )}
      <div className="print:hidden">
        <OnlineAttempts invoiceId={invoice.id} />
      </div>

      <div className="flex flex-wrap gap-3 print:hidden">
        <Button onClick={() => window.print()}>Print</Button>
        {open && invoice.payments.length === 0 && (
          <button onClick={cancel} className="text-sm text-red-600 hover:underline">
            Cancel bill
          </button>
        )}
      </div>
    </div>
  );
}

function RecordPayment({ invoice, onSaved }: { invoice: InvoiceDetail; onSaved: (inv: InvoiceDetail) => void }) {
  const { user } = useAuth();
  const [form, setForm] = useState({ amount: invoice.balance.replace(/\.00$/, ""), date: localToday(), method: "cash", reference: "" });
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => setForm((f) => ({ ...f, amount: invoice.balance.replace(/\.00$/, "") })), [invoice.balance]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      onSaved(await api<InvoiceDetail>(`/api/fees/invoices/${invoice.id}/payments/`, { method: "POST", body: JSON.stringify(form) }));
      setForm((f) => ({ ...f, reference: "" }));
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <form onSubmit={onSubmit} className="space-y-3">
        <h2 className="font-medium">Receive payment</h2>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field
            label={`Amount (${user?.tenant?.currency ?? "PKR"})`}
            type="number"
            min="1"
            step="0.01"
            inputMode="decimal"
            value={form.amount}
            onChange={(e) => setForm({ ...form, amount: e.target.value })}
            required
          />
          <Field label="Date" type="date" value={form.date} max={localToday()} onChange={(e) => setForm({ ...form, date: e.target.value })} required />
          <SelectField label="Method" options={PAYMENT_METHODS} value={form.method} onChange={(e) => setForm({ ...form, method: e.target.value })} />
          <Field
            label="Reference (optional)"
            value={form.reference}
            onChange={(e) => setForm({ ...form, reference: e.target.value })}
            placeholder="Transaction ID / slip no"
          />
        </div>
        <p className="text-xs text-slate-500">You can receive part of the amount now and the rest later.</p>
        <ErrorBox error={error} />
        <Button type="submit" disabled={busy}>
          {busy ? "Saving…" : "Save payment"}
        </Button>
      </form>
    </Card>
  );
}
