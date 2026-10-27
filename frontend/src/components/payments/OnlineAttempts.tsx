"use client";

import { useEffect, useState } from "react";

import { Card } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { money } from "@/lib/fees";
import type { OnlinePayment } from "@/lib/payments";

const TONE = { success: "text-emerald-700", failed: "text-red-600", pending: "text-amber-700" };
const LABEL = { success: "Paid", failed: "Failed", pending: "Waiting" };

/** Online payment attempts on one bill (admins). */
export function OnlineAttempts({ invoiceId }: { invoiceId: number }) {
  const { user, subscription } = useAuth();
  const currency = user?.tenant?.currency;
  const [attempts, setAttempts] = useState<OnlinePayment[]>([]);
  const enabled = subscription?.plan.features.includes("online_payments");

  useEffect(() => {
    if (enabled) api<OnlinePayment[]>(`/api/pay/attempts/?invoice=${invoiceId}`).then(setAttempts).catch(() => setAttempts([]));
  }, [enabled, invoiceId]);

  if (attempts.length === 0) return null;
  return (
    <Card>
      <h2 className="mb-2 font-medium">Online payment attempts</h2>
      <ul className="divide-y divide-slate-200 text-sm dark:divide-slate-800">
        {attempts.map((a) => (
          <li key={a.reference} className="flex flex-wrap items-center justify-between gap-2 py-2">
            <span>
              {a.provider_label}
              {a.test_mode && a.provider !== "demo" ? " (test)" : ""} · {new Date(a.created_at).toLocaleString()}
              <span className="block text-xs text-slate-500">
                {a.reference}
                {a.message && ` · ${a.message}`}
              </span>
            </span>
            <span className="flex items-center gap-2">
              {money(a.amount, currency)}
              <span className={`font-medium ${TONE[a.status]}`}>{LABEL[a.status]}</span>
            </span>
          </li>
        ))}
      </ul>
    </Card>
  );
}
