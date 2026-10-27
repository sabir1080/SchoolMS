import { INVOICE_STATUS, type InvoiceStatus } from "@/lib/fees";

export function InvoiceStatusBadge({ status }: { status: InvoiceStatus }) {
  const s = INVOICE_STATUS[status];
  return <span className={`rounded-full px-2 py-0.5 text-xs font-medium whitespace-nowrap ${s.tone}`}>{s.label}</span>;
}
