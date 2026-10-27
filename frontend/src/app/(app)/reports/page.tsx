"use client";

import { useState } from "react";

import type { AcademicSession, Section } from "@/components/academics/types";
import { useList } from "@/components/academics/useList";
import { Button, Card, ErrorBox, SelectField } from "@/components/ui";
import { api, downloadFile } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Exam } from "@/lib/exams";
import { monthDefaults } from "@/lib/fees";
import { formatDate } from "@/lib/navigation";
import { termsFor } from "@/lib/terms";

type Filter = "section" | "section?" | "month" | "exam" | "status";

interface ReportDef {
  name: string;
  title: string;
  about: string;
  feature: string;
  filters: Filter[];
}

const REPORTS: ReportDef[] = [
  { name: "students", title: "Student list", about: "Names, father, phone, class and roll number.", feature: "students", filters: ["section?", "status"] },
  { name: "attendance", title: "Monthly attendance", about: "Present, absent, leave and % for each student.", feature: "attendance", filters: ["section", "month"] },
  { name: "fee-dues", title: "Fee dues (defaulters)", about: "Every unpaid bill with balance and days overdue.", feature: "fees", filters: ["section?"] },
  { name: "fee-collection", title: "Fee collection", about: "All payments received in a month, with receipts.", feature: "fees", filters: ["month"] },
  { name: "exam-result", title: "Exam result sheet", about: "Marks, total, %, grade and position.", feature: "exams", filters: ["exam", "section"] },
  { name: "payroll", title: "Salaries", about: "Staff salaries of a month and what is paid.", feature: "payroll", filters: ["month"] },
];

interface Report {
  title: string;
  columns: { label: string; kind: string }[];
  rows: (string | number | null)[][];
  totals: string[];
}

export default function ReportsPage() {
  const { subscription } = useAuth();
  const features = subscription?.plan.features ?? [];
  const available = REPORTS.filter((r) => features.includes(r.feature));
  const [chosen, setChosen] = useState<ReportDef | null>(null);

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold print:hidden">Reports</h1>
      {!chosen ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {available.map((r) => (
            <button key={r.name} onClick={() => setChosen(r)} className="rounded-2xl bg-white p-4 text-left shadow-sm hover:ring-1 hover:ring-indigo-200 dark:bg-slate-900">
              <p className="font-semibold">{r.title}</p>
              <p className="mt-1 text-sm text-slate-500">{r.about}</p>
              <p className="mt-2 text-xs font-medium text-indigo-600">Excel · PDF</p>
            </button>
          ))}
        </div>
      ) : (
        <ReportRunner key={chosen.name} report={chosen} onBack={() => setChosen(null)} />
      )}
    </div>
  );
}

