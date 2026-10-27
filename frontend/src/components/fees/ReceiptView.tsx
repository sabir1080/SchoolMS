import { BrandLogo } from "@/components/BrandLogo";
import type { Tenant } from "@/lib/api";
import { amountInWords, invoiceNo, money, receiptNo, type Receipt } from "@/lib/fees";
import { formatDate } from "@/lib/navigation";

/** A printable fee receipt for one payment. */
export function ReceiptView({ receipt, tenant }: { receipt: Receipt; tenant: Tenant | null | undefined }) {
  const cur = receipt.institute.currency;
  const { institute, invoice, student } = receipt;
  const rows: [string, string][] = [
    ["Student", student.full_name],
    ["Admission No.", student.admission_no],
    ...(student.class_name ? [["Class", student.class_name] as [string, string]] : []),
    ["Bill", `${invoiceNo(invoice.number)} · ${invoice.title}`],
    ["Payment method", receipt.method_label + (receipt.reference ? ` (${receipt.reference})` : "")],
  ];
  return (
    <article className="mx-auto max-w-xl rounded-2xl bg-white p-6 text-slate-900 shadow-sm print:max-w-none print:rounded-none print:shadow-none">
      <header className="border-b-2 border-brand-600 pb-3 text-center">
        <BrandLogo src={tenant?.brand?.logo} className="mx-auto mb-1 h-12 w-12" />
        <h2 className="text-xl font-bold">{institute.name}</h2>
        {(institute.address || institute.phone) && (
          <p className="text-xs text-slate-600">{[institute.address, institute.phone].filter(Boolean).join(" · ")}</p>
        )}
        <p className="mt-2 text-sm font-semibold tracking-wide text-brand-700 uppercase">Fee receipt</p>
      </header>
      <div className="mt-3 flex justify-between text-sm">
        <span>No. {receiptNo(receipt.receipt_number)}</span>
        <span>Date: {formatDate(receipt.date)}</span>
      </div>
      <dl className="mt-3 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
        {rows.map(([label, value]) => (
          <div key={label} className="contents">
            <dt className="text-slate-500">{label}</dt>
            <dd className="font-medium">{value}</dd>
          </div>
        ))}
      </dl>
      <div className="mt-4 rounded-xl bg-brand-50 p-4 text-center print:border print:border-slate-300">
        <p className="text-xs text-slate-600">Amount received</p>
        <p className="text-2xl font-bold">{money(receipt.amount, cur)}</p>
        <p className="text-xs text-slate-600">{amountInWords(receipt.amount, cur)} only</p>
      </div>
      <table className="mt-4 w-full border-collapse text-sm">
        <tbody>
          <tr>
            <td className="border border-slate-200 px-3 py-1.5">Bill total</td>
            <td className="border border-slate-200 px-3 py-1.5 text-right">{money(invoice.total, cur)}</td>
          </tr>
          <tr>
            <td className="border border-slate-200 px-3 py-1.5">Paid so far (with this receipt)</td>
            <td className="border border-slate-200 px-3 py-1.5 text-right">{money(invoice.paid_so_far, cur)}</td>
          </tr>
          <tr className="font-semibold">
            <td className="border border-slate-200 px-3 py-1.5">Balance</td>
            <td className="border border-slate-200 px-3 py-1.5 text-right">
              {Number(invoice.balance_after) > 0 ? money(invoice.balance_after, cur) : "Fully paid"}
            </td>
          </tr>
        </tbody>
      </table>
      <footer className="mt-12 grid grid-cols-2 gap-8 text-center text-xs text-slate-600">
        <div className="border-t border-slate-400 pt-1">{receipt.received_by_name ? `Received by ${receipt.received_by_name}` : "Paid online"}</div>
        <div className="border-t border-slate-400 pt-1">Accounts office / stamp</div>
      </footer>
    </article>
  );
}
