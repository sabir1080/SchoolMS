"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { useList } from "@/components/academics/useList";
import { Button, Card, ErrorBox, Field, SelectField } from "@/components/ui";
import { api, type User } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { PAYMENT_METHODS, money, monthDefaults } from "@/lib/fees";
import { isoDay } from "@/lib/homework";
import { monthName, type Employee, type Payslip } from "@/lib/payroll";

type Tab = "salaries" | "staff";

export default function PayrollPage() {
  const [tab, setTab] = useState<Tab>("salaries");
  return (
    <div className="max-w-4xl space-y-4">
      <h1 className="text-2xl font-semibold">Staff &amp; payroll</h1>
      <div className="flex w-max gap-1 rounded-xl bg-slate-200/60 p-1 dark:bg-slate-800" role="tablist">
        {(
          [
            ["salaries", "Monthly salaries"],
            ["staff", "Staff"],
          ] as [Tab, string][]
        ).map(([key, label]) => (
          <button
            key={key}
            role="tab"
            aria-selected={tab === key}
            onClick={() => setTab(key)}
            className={`rounded-lg px-3 py-2 text-sm ${tab === key ? "bg-white font-medium shadow-sm dark:bg-slate-900" : "text-slate-600 dark:text-slate-300"}`}
          >
            {label}
          </button>
        ))}
      </div>
      {tab === "salaries" ? <Salaries onAddStaff={() => setTab("staff")} /> : <Staff />}
    </div>
  );
}

interface Month {
  results: Payslip[];
  summary: { count: number; paid_count: number; total: string; paid: string; unpaid: string };
}