function ReportRunner({ report, onBack }: { report: ReportDef; onBack: () => void }) {
  const { user } = useAuth();
  const terms = termsFor(user?.tenant);
  const sessions = useList<AcademicSession>("/api/academics/sessions/");
  const current = sessions.items.find((s) => s.is_current);
  const sections = useList<Section>(current ? `/api/academics/sections/?session=${current.id}` : null);
  const exams = useList<Exam>(report.filters.includes("exam") ? "/api/exams/" : null);
  const [chosen, setParams] = useState<Record<string, string>>({ month: monthDefaults().month, status: "active" });
  const [data, setData] = useState<Report | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  // Required filters default to the first choice as soon as the lists arrive.
  const params: Record<string, string> = {
    ...chosen,
    section: chosen.section ?? (report.filters.includes("section") && sections.items[0] ? String(sections.items[0].id) : ""),
    exam: chosen.exam ?? (exams.items[0] ? String(exams.items[0].id) : ""),
  };

  const ready = (!report.filters.includes("section") || Boolean(params.section)) && (!report.filters.includes("exam") || Boolean(params.exam));

  const query = () => {
    const q = new URLSearchParams();
    for (const f of report.filters) {
      const key = f.replace("?", "");
      if (params[key]) q.set(key, params[key]);
    }
    return q.toString();
  };

  async function preview() {
    setBusy(true);
    setError(null);
    try {
      setData(await api<Report>(`/api/reports/${report.name}/?${query()}`));
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  async function excel() {
    setError(null);
    try {
      await downloadFile(`/api/reports/${report.name}/?${query()}&download=xlsx`, `${report.name}.xlsx`);
    } catch (err) {
      setError(err);
    }
  }

  const set = (key: string, value: string) => {
    setParams({ ...chosen, [key]: value });
    setData(null);
  };
  const show = (value: string | number | null, kind: string) => {
    if (value === null || value === "") return "—";
    if (kind === "date" && typeof value === "string") return formatDate(value);
    if (kind === "money") return Number(value).toLocaleString();
    if (kind === "percent") return `${value}%`;
    return value;
  };

  return (
    <div className="space-y-4">
      <div className="print:hidden">
        <button onClick={onBack} className="text-sm text-indigo-600 hover:underline">
          ← All reports
        </button>
        <h2 className="mt-1 text-xl font-semibold">{report.title}</h2>
        <p className="text-sm text-slate-500">{report.about}</p>
      </div>
      <Card>
        <div className="grid gap-3 sm:grid-cols-3 print:hidden">
          {report.filters.map((f) => {
            const optional = f.endsWith("?");
            const key = f.replace("?", "");
            if (key === "section")
              return (
                <SelectField
                  key={f}
                  label={terms.section}
                  value={params.section ?? ""}
                  onChange={(e) => set("section", e.target.value)}
                  options={[...(optional ? ([["", "All"]] as [string, string][]) : []), ...sections.items.map((s) => [String(s.id), `${s.program_name} - ${s.name}`] as [string, string])]}
                />
              );
            if (key === "month")
              return (
                <label key={f} className="block space-y-1">
                  <span className="block text-sm font-medium">Month</span>
                  <input type="month" aria-label="Month" value={params.month} onChange={(e) => e.target.value && set("month", e.target.value)} className="w-full rounded-lg border border-slate-300 bg-transparent px-3 py-2 text-sm dark:border-slate-700" />
                </label>
              );
            if (key === "exam") return <SelectField key={f} label="Exam" value={params.exam ?? ""} onChange={(e) => set("exam", e.target.value)} options={exams.items.map((x) => [String(x.id), x.name])} />;
            return (
              <SelectField
                key={f}
                label="Students"
                value={params.status}
                onChange={(e) => set("status", e.target.value)}
                options={[
                  ["active", "Active"],
                  ["left", "Left"],
                  ["graduated", "Graduated"],
                  ["all", "All"],
                ]}
              />
            );
          })}
        </div>
        <div className="mt-4 flex flex-wrap gap-2 print:hidden">
          <Button onClick={preview} disabled={busy || !ready}>
            {busy ? "Loading…" : "Show report"}
          </Button>
          <button onClick={excel} disabled={!ready} className="rounded-lg border border-emerald-600 px-4 py-2 text-sm font-medium text-emerald-700 disabled:opacity-50 dark:text-emerald-400">
            Download Excel
          </button>
          {data && (
            <button onClick={() => window.print()} className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium dark:border-slate-700">
              Print / Save PDF
            </button>
          )}
        </div>
        <ErrorBox error={error} />
      </Card>
      {data && (
        <div className="rounded-2xl bg-white p-4 shadow-sm dark:bg-slate-900 print:p-0 print:shadow-none">
          <p className="text-lg font-semibold">{user?.tenant?.name}</p>
          <p className="mb-3 text-sm text-slate-500">{data.title}</p>
          {data.rows.length === 0 ? (
            <p className="text-sm text-slate-500">Nothing to show.</p>
          ) : (
            <div className="overflow-x-auto print:overflow-visible">
              <table className="w-full text-sm print:text-[10px]">
                <thead>
                  <tr className="text-left text-xs text-slate-500">
                    {data.columns.map((c) => (
                      <th key={c.label} className={`border-b border-slate-200 px-2 py-2 font-medium dark:border-slate-800 ${["money", "number", "percent"].includes(c.kind) ? "text-right" : ""}`}>
                        {c.label}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data.rows.map((row, i) => (
                    <tr key={i} className="border-b border-slate-100 dark:border-slate-800">
                      {row.map((v, j) => (
                        <td key={j} className={`px-2 py-1.5 whitespace-nowrap ${["money", "number", "percent"].includes(data.columns[j].kind) ? "text-right" : ""}`}>
                          {show(v, data.columns[j].kind)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {data.totals.length > 0 && <p className="mt-3 text-sm font-medium">{data.totals.join(" · ")}</p>}
        </div>
      )}
    </div>
  );
}
