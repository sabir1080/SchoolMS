"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { money } from "@/lib/fees";

interface Summary {
  billed: string;
  collected: string;
  outstanding: string;
  collection_percentage: number | null;
  overdue_students: number;
}

/** Admin dashboard: this month's fees at a glance. */
export function FeeSummaryCard() {
  const { user, subscription } = useAuth();
  const [summary, setSummary] = useState<Summary | null>(null);
  const currency = user?.tenant?.currency;
  const enabled = user?.role === "admin" && subscription?.is_usable && subscription.plan.features.includes("fees");

  useEffect(() => {
    if (enabled) api<Summary>("/api/fees/summary/").then(setSummary).catch(() => setSummary(null));
  }, [enabled]);

  if (!enabled || !summary) return null;

  return (
    <div className="rounded-2xl bg-white p-4 shadow-sm md:p-6 dark:bg-slate-900">
      <div className="flex items-center justify-between gap-3">
        <h2 className="font-medium">Fees this month</h2>
        <Link href="/fees/" className="text-sm text-indigo-600 hover:underline">
          Open fees
        </Link>
      </div>
      <dl className="mt-2 grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
        <div>
          <dt className="text-slate-500">Billed</dt>
          <dd className="font-semibold">{money(summary.billed, currency)}</dd>
        </div>
        <div>
          <dt className="text-slate-500">Received</dt>
          <dd className="font-semibold text-emerald-700">{money(summary.collected, currency)}</dd>
        </div>
        <div>
          <dt className="text-slate-500">Still due (all)</dt>
          <dd className="font-semibold text-red-600">{money(summary.outstanding, currency)}</dd>
        </div>
        <div>
          <dt className="text-slate-500">Overdue students</dt>
          <dd className="font-semibold">{summary.overdue_students}</dd>
        </div>
      </dl>
    </div>
  );
}
