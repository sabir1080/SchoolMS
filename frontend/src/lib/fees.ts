import { formatMoney } from "./api";

export type InvoiceStatus = "unpaid" | "partial" | "paid" | "cancelled";

export interface FeeHead {
  id: number;
  name: string;
  frequency: "monthly" | "one_time";
  is_active: boolean;
  sort_order: number;
}

export interface InvoiceListItem {
  id: number;
  number: number;
  student: { id: number; full_name: string; admission_no: string; class_name: string | null };
  period: string;
  title: string;
  issue_date: string;
  due_date: string;
  total: string;
  paid: string;
  balance: string;
  status: InvoiceStatus;
}

export interface InvoiceDetail extends InvoiceListItem {
  session_name: string;
  notes: string;
  items: { id: number; description: string; amount: string; discount: string; net: string }[];
  payments: {
    id: number;
    receipt_number: number;
    amount: string;
    date: string;
    method: string;
    reference: string;
    received_by_name: string | null;
  }[];
}

export interface Discount {
  id: number;
  student: number;
  fee_head: number;
  fee_head_name: string;
  discount_type: "amount" | "percent";
  value: string;
  reason: string;
}

export const FREQUENCIES: [string, string][] = [
  ["monthly", "Every month"],
  ["one_time", "Once per session"],
];

export const PAYMENT_METHODS: [string, string][] = [
  ["cash", "Cash"],
  ["bank", "Bank deposit / transfer"],
  ["jazzcash", "JazzCash"],
  ["easypaisa", "Easypaisa"],
  ["card", "Card"],
  ["other", "Other"],
];

export const INVOICE_STATUS: Record<InvoiceStatus, { label: string; tone: string }> = {
  unpaid: { label: "Unpaid", tone: "bg-red-50 text-red-700 dark:bg-red-950 dark:text-red-300" },
  partial: { label: "Partly paid", tone: "bg-amber-50 text-amber-800 dark:bg-amber-950 dark:text-amber-200" },
  paid: { label: "Paid", tone: "bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300" },
  cancelled: { label: "Cancelled", tone: "bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400" },
};

/** Common fees offered by "Add common fees". */
export const COMMON_FEES: { name: string; frequency: "monthly" | "one_time" }[] = [
  { name: "Tuition Fee", frequency: "monthly" },
  { name: "Admission Fee", frequency: "one_time" },
  { name: "Annual Charges", frequency: "one_time" },
  { name: "Exam Fee", frequency: "monthly" },
  { name: "Transport Fee", frequency: "monthly" },
];

export function invoiceNo(n: number) {
  return `INV-${String(n).padStart(4, "0")}`;
}

export function money(amount: string | number, currency: string | undefined) {
  return formatMoney(amount, currency || "PKR");
}

/** "2026-10" for the current month on this device, and the 1st/10th of it. */
export function monthDefaults() {
  const d = new Date();
  const month = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
  return { month, issue: `${month}-01`, due: `${month}-10` };
}