function Salaries({ onAddStaff }: { onAddStaff: () => void }) {
  const { user } = useAuth();
  const cur = user?.tenant?.currency;
  const [period, setPeriod] = useState(monthDefaults().month);
  const [data, setData] = useState<Month | null>(null);
  const [open, setOpen] = useState<{ id: number; mode: "adjust" | "pay" } | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [message, setMessage] = useState("");

  const load = useCallback(() => {
    let current = true;
    api<Month>(`/api/payroll/payslips/?period=${period}`)
      .then((d) => current && setData(d))
      .catch((e) => current && setError(e));
    return () => {
      current = false;
    };
  }, [period]);
  useEffect(load, [load]);

  async function run(path: string, body?: object, done?: string) {
    setError(null);
    setMessage("");
    try {
      const r = await api<{ created?: number; already?: number }>(path, { method: "POST", body: body ? JSON.stringify(body) : undefined });
      if (done) setMessage(r.created !== undefined ? `${r.created} salary slip(s) made${r.already ? `, ${r.already} already there` : ""}.` : done);
      setOpen(null);
      load();
    } catch (err) {
      setError(err);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-3">
        <label className="block space-y-1">
          <span className="block text-sm font-medium">Month</span>
          <input type="month" aria-label="Month" value={period} onChange={(e) => e.target.value && setPeriod(e.target.value)} className="rounded-lg border border-slate-300 bg-transparent px-3 py-2 text-sm dark:border-slate-700" />
        </label>
        <Button onClick={() => run("/api/payroll/payslips/generate/", { period }, "done")}>Make salaries for {monthName(period)}</Button>
      </div>
      <ErrorBox error={error} />
      {message && <p className="text-sm text-emerald-700">{message}</p>}
      {data && (
        <>
          <div className="grid grid-cols-3 gap-2">
            {(
              [
                ["Total salaries", data.summary.total, ""],
                ["Paid", data.summary.paid, "text-emerald-700 dark:text-emerald-400"],
                ["To pay", data.summary.unpaid, Number(data.summary.unpaid) > 0 ? "text-amber-700 dark:text-amber-300" : ""],
              ] as const
            ).map(([label, value, tone]) => (
              <div key={label} className="rounded-2xl bg-white p-3 shadow-sm dark:bg-slate-900">
                <p className="text-xs text-slate-500">{label}</p>
                <p className={`text-lg font-semibold ${tone}`}>{money(value, cur)}</p>
              </div>
            ))}
          </div>
          <Card>
            {data.results.length === 0 ? (
              <p className="text-sm text-slate-500">
                No salaries for {monthName(period)} yet. Press “Make salaries” to create a slip for every active staff member.{" "}
                <button onClick={onAddStaff} className="text-indigo-600 hover:underline">
                  Add staff first
                </button>
              </p>
            ) : (
              <ul className="divide-y divide-slate-200 dark:divide-slate-800">
                {data.results.map((s) => (
                  <li key={s.id} className="py-3">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0 flex-1">
                        <p className="font-medium">{s.employee_name}</p>
                        <p className="text-xs text-slate-500">
                          {s.designation && `${s.designation} · `}Basic {money(s.basic, cur)}
                          {Number(s.allowance) > 0 && ` + allowance ${money(s.allowance, cur)}`}
                          {Number(s.bonus) > 0 && ` + bonus ${money(s.bonus, cur)}`}
                          {Number(s.deduction) > 0 && ` − ${money(s.deduction, cur)}${s.note ? ` (${s.note})` : ""}`}
                        </p>
                      </div>
                      <div className="shrink-0 text-right">
                        <p className="font-semibold">{money(s.net, cur)}</p>
                        <p className={`text-xs ${s.status === "paid" ? "text-emerald-700 dark:text-emerald-400" : "text-amber-700 dark:text-amber-300"}`}>
                          {s.status === "paid" ? `Paid · ${s.method_label}` : "Not paid"}
                        </p>
                      </div>
                    </div>
                    <div className="mt-2 flex flex-wrap gap-3 text-sm">
                      {s.status === "unpaid" ? (
                        <>
                          <button onClick={() => setOpen({ id: s.id, mode: "pay" })} className="rounded-lg bg-indigo-600 px-3 py-1 font-medium text-white">
                            Pay
                          </button>
                          <button onClick={() => setOpen({ id: s.id, mode: "adjust" })} className="text-indigo-600 hover:underline">
                            Bonus / deduction
                          </button>
                        </>
                      ) : (
                        <button onClick={() => run(`/api/payroll/payslips/${s.id}/unpay/`)} className="text-slate-600 hover:underline dark:text-slate-300">
                          Undo payment
                        </button>
                      )}
                      <Link href={`/payroll/slip/?id=${s.id}`} className="text-indigo-600 hover:underline">
                        Salary slip
                      </Link>
                    </div>
                    {open?.id === s.id && open.mode === "pay" && <PayForm onPay={(body) => run(`/api/payroll/payslips/${s.id}/pay/`, body, "Salary marked as paid.")} onCancel={() => setOpen(null)} />}
                    {open?.id === s.id && open.mode === "adjust" && (
                      <AdjustForm
                        slip={s}
                        onSaved={() => {
                          setOpen(null);
                          load();
                        }}
                        onCancel={() => setOpen(null)}
                      />
                    )}
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </>
      )}
    </div>
  );
}

function PayForm({ onPay, onCancel }: { onPay: (body: object) => void; onCancel: () => void }) {
  const [form, setForm] = useState({ date: isoDay(new Date()), method: "cash", reference: "" });
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onPay(form);
      }}
      className="mt-3 grid gap-2 rounded-xl border border-slate-200 p-3 sm:grid-cols-4 dark:border-slate-700"
    >
      <Field label="Paid on" type="date" value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} required />
      <SelectField label="Paid by" value={form.method} onChange={(e) => setForm({ ...form, method: e.target.value })} options={PAYMENT_METHODS} />
      <Field label="Reference (optional)" value={form.reference} onChange={(e) => setForm({ ...form, reference: e.target.value })} />
      <div className="flex items-end gap-2">
        <Button type="submit">Mark paid</Button>
        <button type="button" onClick={onCancel} className="pb-2 text-sm text-slate-600 dark:text-slate-300">
          Cancel
        </button>
      </div>
    </form>
  );
}

function AdjustForm({ slip, onSaved, onCancel }: { slip: Payslip; onSaved: () => void; onCancel: () => void }) {
  const [form, setForm] = useState({ bonus: slip.bonus.replace(/\.00$/, ""), deduction: slip.deduction.replace(/\.00$/, ""), note: slip.note });
  const [error, setError] = useState<unknown>(null);
  async function save(e: React.FormEvent) {
    e.preventDefault();
    try {
      await api(`/api/payroll/payslips/${slip.id}/`, { method: "PATCH", body: JSON.stringify({ bonus: form.bonus || "0", deduction: form.deduction || "0", note: form.note }) });
      onSaved();
    } catch (err) {
      setError(err);
    }
  }
  return (
    <form onSubmit={save} className="mt-3 space-y-2 rounded-xl border border-slate-200 p-3 dark:border-slate-700">
      <div className="grid gap-2 sm:grid-cols-3">
        <Field label="Bonus" type="number" min="0" value={form.bonus} onChange={(e) => setForm({ ...form, bonus: e.target.value })} />
        <Field label="Deduction" type="number" min="0" value={form.deduction} onChange={(e) => setForm({ ...form, deduction: e.target.value })} />
        <Field label="Reason (optional)" placeholder="e.g. 2 days unpaid leave" value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })} />
      </div>
      <ErrorBox error={error} />
      <div className="flex gap-3">
        <Button type="submit">Save</Button>
        <button type="button" onClick={onCancel} className="text-sm text-slate-600 dark:text-slate-300">
          Cancel
        </button>
      </div>
    </form>
  );
}

