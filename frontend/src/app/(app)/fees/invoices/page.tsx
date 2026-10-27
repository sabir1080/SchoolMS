"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import type { Program } from "@/components/academics/types";
import { useList } from "@/components/academics/useList";
import { FeesTabs } from "@/components/fees/FeesTabs";
import { InvoiceStatusBadge } from "@/components/fees/InvoiceStatusBadge";
import { Button, Card, ErrorBox } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { invoiceNo, money, type InvoiceListItem } from "@/lib/fees";
import { formatDate } from "@/lib/navigation";
import { termsFor } from "@/lib/terms";

interface Page {
  count: number;
  next: string | null;
  results: InvoiceListItem[];
}

const STATUS_FILTERS: [string, string][] = [
  ["", "All bills"],
  ["due", "Not fully paid"],
  ["overdue", "Overdue"],
  ["paid", "Paid"],
  ["cancelled", "Cancelled"],
];

export default function InvoicesPage() {
  const { user } = useAuth();
  const terms = termsFor(user?.tenant);
  const currency = user?.tenant?.currency;
  const programs = useList<Program>("/api/academics/programs/");
  const [filters, setFilters] = useState({ search: "", status: "", program: "", period: "", student: "" });
  const [ready, setReady] = useState(false);
  const [page, setPage] = useState(1);
  const [data, setData] = useState<Page | null>(null);
  const [error, setError] = useState<unknown>(null);

  // Filters can come from links, e.g. ?period=2026-10 or ?student=5&status=due.
  useEffect(() => {
    const p = new URLSearchParams(window.location.search);
    setFilters((f) => ({
      ...f,
      status: p.get("status") ?? "",
      period: p.get("period") ?? "",
      student: p.get("student") ?? "",
    }));
    setReady(true);
  }, []);

  useEffect(() => {
    if (!ready) return;
    const params = new URLSearchParams({ page: String(page) });
    Object.entries(filters).forEach(([k, v]) => v.trim() && params.set(k, v.trim()));
    const timer = setTimeout(() => {
      api<Page>(`/api/fees/invoices/?${params}`)
        .then((d) => {
          setData(d);
          setError(null);
        })
        .catch(setError);
    }, 300);
    return () => clearTimeout(timer);
  }, [filters, page, ready]);

  const set = (key: keyof typeof filters) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setFilters({ ...filters, [key]: e.target.value });
    setPage(1);
  };
  const input = "w-full rounded-lg border border-slate-300 bg-transparent px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900";

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold">Fees</h1>
        <Link href="/fees/new/">
          <Button>+ One-off bill</Button>
        </Link>
      </div>
      <FeesTabs />

      <Card>
        <div className="grid gap-3 sm:grid-cols-4">
          <input value={filters.search} onChange={set("search")} placeholder="Name, admission no, bill no" aria-label="Search bills" className={input} />
          <select value={filters.status} onChange={set("status")} aria-label="Filter by status" className={input}>
            {STATUS_FILTERS.map(([v, t]) => (
              <option key={v} value={v}>
                {t}
              </option>
            ))}
          </select>
          <select value={filters.program} onChange={set("program")} aria-label={`Filter by ${terms.program.toLowerCase()}`} className={input}>
            <option value="">All {terms.programs.toLowerCase()}</option>
            {programs.items.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
          <input type="month" value={filters.period} onChange={set("period")} aria-label="Bill month" className={input} />
        </div>
        {filters.student && (
          <button onClick={() => setFilters({ ...filters, student: "" })} className="mt-2 text-xs text-brand-600 hover:underline">
            Showing one student — show all
          </button>
        )}
      </Card>

      <ErrorBox error={error} />
      {data && (
        <Card>
          <p className="mb-2 text-sm text-slate-500">
            {data.count} bill{data.count === 1 ? "" : "s"}
          </p>
          {data.results.length === 0 ? (
            <p className="text-sm text-slate-500">No bills found. Create monthly bills from the Overview tab.</p>
          ) : (
            <ul className="divide-y divide-slate-200 dark:divide-slate-800">
              {data.results.map((inv) => (
                <li key={inv.id}>
                  <Link href={`/fees/invoice/?id=${inv.id}`} className="flex items-center justify-between gap-3 py-3">
                    <div className="min-w-0">
                      <p className="truncate font-medium">
                        {inv.student.full_name} <span className="text-xs font-normal text-slate-500">{invoiceNo(inv.number)}</span>
                      </p>
                      <p className="truncate text-xs text-slate-500">
                        {inv.title}
                        {inv.student.class_name && ` · ${inv.student.class_name}`} · due {formatDate(inv.due_date)}
                      </p>
                    </div>
                    <div className="shrink-0 text-right">
                      <p className="text-sm font-semibold">{money(inv.status === "paid" ? inv.total : inv.balance, currency)}</p>
                      <InvoiceStatusBadge status={inv.status} />
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          )}
          {(data.next || page > 1) && (
            <div className="mt-3 flex justify-between text-sm">
              <button disabled={page === 1} onClick={() => setPage(page - 1)} className="text-brand-600 disabled:opacity-30">
                ← Previous
              </button>
              <button disabled={!data.next} onClick={() => setPage(page + 1)} className="text-brand-600 disabled:opacity-30">
                Next →
              </button>
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
