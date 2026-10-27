"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Card, ErrorBox } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { money } from "@/lib/fees";
import type { OnlinePayment } from "@/lib/payments";

/** Where the gateway sends the customer back: shows whether the payment went through. */
export default function PaymentResultPage() {
  const { user } = useAuth();
  const [payment, setPayment] = useState<OnlinePayment | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [checks, setChecks] = useState(0);

  useEffect(() => {
    const ref = new URLSearchParams(window.location.search).get("ref") ?? "";
    api<OnlinePayment>(`/api/pay/status/?ref=${encodeURIComponent(ref)}`).then(setPayment).catch(setError);
  }, [checks]);

  // A pending payment may be confirmed a little later (e.g. Easypaisa's notification): check again.
  useEffect(() => {
    if (payment?.status === "pending" && checks < 12) {
      const timer = setTimeout(() => setChecks((c) => c + 1), 5000);
      return () => clearTimeout(timer);
    }
  }, [payment, checks]);

  if (!payment) return <ErrorBox error={error} />;
  const amount = money(payment.amount, user?.tenant?.currency);
  const back = user?.role === "admin" ? `/fees/invoice/?id=${payment.invoice}` : "/dashboard/";

  const view = {
    success: { icon: "✓", tone: "bg-emerald-600", title: "Payment received", text: `${amount} was paid for ${payment.invoice_title}.` },
    failed: { icon: "✕", tone: "bg-red-600", title: "Payment not completed", text: payment.message || "The payment was cancelled or declined. No money was taken." },
    pending: { icon: "…", tone: "bg-amber-500", title: "Waiting for confirmation", text: payment.message || "We are waiting for the gateway to confirm the payment. This page updates by itself." },
  }[payment.status];

  return (
    <div className="mx-auto max-w-md">
      <Card>
        <div className={`mx-auto flex h-12 w-12 items-center justify-center rounded-full text-xl text-white ${view.tone}`}>{view.icon}</div>
        <h1 className="mt-3 text-center text-xl font-semibold">{view.title}</h1>
        <p className="mt-1 text-center text-sm text-slate-500">{view.text}</p>
        <dl className="mt-4 space-y-1 text-sm">
          <div className="flex justify-between">
            <dt className="text-slate-500">Student</dt>
            <dd>{payment.student}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-slate-500">Paid with</dt>
            <dd>{payment.provider_label}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-slate-500">Reference</dt>
            <dd className="tabular-nums">{payment.reference}</dd>
          </div>
        </dl>
        <Link href={back} className="mt-5 block rounded-lg bg-brand-600 py-2.5 text-center text-sm font-medium text-white">
          {user?.role === "admin" ? "Back to the bill" : "Back to dashboard"}
        </Link>
      </Card>
    </div>
  );
}