function Staff() {
  const { user } = useAuth();
  const staff = useList<Employee>("/api/payroll/employees/");
  const [editing, setEditing] = useState<Employee | "new" | null>(null);
  const cur = user?.tenant?.currency;
  return (
    <div className="space-y-4">
      {editing === "new" ? (
        <Card>
          <EmployeeForm
            onDone={() => {
              setEditing(null);
              staff.reload();
            }}
          />
        </Card>
      ) : (
        <Button onClick={() => setEditing("new")}>+ Add staff member</Button>
      )}
      <ErrorBox error={staff.error} />
      <Card>
        {staff.loaded && staff.items.length === 0 ? (
          <p className="text-sm text-slate-500">No staff yet. Add teachers and other staff (guards, clerks, drivers) with their salary.</p>
        ) : (
          <ul className="divide-y divide-slate-200 dark:divide-slate-800">
            {staff.items.map((e) =>
              editing !== "new" && editing?.id === e.id ? (
                <li key={e.id} className="py-3">
                  <EmployeeForm
                    employee={e}
                    onDone={() => {
                      setEditing(null);
                      staff.reload();
                    }}
                  />
                </li>
              ) : (
                <li key={e.id} className={`flex items-center justify-between gap-3 py-3 ${e.is_active ? "" : "opacity-60"}`}>
                  <div className="min-w-0">
                    <p className="font-medium">
                      {e.name} {!e.is_active && <span className="text-xs font-normal text-slate-500">(left)</span>}
                    </p>
                    <p className="text-xs text-slate-500">
                      {[e.designation, e.phone, e.user_name && `login: ${e.user_name}`].filter(Boolean).join(" · ")}
                    </p>
                  </div>
                  <div className="text-right text-sm">
                    <p className="font-medium">{money(Number(e.basic_salary) + Number(e.allowance), cur)}</p>
                    <button onClick={() => setEditing(e)} className="text-xs text-indigo-600 hover:underline">
                      Edit
                    </button>
                  </div>
                </li>
              ),
            )}
          </ul>
        )}
      </Card>
    </div>
  );
}

function EmployeeForm({ employee, onDone }: { employee?: Employee; onDone: () => void }) {
  const logins = useList<User & { is_active: boolean }>("/api/users/?page_size=500");
  const [form, setForm] = useState({
    name: employee?.name ?? "",
    designation: employee?.designation ?? "",
    phone: employee?.phone ?? "",
    cnic: employee?.cnic ?? "",
    join_date: employee?.join_date ?? "",
    basic_salary: employee?.basic_salary.replace(/\.00$/, "") ?? "",
    allowance: employee?.allowance.replace(/\.00$/, "") ?? "0",
    bank_account: employee?.bank_account ?? "",
    user: employee?.user ? String(employee.user) : "",
    is_active: employee?.is_active ?? true,
  });
  const [error, setError] = useState<unknown>(null);
  const set = (key: keyof typeof form, value: string | boolean) => setForm({ ...form, [key]: value });

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await api(employee ? `/api/payroll/employees/${employee.id}/` : "/api/payroll/employees/", {
        method: employee ? "PATCH" : "POST",
        body: JSON.stringify({ ...form, join_date: form.join_date || null, user: form.user ? Number(form.user) : null, allowance: form.allowance || "0" }),
      });
      onDone();
    } catch (err) {
      setError(err);
    }
  }
  const staffLogins = logins.items.filter((u) => u.role === "teacher" || u.role === "admin");
  return (
    <form onSubmit={submit} className="space-y-3">
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Name" value={form.name} onChange={(e) => set("name", e.target.value)} required />
        <Field label="Designation" placeholder="e.g. Teacher, Guard, Clerk" value={form.designation} onChange={(e) => set("designation", e.target.value)} />
        <Field label="Basic salary" type="number" min="0" value={form.basic_salary} onChange={(e) => set("basic_salary", e.target.value)} required />
        <Field label="Allowance" type="number" min="0" value={form.allowance} onChange={(e) => set("allowance", e.target.value)} />
        <Field label="Phone" value={form.phone} onChange={(e) => set("phone", e.target.value)} />
        <Field label="CNIC" value={form.cnic} onChange={(e) => set("cnic", e.target.value)} />
        <Field label="Joining date" type="date" value={form.join_date} onChange={(e) => set("join_date", e.target.value)} />
        <Field label="Bank account (optional)" value={form.bank_account} onChange={(e) => set("bank_account", e.target.value)} />
        <SelectField
          label="Login (to see own salary slips)"
          value={form.user}
          onChange={(e) => set("user", e.target.value)}
          options={[["", "No login"], ...staffLogins.map((u) => [String(u.id), `${`${u.first_name} ${u.last_name}`.trim() || u.username} (${u.username})`] as [string, string])]}
        />
        <label className="flex items-center gap-2 self-end pb-2 text-sm">
          <input type="checkbox" checked={form.is_active} onChange={(e) => set("is_active", e.target.checked)} />
          Active (gets a salary each month)
        </label>
      </div>
      <ErrorBox error={error} />
      <div className="flex gap-3">
        <Button type="submit">{employee ? "Save" : "Add staff member"}</Button>
        <button type="button" onClick={onDone} className="text-sm text-slate-600 dark:text-slate-300">
          Cancel
        </button>
      </div>
    </form>
  );
}
