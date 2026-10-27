"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { InvoiceStatusBadge } from "@/components/fees/InvoiceStatusBadge";
import { Button, Card, ErrorBox, Field, SelectField } from "@/components/ui";
import { api, apiList } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { invoiceNo, money, type Discount, type FeeHead, type InvoiceListItem } from "@/lib/fees";

/** Fees on the student profile (admins): balance, bills and fee discounts. */
export function StudentFeesCard({ studentId }: { studentId: number }) {
  const { user } = useAuth();
  const currency = user?.tenant?.currency;
  const [invoices, setInvoices] = useState<InvoiceListItem[]>([]);
  const [discounts, setDiscounts] = useState<Discount[]>([]);
  const [heads, setHeads] = useState<FeeHead[]>([]);
  const [adding, setAdding] = useState(false);
  const [form, setForm] = useState({ fee_head: "", discount_type: "amount", value: "", reason: "" });
  const [error, setError] = useState<unknown>(null);

  const load = useCallback(() => {
    apiList<InvoiceListItem>(`/api/fees/invoices/?student=${studentId}`).then(setInvoices).catch(setError);
    apiList<Discount>(`/api/fees/discounts/?student=${studentId}`).then(setDiscounts).catch(setError);
    apiList<FeeHead>("/api/fees/heads/").then(setHeads).catch(setError);
  }, [studentId]);

  useEffect(load, [load]);

  const due = invoices
    .filter((i) => i.status === "unpaid" || i.status === "partial")
    .reduce((sum, i) => sum + Number(i.balance), 0);

  async function addDiscount(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await api("/api/fees/discounts/", {
        method: "POST",
        body: JSON.stringify({ ...form, student: studentId, fee_head: Number(form.fee_head) }),
      });
      setAdding(false);
      setForm({ fee_head: "", discount_type: "amount", value: "", reason: "" });
      load();
    } catch (err) {
      setError(err);
    }
  }

  async function removeDiscount(id: number) {
    if (!confirm("Remove this discount? Bills already made are not changed.")) return;
    await api(`/api/fees/discounts/${id}/`, { method: "DELETE" }).catch(setError);
    load();
  }

  return (
    <Card>
      <div className="flex items-center justify-between gap-3">
        <h2 className="font-medium">Fees</h2>
        <Link href={`/fees/new/?student=${studentId}`} className="text-sm text-indigo-600 hover:underline">
          + One-off bill
        </Link>
      </div>
      <p className="mt-1 text-sm">
        Due now:{" "}
        <span className={`font-semibold ${due > 0 ? "text-red-600" : "text-emerald-700"}`}>{money(due, currency)}</span>
      </p>
      <ErrorBox error={error} />

      {invoices.length > 0 && (
        <ul className="mt-2 divide-y divide-slate-200 text-sm dark:divide-slate-800">
          {invoices.slice(0, 6).map((inv) => (
            <li key={inv.id}>
              <Link href={`/fees/invoice/?id=${inv.id}`} className="flex items-center justify-between gap-2 py-2">
                <span className="min-w-0 truncate">
                  {inv.title} <span className="text-xs text-slate-500">{invoiceNo(inv.number)}</span>
                </span>
                <span className="flex shrink-0 items-center gap-2">
                  {money(inv.total, currency)}
                  <InvoiceStatusBadge status={inv.status} />
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
      {invoices.length > 6 && (
        <Link href={`/fees/invoices/?student=${studentId}`} className="text-sm text-indigo-600 hover:underline">
          All {invoices.length} bills
        </Link>
      )}

      <div className="mt-4 border-t border-slate-200 pt-3 dark:border-slate-800">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-medium">Discounts / concessions</h3>
          {!adding && heads.length > 0 && (
            <button onClick={() => setAdding(true)} className="text-sm text-indigo-600 hover:underline">
              + Add discount
            </button>
          )}
        </div>
        {discounts.length === 0 && !adding && <p className="text-sm text-slate-500">None.</p>}
        <ul className="text-sm">
          {discounts.map((d) => (
            <li key={d.id} className="flex items-center justify-between gap-2 py-1">
              <span>
                {d.fee_head_name}: {d.discount_type === "percent" ? `${Number(d.value)}% off` : `${money(d.value, currency)} off`}
                {d.reason && <span className="text-slate-500"> ({d.reason})</span>}
              </span>
              <button onClick={() => removeDiscount(d.id)} className="text-xs text-red-600 hover:underline">
                Remove
              </button>
            </li>
          ))}
        </ul>
        {adding && (
          <form onSubmit={addDiscount} className="mt-2 space-y-2 rounded-xl bg-slate-50 p-3 dark:bg-slate-800">
            <div className="grid gap-2 sm:grid-cols-2">
              <SelectField
                label="Fee"
                options={[["", "— Choose fee —"], ...heads.filter((h) => h.is_active).map((h): [string, string] => [String(h.id), h.name])]}
                value={form.fee_head}
                onChange={(e) => setForm({ ...form, fee_head: e.target.value })}
              />
              <SelectField
                label="Type"
                options={[
                  ["amount", `Fixed amount (${currency ?? "PKR"})`],
                  ["percent", "Percent (%)"],
                ]}
                value={form.discount_type}
                onChange={(e) => setForm({ ...form, discount_type: e.target.value })}
              />
              <Field label="Discount" type="number" min="1" step="0.01" value={form.value} onChange={(e) => setForm({ ...form, value: e.target.value })} required />
              <Field label="Reason (optional)" value={form.reason} onChange={(e) => setForm({ ...form, reason: e.target.value })} placeholder="e.g. Sibling, Scholarship" />
            </div>
            <p className="text-xs text-slate-500">Applies to new bills from now on.</p>
            <div className="flex gap-3">
              <Button type="submit" disabled={!form.fee_head}>
                Save discount
              </Button>
              <button type="button" onClick={() => setAdding(false)} className="text-sm text-slate-500">
                Cancel
              </button>
            </div>
          </form>
        )}
      </div>
    </Card>
  );
}
