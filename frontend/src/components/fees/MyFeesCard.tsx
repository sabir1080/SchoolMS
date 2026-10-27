"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { InvoiceStatusBadge } from "@/components/fees/InvoiceStatusBadge";
import { PayOnline } from "@/components/payments/PayOnline";
import { Card } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { invoiceNo, money, type InvoiceDetail } from "@/lib/fees";
import { formatDate } from "@/lib/navigation";

/** Fee bills for a parent's child or for the logged-in student. */
export function MyFeesCard({ url }: { url: string }) {
  const { user } = useAuth();
  const currency = user?.tenant?.currency;
  const [invoices, setInvoices] = useState<InvoiceDetail[] | null>(null);

  useEffect(() => {
    api<InvoiceDetail[]>(url).then(setInvoices).catch(() => setInvoices(null));
  }, [url]);

  if (!invoices) return null;
  const due = invoices.filter((i) => i.status !== "paid").reduce((sum, i) => sum + Number(i.balance), 0);

  return (
    <Card>
      <h2 className="font-medium">Fees</h2>
      <p className="text-sm">
        Due: <span className={`font-semibold ${due > 0 ? "text-red-600" : "text-emerald-700"}`}>{money(due, currency)}</span>
      </p>
      {invoices.length === 0 ? (
        <p className="mt-1 text-sm text-slate-500">No bills yet.</p>
      ) : (
        <ul className="mt-2 divide-y divide-slate-200 text-sm dark:divide-slate-800">
          {invoices.slice(0, 6).map((inv) => (
            <li key={inv.id} className="py-2">
              <div className="flex items-center justify-between gap-2">
                <span className="min-w-0">
                  <span className="block truncate">{inv.title}</span>
                  <span className="text-xs text-slate-500">
                    {invoiceNo(inv.number)} · due {formatDate(inv.due_date)}
                  </span>
                </span>
                <span className="flex shrink-0 flex-col items-end gap-1">
                  {money(inv.status === "paid" ? inv.total : inv.balance, currency)}
                  <InvoiceStatusBadge status={inv.status} />
                </span>
              </div>
              {inv.payments.length > 0 && (
                <p className="mt-1 flex flex-wrap gap-x-3 text-xs">
                  {inv.payments.map((p) => (
                    <Link key={p.id} href={`/receipt/?id=${p.id}`} className="text-brand-600 hover:underline">
                      Receipt {formatDate(p.date)}
                    </Link>
                  ))}
                </p>
              )}
              {(inv.status === "unpaid" || inv.status === "partial") && <PayOnline invoiceId={inv.id} compact />}
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
