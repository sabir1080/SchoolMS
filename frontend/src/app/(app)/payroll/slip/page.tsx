"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { PayslipView } from "@/components/payroll/PayslipView";
import { ErrorBox } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Payslip } from "@/lib/payroll";

export default function PayslipPage() {
  const { user } = useAuth();
  const [slip, setSlip] = useState<Payslip | null>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    const id = new URLSearchParams(window.location.search).get("id");
    api<Payslip>(`/api/payroll/payslips/${id}/`).then(setSlip).catch(setError);
  }, []);

  if (!slip) return <ErrorBox error={error} />;
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between print:hidden">
        <Link href="/payroll/" className="text-sm text-indigo-600 hover:underline">
          ← Payroll
        </Link>
        <button onClick={() => window.print()} className="rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white">
          Print
        </button>
      </div>
      <PayslipView slip={slip} tenant={user?.tenant} />
    </div>
  );
}
