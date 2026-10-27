import { money } from "@/lib/fees";
import { formatDate } from "@/lib/navigation";
import { monthName, type Payslip } from "@/lib/payroll";
import type { Tenant } from "@/lib/api";

/** A printable salary slip. */
export function PayslipView({ slip, tenant }: { slip: Payslip; tenant: Tenant | null | undefined }) {
  const cur = tenant?.currency;
  const rows: [string, string, boolean?][] = [
    ["Basic salary", slip.basic],
    ["Allowance", slip.allowance],
    ["Bonus", slip.bonus],
    ["Gross salary", slip.gross, true],
    [`Deductions${slip.note ? ` (${slip.note})` : ""}`, slip.deduction],
  ];
  return (
    <article className="mx-auto max-w-xl rounded-2xl bg-white p-6 text-slate-900 shadow-sm print:max-w-none print:rounded-none print:shadow-none">
      <header className="border-b-2 border-indigo-600 pb-3 text-center">
        <h2 className="text-xl font-bold">{tenant?.name}</h2>
        <p className="mt-1 text-sm font-semibold text-indigo-700">Salary slip · {monthName(slip.period)}</p>
      </header>
      <dl className="mt-4 grid grid-cols-2 gap-y-1 text-sm">
        <dt className="text-slate-500">Name</dt>
        <dd className="font-medium">{slip.employee_name}</dd>
        {slip.designation && (
          <>
            <dt className="text-slate-500">Designation</dt>
            <dd>{slip.designation}</dd>
          </>
        )}
        {slip.bank_account && (
          <>
            <dt className="text-slate-500">Bank account</dt>
            <dd>{slip.bank_account}</dd>
          </>
        )}
      </dl>
      <table className="mt-4 w-full border-collapse text-sm">
        <tbody>
          {rows.map(([label, value, bold]) => (
            <tr key={label} className={bold ? "font-semibold" : ""}>
              <td className="border border-slate-200 px-3 py-1.5">{label}</td>
              <td className="border border-slate-200 px-3 py-1.5 text-right">{money(value, cur)}</td>
            </tr>
          ))}
          <tr className="bg-indigo-50 text-base font-bold">
            <td className="border border-slate-200 px-3 py-2">Net salary</td>
            <td className="border border-slate-200 px-3 py-2 text-right">{money(slip.net, cur)}</td>
          </tr>
        </tbody>
      </table>
      <p className="mt-3 text-sm">
        {slip.status === "paid" ? (
          <span className="font-medium text-emerald-700">
            Paid on {formatDate(slip.paid_on!)} by {slip.method_label}
            {slip.reference && ` (${slip.reference})`}
          </span>
        ) : (
          <span className="font-medium text-amber-700">Not paid yet</span>
        )}
      </p>
      <footer className="mt-12 grid grid-cols-2 gap-8 text-center text-xs text-slate-600">
        <div className="border-t border-slate-400 pt-1">Received by</div>
        <div className="border-t border-slate-400 pt-1">Principal / Accounts</div>
      </footer>
    </article>
  );
}
