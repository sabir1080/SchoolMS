"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import type { AcademicSession } from "@/components/academics/types";
import { useList } from "@/components/academics/useList";
import { FeesTabs } from "@/components/fees/FeesTabs";
import { Button, Card, ErrorBox, Field } from "@/components/ui";
import { api, apiList } from "@/lib/api";
import type { InvoiceDetail } from "@/lib/fees";
import { monthDefaults } from "@/lib/fees";
import type { StudentListItem } from "@/lib/students";

interface Line {
  description: string;
  amount: string;
  discount: string;
}

export default function NewInvoicePage() {
  const router = useRouter();
  const defaults = monthDefaults();
  const sessions = useList<AcademicSession>("/api/academics/sessions/");
  const [search, setSearch] = useState("");
  const [matches, setMatches] = useState<StudentListItem[]>([]);
  const [student, setStudent] = useState<StudentListItem | null>(null);
  const [form, setForm] = useState({ title: "", issue_date: defaults.issue, due_date: defaults.due, notes: "" });
  const [lines, setLines] = useState<Line[]>([{ description: "", amount: "", discount: "" }]);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  // Pre-select a student from ?student= (link from the student profile).
  useEffect(() => {
    const id = new URLSearchParams(window.location.search).get("student");
    if (id) api<StudentListItem>(`/api/students/${id}/`).then(setStudent).catch(() => undefined);
  }, []);

  useEffect(() => {
    if (student || search.trim().length < 2) {
      setMatches([]);
      return;
    }
    const timer = setTimeout(() => {
      apiList<StudentListItem>(`/api/students/?status=active&search=${encodeURIComponent(search.trim())}`)
        .then((rows) => setMatches(rows.slice(0, 8)))
        .catch(() => setMatches([]));
    }, 300);
    return () => clearTimeout(timer);
  }, [search, student]);

  const current = sessions.items.find((s) => s.is_current) ?? sessions.items[0];

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!student || !current) return;
    setBusy(true);
    setError(null);
    try {
      const invoice = await api<InvoiceDetail>("/api/fees/invoices/", {
        method: "POST",
        body: JSON.stringify({
          ...form,
          student: student.id,
          session: current.id,
          items: lines
            .filter((l) => l.description.trim() && l.amount)
            .map((l) => ({ description: l.description, amount: l.amount, discount: l.discount || "0" })),
        }),
      });
      router.push(`/fees/invoice/?id=${invoice.id}`);
    } catch (err) {
      setError(err);
      setBusy(false);
    }
  }

  return (
    <div className="max-w-2xl space-y-4">
      <h1 className="text-2xl font-semibold">Fees</h1>
      <FeesTabs />
      <form onSubmit={onSubmit} className="space-y-4">
        <Card>
          <h2 className="mb-3 font-medium">One-off bill</h2>
          <p className="mb-3 text-sm text-slate-500">For extra charges like a trip, books or a fine. Monthly fees are created from the Overview tab.</p>
          {student ? (
            <p className="text-sm">
              Student: <span className="font-medium">{student.full_name}</span> (#{student.admission_no}){" "}
              <button type="button" onClick={() => setStudent(null)} className="text-brand-600 hover:underline">
                change
              </button>
            </p>
          ) : (
            <div>
              <Field label="Student" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Type a name or admission no" />
              {matches.length > 0 && (
                <ul className="mt-1 divide-y divide-slate-200 rounded-lg border border-slate-200 text-sm dark:divide-slate-700 dark:border-slate-700">
                  {matches.map((m) => (
                    <li key={m.id}>
                      <button type="button" onClick={() => setStudent(m)} className="w-full px-3 py-2 text-left hover:bg-slate-50 dark:hover:bg-slate-800">
                        {m.full_name} <span className="text-slate-500">#{m.admission_no}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
          <div className="mt-3 grid gap-3 sm:grid-cols-3">
            <Field label="Bill title" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} placeholder="e.g. Study trip" required />
            <Field label="Issue date" type="date" value={form.issue_date} onChange={(e) => setForm({ ...form, issue_date: e.target.value })} required />
            <Field label="Due date" type="date" value={form.due_date} onChange={(e) => setForm({ ...form, due_date: e.target.value })} required />
          </div>
        </Card>
        <Card>
          <h2 className="mb-3 font-medium">Items</h2>
          <div className="space-y-3">
            {lines.map((line, i) => (
              <div key={i} className="grid grid-cols-[1fr_6rem_6rem] gap-2">
                <Field label="Description" value={line.description} onChange={(e) => setLines(lines.map((l, j) => (j === i ? { ...l, description: e.target.value } : l)))} />
                <Field label="Amount" type="number" min="1" value={line.amount} onChange={(e) => setLines(lines.map((l, j) => (j === i ? { ...l, amount: e.target.value } : l)))} />
                <Field label="Discount" type="number" min="0" value={line.discount} onChange={(e) => setLines(lines.map((l, j) => (j === i ? { ...l, discount: e.target.value } : l)))} />
              </div>
            ))}
          </div>
          <button type="button" onClick={() => setLines([...lines, { description: "", amount: "", discount: "" }])} className="mt-3 text-sm text-brand-600 hover:underline">
            + Add item
          </button>
        </Card>
        <ErrorBox error={error} />
        <Button type="submit" disabled={busy || !student}>
          {busy ? "Creating…" : "Create bill"}
        </Button>
      </form>
    </div>
  );
}
