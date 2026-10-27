"use client";

import { useEffect, useState } from "react";

import { PayslipView } from "@/components/payroll/PayslipView";
import { Card, ErrorBox } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { money } from "@/lib/fees";
import { monthName, type Payslip } from "@/lib/payroll";

/** A staff member's own salary slips. */
export default function MyPayslipsPage() {
  const { user } = useAuth();
  const [data, setData] = useState<{ linked: boolean; results: Payslip[] } | null>(null);
  const [open, setOpen] = useState<number | null>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    api<{ linked: boolean; results: Payslip[] }>("/api/me/payslips/").then(setData).catch(setError);
  }, []);

  const slip = data?.results.find((s) => s.id === open);
  return (
    <div className="max-w-2xl space-y-4">
      <h1 className="text-2xl font-semibold print:hidden">My salary slips</h1>
      <ErrorBox error={error} />
      {data && !slip && (
        <Card>
          {!data.linked ? (
            <p className="text-sm text-slate-500">Your login is not linked to a staff record yet. Ask the admin to link it under Staff &amp; payroll.</p>
          ) : data.results.length === 0 ? (
            <p className="text-sm text-slate-500">No salary slips yet.</p>
          ) : (
            <ul className="divide-y divide-slate-200 dark:divide-slate-800">
              {data.results.map((s) => (
                <li key={s.id}>
                  <button onClick={() => setOpen(s.id)} className="flex w-full items-center justify-between py-3 text-left">
                    <span className="font-medium">{monthName(s.period)}</span>
                    <span className="text-sm">
                      {money(s.net, user?.tenant?.currency)}{" "}
                      <span className={s.status === "paid" ? "text-emerald-700" : "text-amber-700"}>{s.status === "paid" ? "Paid" : "Not paid"}</span> ›
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </Card>
      )}
      {slip && (
        <>
          <div className="flex items-center justify-between print:hidden">
            <button onClick={() => setOpen(null)} className="text-sm text-indigo-600 hover:underline">
              ← All slips
            </button>
            <button onClick={() => window.print()} className="rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white">
              Print
            </button>
          </div>
          <PayslipView slip={slip} tenant={user?.tenant} />
        </>
      )}
    </div>
  );
}
