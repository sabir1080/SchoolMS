"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AmountColumns, BarList } from "@/components/dashboard/charts";
import { Card, ErrorBox } from "@/components/ui";
import { api, formatMoney } from "@/lib/api";
import { formatDate, STATUS_LABELS } from "@/lib/navigation";

interface SubRow {
  tenant: number;
  name: string;
  slug: string;
  plan: string;
  status: string;
  days_left: number;
  period_end: string;
  email: string;
  phone: string;
}

interface Overview {
  institutes: { total: number; active: number; trial: number; paying: number; expired: number; suspended: number; new_this_month: number };
  plans: { plan: string; institutes: number }[];
  students: number;
  users: number;
  revenue: { currency: string; this_month: string; last_month: string; this_year: string; months: { month: string; amount: string }[] }[];
  expiring: SubRow[];
  expired: SubRow[];
  recent_institutes: { id: number; name: string; slug: string; institute_type: string; created_at: string }[];
  recent_payments: { id: number; name: string; plan: string; amount: string; currency: string; method: string; created_at: string }[];
  top_institutes: { tenant_id: number; tenant__name: string; students: number }[];
}

function monthLabel(month: string) {
  const [y, m] = month.split("-").map(Number);
  return new Date(y, m - 1, 1).toLocaleDateString(undefined, { month: "short" });
}

function Tile({ label, value, note, tone = "" }: { label: string; value: string | number; note?: string; tone?: string }) {
  return (
    <div className="rounded-2xl bg-white p-4 shadow-sm dark:bg-slate-900">
      <p className="text-xs text-slate-500">{label}</p>
      <p className={`text-2xl font-semibold tabular-nums ${tone}`}>{value}</p>
      {note && <p className="text-xs text-slate-500">{note}</p>}
    </div>
  );
}

function SubList({ rows, empty, expired = false }: { rows: SubRow[]; empty: string; expired?: boolean }) {
  if (rows.length === 0) return <p className="text-sm text-slate-500">{empty}</p>;
  return (
    <ul className="divide-y divide-slate-100 text-sm dark:divide-slate-800">
      {rows.map((r) => (
        <li key={r.tenant} className="flex items-center justify-between gap-3 py-2">
          <span className="min-w-0">
            <span className="block truncate font-medium">{r.name}</span>
            <span className="block text-xs text-slate-500">
              {r.slug} · {r.plan} · {STATUS_LABELS[r.status as keyof typeof STATUS_LABELS] ?? r.status}
              {r.phone && ` · ${r.phone}`}
            </span>
          </span>
          <span className={`shrink-0 text-right text-xs font-medium ${expired ? "text-red-600" : "text-amber-700"}`}>
            {expired ? `Ended ${formatDate(r.period_end)}` : r.days_left === 0 ? "Ends today" : `${r.days_left} day${r.days_left === 1 ? "" : "s"} left`}
          </span>
        </li>
      ))}
    </ul>
  );
}

/** The platform owner's dashboard. */
export default function PlatformOverviewPage() {
  const [data, setData] = useState<Overview | null>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    api<Overview>("/api/platform/overview/").then(setData).catch(setError);
  }, []);

  if (!data) return error ? <ErrorBox error={error} /> : <p className="text-sm text-slate-500">Loading…</p>;
  const { institutes: i } = data;
  const main = data.revenue[0];
  const fmt = (n: number) => formatMoney(n, main.currency);

  return (
    <div className="max-w-5xl space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-2xl font-semibold">Platform overview</h1>
        <Link href="/platform/tenants" className="text-sm font-medium text-brand-600 hover:underline">
          Manage institutes →
        </Link>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Tile label="Institutes" value={i.total} note={`${i.new_this_month} new this month`} />
        <Tile label="Paying" value={i.paying} note={`${i.trial} on free trial`} tone="text-emerald-700" />
        <Tile label="Expired" value={i.expired} note={i.suspended ? `${i.suspended} suspended` : "Need renewal"} tone={i.expired ? "text-red-600" : ""} />
        <Tile label={`Revenue this month (${main.currency})`} value={fmt(Number(main.this_month))} note={`Last month ${fmt(Number(main.last_month))}`} />
      </div>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Tile label="Students (active)" value={data.students.toLocaleString()} />
        <Tile label="Users" value={data.users.toLocaleString()} note="Admins, teachers, parents, students" />
        <Tile label={`Revenue this year`} value={fmt(Number(main.this_year))} />
        <Tile label="Active institutes" value={i.active} note="Trial or paid, not expired" />
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <AmountColumns
            title={`Subscription revenue (${main.currency}), last 6 months`}
            columns={main.months.map((m) => ({ key: m.month, label: monthLabel(m.month), value: Number(m.amount) }))}
            format={fmt}
          />
          {data.revenue.length > 1 && (
            <p className="mt-2 text-xs text-slate-500">
              Also this month:{" "}
              {data.revenue
                .slice(1)
                .map((r) => formatMoney(r.this_month, r.currency))
                .join(", ")}
            </p>
          )}
        </Card>
        <Card>
          <BarList
            title="Active institutes by plan"
            rows={data.plans.map((p) => ({ key: p.plan, label: p.plan, value: p.institutes }))}
            emptyText="No active institutes yet."
          />
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <h2 className="mb-2 font-medium">Renewals due in 14 days</h2>
          <SubList rows={data.expiring} empty="Nothing due soon." />
        </Card>
        <Card>
          <h2 className="mb-2 font-medium">Expired — follow up</h2>
          <SubList rows={data.expired} empty="No expired institutes." expired />
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <h2 className="mb-2 font-medium">Newest institutes</h2>
          <ul className="space-y-1 text-sm">
            {data.recent_institutes.map((t) => (
              <li key={t.id} className="flex justify-between gap-2">
                <span className="truncate">{t.name}</span>
                <span className="shrink-0 text-xs text-slate-500">{formatDate(t.created_at)}</span>
              </li>
            ))}
          </ul>
        </Card>
        <Card>
          <h2 className="mb-2 font-medium">Latest payments</h2>
          {data.recent_payments.length === 0 ? (
            <p className="text-sm text-slate-500">No payments yet.</p>
          ) : (
            <ul className="space-y-1 text-sm">
              {data.recent_payments.map((p) => (
                <li key={p.id} className="flex justify-between gap-2">
                  <span className="min-w-0 truncate">
                    {p.name} <span className="text-xs text-slate-500">· {p.plan}</span>
                  </span>
                  <span className="shrink-0 font-medium tabular-nums">{formatMoney(p.amount, p.currency)}</span>
                </li>
              ))}
            </ul>
          )}
        </Card>
        <Card>
          <BarList
            title="Biggest institutes (students)"
            rows={data.top_institutes.map((t) => ({ key: String(t.tenant_id), label: t.tenant__name, value: t.students }))}
            emptyText="No students yet."
          />
        </Card>
      </div>
    </div>
  );
}
