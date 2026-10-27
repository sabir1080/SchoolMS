"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import type { AcademicSession, Program, Section } from "@/components/academics/types";
import { useList } from "@/components/academics/useList";
import { FeesTabs } from "@/components/fees/FeesTabs";
import { Button, Card, ErrorBox, Field, SelectField } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { money, monthDefaults } from "@/lib/fees";
import { termsFor } from "@/lib/terms";

interface Summary {
  month: string;
  billed: string;
  billed_paid: string;
  collection_percentage: number | null;
  collected: string;
  outstanding: string;
  overdue_students: number;
  defaulters: { student: number; full_name: string; admission_no: string; balance: string; invoices: number }[];
}

export default function FeesOverviewPage() {
  const { user } = useAuth();
  const currency = user?.tenant?.currency;
  const [month, setMonth] = useState(monthDefaults().month);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [error, setError] = useState<unknown>(null);

  const load = useCallback(() => {
    api<Summary>(`/api/fees/summary/?month=${month}`).then(setSummary).catch(setError);
  }, [month]);

  useEffect(load, [load]);

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Fees</h1>
      <FeesTabs />
      <ErrorBox error={error} />

      <Card>
        <div className="mb-3 flex flex-wrap items-end justify-between gap-3">
          <h2 className="font-medium">Month summary</h2>
          <div className="w-44">
            <Field label="Month" type="month" value={month} onChange={(e) => setMonth(e.target.value)} />
          </div>
        </div>
        {summary && (
          <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Stat label="Billed this month" value={money(summary.billed, currency)} />
            <Stat
              label="Paid of this month's bills"
              value={summary.collection_percentage === null ? "—" : `${summary.collection_percentage}%`}
            />
            <Stat label="Received this month" value={money(summary.collected, currency)} />
            <Stat label="Total still due" value={money(summary.outstanding, currency)} tone="text-red-600" />
          </dl>
        )}
      </Card>

      <GenerateBills onDone={load} />

      {summary && summary.defaulters.length > 0 && (
        <Card>
          <h2 className="mb-2 font-medium">Overdue ({summary.overdue_students} students)</h2>
          <ul className="divide-y divide-slate-200 text-sm dark:divide-slate-800">
            {summary.defaulters.map((d) => (
              <li key={d.student} className="flex items-center justify-between gap-3 py-2">
                <Link href={`/fees/invoices/?student=${d.student}&status=due`} className="min-w-0 truncate text-brand-600 hover:underline">
                  {d.full_name} <span className="text-xs text-slate-500">#{d.admission_no}</span>
                </Link>
                <span className="shrink-0 font-medium text-red-600">
                  {money(d.balance, currency)}
                  <span className="ml-1 text-xs font-normal text-slate-500">({d.invoices} bill{d.invoices === 1 ? "" : "s"})</span>
                </span>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}

function Stat({ label, value, tone = "" }: { label: string; value: string; tone?: string }) {
  return (
    <div className="rounded-xl bg-slate-50 p-3 dark:bg-slate-800">
      <dt className="text-xs text-slate-500">{label}</dt>
      <dd className={`text-lg font-semibold ${tone}`}>{value}</dd>
    </div>
  );
}

function GenerateBills({ onDone }: { onDone: () => void }) {
  const { user } = useAuth();
  const terms = termsFor(user?.tenant);
  const currency = user?.tenant?.currency;
  const defaults = monthDefaults();
  const sessions = useList<AcademicSession>("/api/academics/sessions/");
  const programs = useList<Program>("/api/academics/programs/");
  const [sessionId, setSessionId] = useState("");
  const sections = useList<Section>(sessionId ? `/api/academics/sections/?session=${sessionId}` : null);
  const [form, setForm] = useState({ month: defaults.month, issue_date: defaults.issue, due_date: defaults.due, program: "" });
  const [result, setResult] = useState<{ created: number; already_billed: number; nothing_to_bill: number; total_amount: string } | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!sessionId && sessions.items.length) {
      setSessionId(String((sessions.items.find((s) => s.is_current) ?? sessions.items[0]).id));
    }
  }, [sessions.items, sessionId]);

  function setMonth(month: string) {
    setForm({ ...form, month, issue_date: `${month}-01`, due_date: `${month}-10` });
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    const label = form.program ? programs.items.find((p) => String(p.id) === form.program)?.name : `all ${terms.programs.toLowerCase()}`;
    if (!confirm(`Create ${form.month} bills for ${label}?`)) return;
    setBusy(true);
    setError(null);
    setResult(null);
    const chosen = form.program ? sections.items.filter((s) => String(s.program) === form.program).map((s) => s.id) : undefined;
    try {
      setResult(
        await api("/api/fees/invoices/generate/", {
          method: "POST",
          body: JSON.stringify({
            session: Number(sessionId),
            month: form.month,
            issue_date: form.issue_date,
            due_date: form.due_date,
            ...(chosen ? { sections: chosen } : {}),
          }),
        }),
      );
      onDone();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <h2 className="mb-1 font-medium">Create monthly bills</h2>
      <p className="mb-3 text-sm text-slate-500">
        Makes one bill per active student from the fees in Fee setup. Students who already have a bill for the month are
        skipped, so it is safe to run again (e.g. after new admissions).
      </p>
      <form onSubmit={onSubmit} className="space-y-3">
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Bill month" type="month" value={form.month} onChange={(e) => setMonth(e.target.value)} required />
          <SelectField
            label={terms.program}
            options={[["", `All ${terms.programs.toLowerCase()}`], ...programs.items.filter((p) => p.is_active).map((p): [string, string] => [String(p.id), p.name])]}
            value={form.program}
            onChange={(e) => setForm({ ...form, program: e.target.value })}
          />
          <Field label="Issue date" type="date" value={form.issue_date} onChange={(e) => setForm({ ...form, issue_date: e.target.value })} required />
          <Field label="Due date" type="date" value={form.due_date} onChange={(e) => setForm({ ...form, due_date: e.target.value })} required />
        </div>
        <ErrorBox error={error} />
        {result && (
          <div className="rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200">
            <p className="font-medium">
              {result.created} bill{result.created === 1 ? "" : "s"} created ({money(result.total_amount, currency)}).
            </p>
            {result.already_billed > 0 && <p>{result.already_billed} already had a bill for this month.</p>}
            {result.nothing_to_bill > 0 && <p>{result.nothing_to_bill} had nothing to pay (no fees set or full discount).</p>}
            {result.created > 0 && (
              <Link href={`/fees/invoices/?period=${form.month}`} className="underline">
                View the bills
              </Link>
            )}
          </div>
        )}
        <Button type="submit" disabled={busy || !sessionId}>
          {busy ? "Creating…" : "Create bills"}
        </Button>
      </form>
    </Card>
  );
}
